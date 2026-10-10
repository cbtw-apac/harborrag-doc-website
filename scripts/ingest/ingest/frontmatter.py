from __future__ import annotations

import re
from pathlib import PurePosixPath

import yaml

from ingest.models import Doc
from ingest.toc import Category, DocItem, TocItem, doc_id

EDIT_URL_BASE = "https://github.com/cbtw-apac/HarborRAG/edit/main/"
DESCRIPTION_MAX = 160
#: Docusaurus class put on docs that are not in TOC.md, hidden by custom.css.
HIDDEN_SIDEBAR_CLASS = "hidden-from-sidebar"
H1_RE = re.compile(r"^#\s+(?P<title>.+?)(?:\s+#+)?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
ORDERED_ITEM_RE = re.compile(r"^\d+\.\s")
#: Paragraphs starting with one of these are not prose
NON_PROSE_PREFIXES = (
    "#",
    "- ",
    "* ",
    "+ ",
    "|",
    ">",
    ":::",
    "<",
    "![",
    "[![",
    "Last reviewed:",
)


# --------------------------------------------------------------------------- inline


def flatten_inline(text: str) -> str:
    """Strip inline Markdown and collapse whitespace.

    ``[text](url)`` -> ``text``, `` `code` `` -> ``code``, ``**bold**`` / ``_em_``
    -> plain text. ``_`` inside a word (``harbor_rag_core``) is left alone.
    """
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)

    return " ".join(text.split())


# --------------------------------------------------------------------------- title


def fallback_title(source_path: PurePosixPath) -> str:
    """Return a title from the file name when the page has no H1.

    ``docs/users/ingestion-modes.md`` -> ``Ingestion Modes``
    (stem, ``-``/``_`` -> space, title-cased).

    ``README.md`` uses its parent dir name (``users/chat/README.md`` -> ``Chat``);
    the root ``README.md`` has none and keeps ``Readme``.
    """
    if source_path.stem.lower() == "readme" and source_path.parent.name:
        name = source_path.parent.name
    else:
        name = source_path.stem

    return name.replace("-", " ").replace("_", " ").title()


def extract_title(body: str, *, source_path: PurePosixPath) -> tuple[str, str]:
    """Return ``(title, body_without_h1)``.

    The title is the text of the first ``# H1`` line that is not inside a fenced
    code block (``#`` lines in a bash block are comments, not headings).
    Trailing content on the heading line is kept in the title, a closing ``#``
    sequence and whitespace are stripped, inline Markdown is flattened:
    ``# Chat Models (`beta`)  #`` -> ``Chat Models (beta)``; ``# C#`` -> ``C#``.

    Only that one line is removed, plus the blank lines directly after it, so
    the body does not start with an empty paragraph. Everything else - including
    a ``Last reviewed: YYYY-MM-DD`` footer - is left untouched.

    No H1 -> ``(fallback_title(source_path), body)`` with the body unchanged.
    """
    lines = body.splitlines(keepends=True)
    in_fence = False

    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        heading = H1_RE.match(line)
        if heading is None:
            continue

        end = index + 1
        while end < len(lines) and lines[end].strip() == "":
            end += 1

        return flatten_inline(heading["title"]), "".join(lines[:index] + lines[end:])

    return fallback_title(source_path), body


# --------------------------------------------------------------------------- description


def _paragraphs(body: str) -> list[str]:
    """Split ``body`` into blank-line separated paragraphs, dropping fenced code blocks."""
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = False

    for line in body.splitlines():
        is_fence = FENCE_RE.match(line) is not None
        if is_fence:
            in_fence = not in_fence

        if is_fence or in_fence or line.strip() == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue

        current.append(line)

    if current:
        paragraphs.append("\n".join(current))

    return paragraphs


def _truncate(text: str) -> str:
    """Cut ``text`` to ``DESCRIPTION_MAX`` chars on a word boundary, adding ``…``."""
    if len(text) <= DESCRIPTION_MAX:
        return text

    limit = DESCRIPTION_MAX - 1  
    space = text.rfind(" ", 0, limit + 1)
    cut = text[:space] if space > 0 else text[:limit]

    return cut.rstrip() + "…"


def extract_description(body: str) -> str | None:
    """Return the first prose paragraph of ``body`` as a one-line description.

    A paragraph is a run of non-blank lines. Skipped paragraphs: fenced code and
    those starting with a ``NON_PROSE_PREFIXES`` entry or ``1.`` - headings,
    lists, tables, blockquotes / admonitions, HTML, images / badges and the
    ``Last reviewed:`` footer.

    Inline Markdown is flattened (see ``flatten_inline``). Longer than
    ``DESCRIPTION_MAX`` -> cut at the last word boundary that fits with a
    trailing ``…`` (the result, ellipsis included, is <= DESCRIPTION_MAX).

    Returns ``None`` when there is no prose paragraph.
    """
    for paragraph in _paragraphs(body):
        first = paragraph.lstrip()
        if first.startswith(NON_PROSE_PREFIXES) or ORDERED_ITEM_RE.match(first):
            continue

        text = flatten_inline(paragraph)
        if text:
            return _truncate(text)

    return None


# --------------------------------------------------------------------------- sidebar


def _walk(items: list[TocItem]) -> list[DocItem]:
    """Flatten ``items`` depth-first, keeping only ``DocItem``s (helper for sidebar_positions)."""
    docs: list[DocItem] = []

    for item in items:
        if isinstance(item, DocItem):
            docs.append(item)
            docs.extend(_walk(item.items))

    return docs


def sidebar_positions(toc: list[Category]) -> dict[str, int]:
    """Return ``{doc id: sidebar_position}`` in TOC.md reading order.

    Positions are 1-based and run across the whole TOC (categories and nested
    items flattened depth-first), so they are unique. ``LinkItem``s take no
    position. A doc listed twice keeps its first position.
    """
    positions: dict[str, int] = {}

    for category in toc:
        for item in _walk(category.items):
            positions.setdefault(item.id, len(positions) + 1)

    return positions


# --------------------------------------------------------------------------- assemble


def build_frontmatter(
    *,
    title: str,
    description: str | None,
    position: int | None,
    source_path: PurePosixPath,
    source_sha: str,
) -> dict[str, object]:
    """Return the frontmatter dict, keys in this order (``sort_keys=False`` keeps it)::

    title
    description          # omitted when None
    sidebar_position     # when the doc is in TOC.md
    sidebar_class_name   # HIDDEN_SIDEBAR_CLASS, when it is not
    custom_edit_url      # EDIT_URL_BASE + source_path
    source_path          # custom field, read by the footer component (Phase 6)
    source_sha           # custom field, read by the footer component (Phase 6)

    Exactly one of ``sidebar_position`` / ``sidebar_class_name`` is present.
    """
    fm: dict[str, object] = {"title": title}

    if description is not None:
        fm["description"] = description

    if position is not None:
        fm["sidebar_position"] = position
    else:
        fm["sidebar_class_name"] = HIDDEN_SIDEBAR_CLASS

    fm["custom_edit_url"] = EDIT_URL_BASE + source_path.as_posix()
    fm["source_path"] = source_path.as_posix()  # str: safe_dump cannot serialise Path
    fm["source_sha"] = source_sha

    return fm


def apply_frontmatter(doc: Doc, *, positions: dict[str, int], source_sha: str) -> Doc:
    """Fill ``doc.title``, ``doc.body`` (H1 removed) and ``doc.frontmatter``; return ``doc``.

    The doc's sidebar id is ``doc_id(doc.target_path)``; its position is looked
    up in ``positions`` (from ``sidebar_positions``).
    """
    source_path = PurePosixPath(doc.source_path.as_posix())
    doc.title, doc.body = extract_title(doc.body, source_path=source_path)

    doc.frontmatter = build_frontmatter(
        title=doc.title,
        description=extract_description(doc.body),
        position=positions.get(doc_id(PurePosixPath(doc.target_path.as_posix()))),
        source_path=source_path,
        source_sha=source_sha,
    )

    return doc


def render(doc: Doc) -> str:
    """Return the page file content: YAML frontmatter block, blank line, body.

    Serialised with ``yaml.safe_dump(doc.frontmatter, sort_keys=False,
    allow_unicode=True)`` so titles with ``:`` or quotes are escaped correctly.
    The result ends with exactly one newline (an empty body ends right after ``---``).
    """
    fm = yaml.safe_dump(doc.frontmatter, sort_keys=False, allow_unicode=True)
    body = doc.body.strip("\n")

    return f"---\n{fm}---\n" + (f"\n{body}\n" if body else "")
