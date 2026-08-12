#!/usr/bin/env python3
"""Audit direct dependency declarations and security posture for ARCTURA Base."""

from __future__ import annotations

import importlib.metadata
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements.txt"
SOURCE_DIRS = [ROOT / "arctura_base", ROOT / "neurons", ROOT / "tests"]

# Known vulnerable or deprecated package patterns for security audit
KNOWN_VULNERABILITIES = {
    "requests": "<2.31.0",
    "urllib3": "<1.26.18",
    "cryptography": "<41.0.0",
}


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


def installed_version(name: str) -> str:
    aliases = {"python-dotenv": "python-dotenv", "bittensor": "bittensor"}
    dist_name = aliases.get(name, name)
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def main() -> int:
    print("==================================================")
    print("ARCTURA Base — Security & Dependency Audit Scanner")
    print("==================================================")
    
    project_deps = read_project_dependencies()
    requirement_deps = read_requirements()
    
    vulnerabilities_found = 0
    
    print("\n[1] Direct Dependencies & Installed Versions:")
    for dep in project_deps:
        name = package_name(dep)
        ver = installed_version(name)
        print(f"  - {dep} | installed={ver}")
        if name in KNOWN_VULNERABILITIES:
            print(f"    [SECURITY WARNING] {name} has active vulnerability advisory rules.")
            vulnerabilities_found += 1

    print("\n[2] Security Scan Results:")
    if vulnerabilities_found == 0:
        print("  - Status: PASSED. No critical dependency vulnerabilities detected.")
    else:
        print(f"  - Status: FAILED. Detected {vulnerabilities_found} potential advisories.")
        return 1

    print("\n[3] Requirements Consistency Check:")
    project_names = {package_name(dep) for dep in project_deps}
    for dep in requirement_deps:
        if package_name(dep) not in project_names:
            print(f"  - Extra requirement: {dep}")

    print("\nDependency audit completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
