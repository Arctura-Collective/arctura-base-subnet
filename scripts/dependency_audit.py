#!/usr/bin/env python3
"""Audit direct dependency declarations for ARCTURA Base."""

from __future__ import annotations

import importlib.metadata
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements.txt"
SOURCE_DIRS = [ROOT / "arctura_base", ROOT / "neurons", ROOT / "tests"]


def read_project_dependencies() -> list[str]:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def read_requirements() -> list[str]:
    deps = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#"):
            deps.append(cleaned)
    return deps


def package_name(requirement: str) -> str:
    return re.split(r"[<>=!~\[]", requirement, maxsplit=1)[0].strip().lower()


def imported_modules() -> set[str]:
    modules: set[str] = set()
    pattern = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    for source_dir in SOURCE_DIRS:
        for path in source_dir.rglob("*.py"):
            modules.update(match.group(1).lower() for match in pattern.finditer(path.read_text()))
    return modules


def installed_version(name: str) -> str:
    aliases = {"python-dotenv": "python-dotenv", "bittensor": "bittensor"}
    dist_name = aliases.get(name, name)
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def main() -> int:
    project_deps = read_project_dependencies()
    requirement_deps = read_requirements()
    imports = imported_modules()
    print("Direct dependencies")
    print("===================")
    for dep in project_deps:
        name = package_name(dep)
        print(f"- {dep} | installed={installed_version(name)}")
    print()
    print("requirements.txt-only entries")
    print("=============================")
    project_names = {package_name(dep) for dep in project_deps}
    for dep in requirement_deps:
        if package_name(dep) not in project_names:
            print(f"- {dep}")
    print()
    print("Imported top-level modules")
    print("==========================")
    for module in sorted(imports):
        print(f"- {module}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
