"""Heading anchors of a page, computed the way Docusaurus does.

Docusaurus gives every heading an id with ``github-slugger`` and, with
``onBrokenAnchors: 'throw'``, fails the build when a link points to an id that
is not on the target page. ``page_anchors`` reproduces those ids so
``links.py`` can reject a broken ``#anchor`` before anything is written.
"""

from __future__ import annotations

import re
import unicodedata

from ingest.frontmatter import FENCE_RE, H1_RE, flatten_inline

#: ATX heading ``## Text`` (up to 3 leading spaces, optional closing ``#``s).
HEADING_RE = re.compile(r"^ {0,3}(?P<hashes>#{1,6})[ \t]+(?P<text>.*?)(?:[ \t]+#+)?[ \t]*$")
#: Docusaurus explicit id: ``## Text {#custom-id}``.
EXPLICIT_ID_RE = re.compile(r"\s*\{#(?P<id>[^}\s]+)\}\s*$")
#: ``<a id="x">`` / ``<span id='x'>`` in raw HTML.
HTML_ID_RE = re.compile(r"""<[A-Za-z][^>]*?\sid=(?P<q>["'])(?P<id>[^"']+)(?P=q)""")


def slugify(text: str) -> str:
    """``github-slugger``'s ``slug()``: lowercase, drop punctuation/symbols, spaces -> ``-``.

    Kept: letters, marks, numbers, connector punctuation (``_``), ``-`` and space.
    ``Policy and audit status`` -> ``policy-and-audit-status``
    ``What's new in 2.0?``      -> ``whats-new-in-20``
    """
    kept = (
        ch
        for ch in text.lower()
        if ch in " -" or unicodedata.category(ch)[0] in "LMN" or unicodedata.category(ch) == "Pc"
    )
    return "".join(kept).replace(" ", "-")


def heading_text(raw: str) -> str:
    """Plain text of a heading as Docusaurus sees it (inline Markdown and HTML tags removed)."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", raw)  # image -> alt
    text = flatten_inline(text)
    text = re.sub(r"<[^>]+>", "", text)  # inline HTML / JSX tags
    text = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", text)  # *em*
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    return text.strip()


def page_anchors(body: str) -> set[str]:
    """Return every anchor id a page body will have once built by Docusaurus.

    - headings outside fenced code blocks, slugged like ``github-slugger``,
      duplicates suffixed ``-1``, ``-2`` ... in document order;
    - ``{#custom-id}`` replaces the slug of its heading;
    - the first ``# H1`` is skipped: ``frontmatter.extract_title`` moves it into
      the ``title`` front matter, and the page title has no anchor;
    - ``id="..."`` of raw HTML elements.

    Not covered: setext headings (``Title\\n=====``) - rare in HarborRAG docs.
    """
    anchors: set[str] = set()
    occurrences: dict[str, int] = {}
    in_fence = False
    title_skipped = False

    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        anchors.update(m["id"] for m in HTML_ID_RE.finditer(line))

        heading = HEADING_RE.match(line)
        if heading is None:
            continue

        if not title_skipped and H1_RE.match(line):
            title_skipped = True
            continue

        text = heading["text"]
        explicit = EXPLICIT_ID_RE.search(text)
        if explicit:
            anchors.add(explicit["id"])
            continue

        # Same loop as github-slugger's BananaSlug.slug().
        original = slug = slugify(heading_text(text))
        while slug in occurrences:
            occurrences[original] += 1
            slug = f"{original}-{occurrences[original]}"
        occurrences[slug] = 0
        anchors.add(slug)

    return anchors