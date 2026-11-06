from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ingest.frontmatter import FENCE_RE, H1_RE
from ingest.models import Doc
from ingest.toc import doc_id

#: Root files -> target path relative to the docs dir.
ROOT_BRIDGE: dict[Path, Path] = {
    Path("README.md"): Path("project/overview.md"),
    Path("CONTRIBUTING.md"): Path("project/contributing.md"),
    Path("SECURITY.md"): Path("project/security.md"),
    Path("CHANGELOG.md"): Path("project/changelog.md"),
}
PACKAGES_DIR = "packages"
PYPI_URL_BASE = "https://pypi.org/project/"


@dataclass(frozen=True)
class PackageFacts:
    name: str
    version: str
    description: str


# --------------------------------------------------------------------------- route


def is_package_readme(source_path: Path) -> bool:
    """Return ``True`` for ``packages/<name>/README.md`` (exactly three parts).

    ``packages/demo/README.md``           -> True
    ``packages/demo/docs/README.md``      -> False
    ``packages/demo/pyproject.toml``      -> False
    """
    parts = source_path.parts

    return len(parts) == 3 and parts[0] == PACKAGES_DIR and parts[-1] == "README.md"


def bridge_target(source_path: Path) -> Path | None:
    """Return the target path (relative to the docs dir) of a bridged file.

    ``CONTRIBUTING.md``         -> ``project/contributing.md``
    ``packages/demo/README.md`` -> ``packages/demo.md``
    ``docs/users/guide.md``     -> None   (a normal page, not bridged)
    ``packages/demo/pyproject.toml`` -> None (metadata only, never a page)
    """
    if source_path in ROOT_BRIDGE:
        return ROOT_BRIDGE[source_path]
    elif is_package_readme(source_path):
        name = source_path.parts[1]
        return Path(PACKAGES_DIR) / f"{name}.md"
    else:
        return None


def bridge_ids(files: list[Path]) -> dict[str, str]:
    """Return ``{repo path: doc id}`` for every bridged file in ``files``.

    This is the ``bridge`` argument of ``toc.load_toc`` / ``parse_toc``:
    ``{"CONTRIBUTING.md": "project/contributing", "packages/demo/README.md": "packages/demo"}``
    """
    bridge = {}
    for path in files:
        target = bridge_target(path)
        if target is None:
            continue
        bridge[path.as_posix()] = doc_id(PurePosixPath(target.as_posix()))
    return bridge


def bridge_mapping(files: list[Path]) -> dict[Path, str]:
    """Return ``{repo path: target path}`` for the bridged files, for ``links.apply_links``.

    Values are docs-dir-relative POSIX strings (``"project/contributing.md"``),
    so ``links.site_link`` turns them into relative links like any docs/ page.
    """
    bridge = {}
    for path in files:
        target = bridge_target(path)
        if target is None:
            continue
        bridge[path] = target.as_posix()
    return bridge


# --------------------------------------------------------------------------- facts


def read_package_facts(pyproject: Path) -> PackageFacts:
    """Read ``[project] name / version / description`` from a ``pyproject.toml``.

    A missing ``description`` becomes ``""``. A missing ``name`` or ``version``
    is a broken distribution: raise ``KeyError`` naming the file.
    """
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})

    if "name" not in project:
        raise KeyError(f"{pyproject}: [project].name is required!")

    if "version" not in project:
        raise KeyError(f"{pyproject}: [project].version is required!")

    return PackageFacts(
        project["name"],
        project["version"],
        project.get("description", ""),
    )


def facts_table(facts: PackageFacts) -> str:
    """Return the Markdown table prepended to a package page, ending with one newline::

        | | |
        | --- | --- |
        | Package | `harborrag` |
        | Version | `2.0.0a1` |
        | Description | The public SDK facade |
        | PyPI | [harborrag](https://pypi.org/project/harborrag/) |

    The ``Description`` row is omitted when ``facts.description`` is empty.
    ``|`` inside the description is escaped as ``\\|`` so it cannot break the table.
    """
    rows = [
        "| | |",
        "| --- | --- |",
        f"| Package | `{facts.name}` |",
        f"| Version | `{facts.version}` |",
    ]

    if facts.description:
        description = facts.description.replace("|", r"\|")
        rows.append(f"| Description | {description} |")

    rows.append(f"| PyPI | [{facts.name}]({PYPI_URL_BASE}{facts.name}/) |")

    return "\n".join(rows) + "\n"


def prepend_facts(body: str, facts: PackageFacts) -> str:
    """Insert ``facts_table`` right after the page's H1, or at the top when there is none.

    Keeping the H1 first means ``frontmatter.extract_title`` still finds it, and
    ``extract_description`` skips the table (``|`` is in ``NON_PROSE_PREFIXES``),
    so the description is still the README's first prose paragraph.

    ``"# demo\\n\\nIntro.\\n"`` -> ``"# demo\\n\\n<table>\\nIntro.\\n"``
    """
    lines = body.splitlines(keepends=True)
    in_fence = False
    head = ""
    tail = ""

    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        heading = H1_RE.match(line)
        if heading is None:
            continue

        head = "".join(lines[: index + 1])
        tail = "".join(lines[index + 1 :]).lstrip("\n")
        break

    if head:
        return head + "\n" + facts_table(facts) + "\n" + tail
    else:
        return facts_table(facts) + "\n" + body


# --------------------------------------------------------------------------- docs


def bridge_doc(source: Path, source_path: Path) -> Doc:
    """Return the ``Doc`` for one bridged file, before frontmatter (2.6) and links (2.7).

    ``title=""`` and ``frontmatter={}``: ``frontmatter.apply_frontmatter`` fills them.
    ``source_path`` stays the repo path (``CONTRIBUTING.md``) so ``custom_edit_url``
    and link resolution point at the real file; only ``target_path`` changes.
    Package READMEs get ``prepend_facts`` with the facts of the sibling
    ``pyproject.toml``.
    """
    target = bridge_target(source_path)
    if target is None:
        raise ValueError(f"{source_path} is not a bridged file")

    body = (source / source_path).read_text(encoding="utf-8")
    if is_package_readme(source_path):
        facts = read_package_facts(source / source_path.parent / "pyproject.toml")
        body = prepend_facts(body, facts)

    return Doc(source_path, target, title="", body=body, frontmatter={})


def bridge_docs(source: Path, files: list[Path]) -> list[Doc]:
    """Return a ``Doc`` for every bridged file in ``files`` (the output of ``collect``).

    docs/ pages and ``pyproject.toml`` files are skipped; order follows ``files``.
    """
    return [bridge_doc(source, p) for p in files if bridge_target(p) is not None]
