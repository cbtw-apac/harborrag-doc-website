from __future__ import annotations

from pathlib import Path

#: Root files bridged onto the site (same set as check_docs_publish_path.py).
PUBLISHED_ROOT_FILES = frozenset({"README.md", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md"})

#: docs/TOC.md drives the sidebar (see toc.py); it is not a page itself.
TOC_FILE = Path("docs") / "TOC.md"


def _docs_pages(source: Path) -> list[Path]:
    """Return every Markdown page under docs/, excluding docs/TOC.md."""

    source_docs = source / "docs"

    if not source_docs.is_dir():
        return []

    list_files = []
    for path in source_docs.rglob("*.md"):
        if path.is_file():
            relative_path = path.relative_to(source)
            if relative_path != TOC_FILE:
                list_files.append(relative_path)

    return list_files


def _root_files(source: Path) -> list[Path]:
    """Return the published root files that exist at the top of the checkout."""
    files = [
        Path(file_name) for file_name in PUBLISHED_ROOT_FILES if (source / file_name).is_file()
    ]

    return files


def _package_files(source: Path) -> list[Path]:
    """Return README.md and pyproject.toml for every distribution under packages/."""

    source_packages = source / "packages"

    if not source_packages.is_dir():
        return []

    list_files = []

    for child_package in source_packages.iterdir():
        if not child_package.is_dir() or not (child_package / "pyproject.toml").is_file():
            continue

        list_files.append((child_package / "pyproject.toml").relative_to(source))

        if (child_package / "README.md").is_file():
            list_files.append((child_package / "README.md").relative_to(source))

    return list_files


def collect(source: Path) -> list[Path]:
    """Return the repository-relative paths that reach the website, sorted."""

    list_files = _root_files(source) + _docs_pages(source) + _package_files(source)
    return sorted(set(list_files), key=Path.as_posix)
