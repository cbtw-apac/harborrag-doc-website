from __future__ import annotations

import json
import posixpath
import re
import textwrap
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

TOC_FILE = Path("docs") / "TOC.md"
EXTERNAL_LINKS: dict[str, str] = {
    "LICENSE": "https://github.com/cbtw-apac/HarborRAG/blob/main/LICENSE",
}
HEADING_RE = re.compile(r"^##\s+(?P<label>.+?)\s*$")
ITEM_RE = re.compile(r"^(?P<indent>[ ]*)-\s+\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)\)\s*$")
INDENT = 2
ABSOLUTE_URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
ANCHOR = re.compile(r"^#")
MINOR_VERSION_RE = re.compile(r"\d+\.\d+")  # Docusaurus version labels are minors: "2.0"


class TocError(ValueError):
    """A TOC.md line that cannot be turned into a sidebar entry.

    The message always names the line: ``docs/TOC.md:42: <reason>: <line>``.
    """


@dataclass(frozen=True)
class LinkItem:
    label: str
    href: str


@dataclass
class DocItem:
    label: str
    id: str  # Docusaurus doc id, e.g. "users/chat/README"
    items: list[DocItem | LinkItem] = field(default_factory=list)  # indented children


@dataclass
class Category:
    label: str  # from "## Heading"
    items: list[DocItem | LinkItem] = field(default_factory=list)


TocItem = DocItem | LinkItem


# --------------------------------------------------------------------------- parse


def doc_id(target_path: PurePosixPath) -> str:
    """Return the Docusaurus doc id for a page path relative to the docs dir.

    ``users/chat/models.md`` -> ``users/chat/models``
    ``users/chat/README.md`` -> ``users/chat/README`` (explicit, no index magic)
    """
    return target_path.with_suffix("").as_posix()


def resolve_target(
    raw: str,
    *,
    label: str,
    pages: Collection[Path] | None,
    bridge: Mapping[str, str],
) -> TocItem:
    """Turn one link target from TOC.md into a ``DocItem`` or ``LinkItem``.

    ``raw`` is relative to ``docs/`` (where TOC.md lives). Resolution order:

    1. Normalise to a repository-relative path: ``docs/`` + raw, collapse ``..``
       (``../packages/x/README.md`` -> ``packages/x/README.md``).
    2. Under ``docs/`` -> ``DocItem`` with ``doc_id(path relative to docs/)``.
       When ``pages`` is given (repo-relative POSIX paths from ``collect()``),
       the path must be in it.
    3. In ``bridge`` (repo path -> doc id) -> ``DocItem``.
    4. In ``EXTERNAL_LINKS`` -> ``LinkItem``.

    Raises:
        KeyError: the target matches none of the above. ``parse_toc`` turns this
            into a ``TocError`` naming the line, so keep this function line-agnostic.
    """
    if ABSOLUTE_URL.match(raw) or ANCHOR.match(raw):
        raise KeyError(raw)

    repo_path = posixpath.normpath(f"docs/{raw}")

    if repo_path.startswith(".."):
        raise KeyError(repo_path)

    if repo_path.startswith("docs/"):
        if pages is not None and PurePosixPath(repo_path) not in pages:
            raise KeyError(repo_path)

        return DocItem(label, doc_id(PurePosixPath(repo_path).relative_to("docs")))

    if repo_path in bridge:
        return DocItem(label, bridge[repo_path])

    if repo_path in EXTERNAL_LINKS:
        return LinkItem(label, EXTERNAL_LINKS[repo_path])

    raise KeyError(repo_path)


def parse_toc(
    text: str,
    *,
    pages: Collection[Path] | None = None,
    bridge: Mapping[str, str],
    source_name: str = TOC_FILE.as_posix(),
) -> list[Category]:
    """Parse TOC.md into categories with (at most one level of) nested items.

    Line rules:
      - ``# Title``, blank lines, plain prose (``Last reviewed: ...``) -> ignored
      - ``## Heading``                -> start a new ``Category``
      - ``- [Label](path)``           -> item in the current category
      - ``  - [Label](path)`` (+2 sp) -> child of the previous top-level ``DocItem``

    Raises:
        TocError: ``{source_name}:{line_no}: <reason>: {line}`` for an unknown
            target, an item before any ``##`` heading, an indented item with no
            parent, or indentation that is not a multiple of ``INDENT`` / too deep.
    """
    categories: list[Category] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading is not None:
            categories.append(Category(label=heading["label"]))
            continue

        item = ITEM_RE.match(line)
        if not item:
            if line.lstrip().startswith("-"):
                raise TocError(
                    f"{source_name}:{line_no}: malformed list item "
                    f"(expected '- [Label](path)' indented with spaces): {line}"
                )
            continue

        if not categories:
            raise TocError(f"{source_name}:{line_no}: item before any ## heading: {line}")

        level, rem = divmod(len(item["indent"]), INDENT)
        if rem != 0 or level > 1:
            raise TocError(
                f"{source_name}:{line_no}: invalid indentation "
                f"(got {len(item['indent'])} spaces, expected 0 or {INDENT}): {line}"
            )

        try:
            entry = resolve_target(item["target"], label=item["label"], pages=pages, bridge=bridge)
        except KeyError as exc:
            raise TocError(
                f"{source_name}:{line_no}: unknown link target {exc}: {line.strip()}"
            ) from None

        if level == 0:
            categories[-1].items.append(entry)
        else:
            if not categories[-1].items:
                raise TocError(f"{source_name}:{line_no}: nested item without a parent doc: {line}")

            parent = categories[-1].items[-1]

            if not isinstance(parent, DocItem):
                raise TocError(f"{source_name}:{line_no}: nested item without a parent doc: {line}")

            parent.items.append(entry)

    return categories


def load_toc(
    source: Path,
    *,
    pages: Collection[Path] | None = None,
    bridge: Mapping[str, str],
) -> list[Category]:
    """Read ``source / docs/TOC.md`` and parse it (see ``parse_toc``)."""
    text = (source / TOC_FILE).read_text(encoding="utf-8")

    return parse_toc(text, pages=pages, bridge=bridge)


# --------------------------------------------------------------------------- output model


def _item(entry: TocItem) -> dict[str, object]:
    if isinstance(entry, LinkItem):
        return {
            "type": "link",
            "label": entry.label,
            "href": entry.href,
        }

    if isinstance(entry, DocItem):
        if not entry.items:
            return {
                "type": "doc",
                "id": entry.id,
                "label": entry.label,
            }

        return {
            "type": "category",
            "label": entry.label,
            "link": {
                "type": "doc",
                "id": entry.id,
            },
            "items": [_item(child) for child in entry.items],
        }

    raise TypeError(f"Unsupported TOC item: {type(entry).__name__}")


def to_sidebar_items(toc: list[Category]) -> list[dict[str, object]]:
    """Return the Docusaurus sidebar items (JSON-ready dicts) for the parsed TOC.

    Mapping:
      Category            -> {"type": "category", "label", "items": [...]}
      DocItem, no kids    -> {"type": "doc", "id", "label"}
      DocItem with kids   -> {"type": "category", "label",
                              "link": {"type": "doc", "id"}, "items": [...]}
      LinkItem            -> {"type": "link", "label", "href"}

    Shared by both writers so sidebars.ts and versioned JSON never drift.
    """
    return [
        {"type": "category", "label": c.label, "items": [_item(i) for i in c.items]} for c in toc
    ]


# --------------------------------------------------------------------------- writers


def render_sidebars_ts(toc: list[Category]) -> str:
    """Render ``website/sidebars.ts`` for the Next (current) docs.

    Shape::

        // Generated by scripts/ingest from docs/TOC.md - do not edit.
        import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

        export default {
          docs: [ ... ],
        } satisfies SidebarsConfig;

    The sidebar key must stay ``docs`` (navbar sidebarId).
    """
    items = json.dumps(to_sidebar_items(toc), indent=2, ensure_ascii=False)
    items = textwrap.indent(items, "  ").lstrip()

    return (
        "// Generated by scripts/ingest from docs/TOC.md - do not edit.\n"
        "import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';\n"
        "\n"
        "export default {\n"
        f"  docs: {items},\n"
        "} satisfies SidebarsConfig;\n"
    )


def write_sidebars_ts(site: Path, toc: list[Category]) -> Path:
    """Write ``site / sidebars.ts`` and return its path."""
    path = site / "sidebars.ts"
    path.write_text(render_sidebars_ts(toc), encoding="utf-8")

    return path


def render_versioned_sidebars(toc: list[Category]) -> str:
    """Render ``versioned_sidebars/version-X.Y-sidebars.json`` content."""
    return json.dumps({"docs": to_sidebar_items(toc)}, indent=2, ensure_ascii=False) + "\n"


def write_versioned_sidebars(site: Path, version: str, toc: list[Category]) -> Path:
    """Write ``site / versioned_sidebars / version-{version}-sidebars.json`` and return its path.

    ``version`` is the minor label, e.g. ``"2.0"``; a full version such as ``"2.0.1"``
    would create a file Docusaurus never reads, so it is rejected.

    Raises:
        ValueError: ``version`` is not ``MAJOR.MINOR``.
    """
    if not MINOR_VERSION_RE.fullmatch(version):
        raise ValueError(f"expected a MAJOR.MINOR version label like '2.0', got {version!r}")

    path = site / "versioned_sidebars" / f"version-{version}-sidebars.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_versioned_sidebars(toc), encoding="utf-8")

    return path
