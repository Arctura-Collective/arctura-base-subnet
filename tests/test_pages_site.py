"""Checks for the GitHub Pages launch portal."""

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def _links_from(path: Path) -> list[str]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.links


def test_pages_workflow_builds_docs_with_jekyll_and_deploys_pages():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")

    assert "actions/configure-pages@v5" in workflow
    assert "actions/jekyll-build-pages@v1" in workflow
    assert "source: docs" in workflow
    assert "destination: _site" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow


def test_launch_portal_links_existing_local_pages():
    links = _links_from(DOCS / "index.html")
    local_links = [
        link
        for link in links
        if not link.startswith(("http://", "https://")) and not link.startswith("#")
    ]

    assert "pitch_deck.html" in local_links
    assert "subnet-cost.html" in local_links
    for link in local_links:
        source = link.removesuffix(".html")
        candidate = DOCS / link
        markdown_candidate = DOCS / f"{source}.md"
        assert candidate.exists() or markdown_candidate.exists(), link


def test_pitch_deck_has_balanced_sections_and_no_broken_opening_tag():
    deck = (DOCS / "pitch_deck.html").read_text(encoding="utf-8")

    assert "section>" not in deck.replace("<section>", "").replace("</section>", "")
    assert deck.count("<section>") == deck.count("</section>")
    assert deck.count("<section>") >= 8


def test_readme_links_github_pages_launch_portal():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://arctura-collective.github.io/arctura-base-subnet/" in readme
    assert "GitHub Pages launch portal" in readme
