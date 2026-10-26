from __future__ import annotations

from pathlib import Path

#: Root files bridged onto the site (same set as check_docs_publish_path.py).
PUBLISHED_ROOT_FILES = frozenset({"README.md", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md"})

#: docs/TOC.md drives the sidebar (see toc.py); it is not a page itself.
TOC_FILE = Path("docs") / "TOC.md"


def _docs_pages(source: Path) -> list[Path]:
    """Return every Markdown page under docs/, recursively, excluding docs/TOC.md.

    Returns an empty list when the checkout has no docs/ directory.
    """

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
    """Return README.md and pyproject.toml for every distribution under packages/.

    Only direct children of packages/ that contain a pyproject.toml count as
    distributions; anything else (e.g. packages/<x>/docs/) is not published.
    pyproject.toml is collected for its metadata only, not as a page.
    Returns an empty list when the checkout has no packages/ directory.
    """

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
    """Return the published set: the repository-relative paths that reach the website.

    Mirrors HarborRAG's ``website/check_docs_publish_path.py``: the four root
    files in ``PUBLISHED_ROOT_FILES``, ``docs/**/*.md`` except ``docs/TOC.md``,
    and ``packages/<name>/README.md`` + ``pyproject.toml`` for each distribution.
    Everything else in the checkout is an internal note and is left out.

    Paths are relative to ``source`` (read them as ``source / path``), free of
    duplicates and sorted by ``as_posix()``, so the result is deterministic.
    """

    list_files = _root_files(source) + _docs_pages(source) + _package_files(source)
    return sorted(set(list_files), key=Path.as_posix)
