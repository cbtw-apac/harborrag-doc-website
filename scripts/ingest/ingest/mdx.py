from __future__ import annotations

import re
from pathlib import Path

from ingest.frontmatter import FENCE_RE
from ingest.models import Doc

#: ``<https://x>`` / ``<mailto:a@b>`` - CommonMark autolinks; MDX reads them as JSX tags.
AUTOLINK_RE = re.compile(r"<(?P<url>(?:https?://|mailto:)[^>\s]+)>")
#: HTML void elements written without ``/>``: ``<img src="a.png">``, ``<br>``.
VOID_TAG_RE = re.compile(
    r"<(?P<tag>img|br|hr|source|input)\b(?P<attrs>[^>]*?)\s*(?<!/)>", re.IGNORECASE
)
#: ``<!-- text -->`` on one line; MDX only accepts ``{/* text */}``.
HTML_COMMENT_RE = re.compile(r"<!--(?P<text>.*?)-->")
HTML_COMMENT_OPEN_RE = re.compile(r"<!--(?!.*-->)")

#: ``<`` that MDX would try to read as a tag but cannot: ``<=``, ``<5``, ``<-``.
#: A letter, ``/`` or ``!`` starts a real tag or comment; whitespace makes it plain text.
ANGLE_BRACKET_RE = re.compile(r"<(?![A-Za-z/!\s])")
CURLY_BRACE_RE = re.compile(r"\{")
#: Inline code spans (`` `x` ``) - their content is literal, never rewritten.
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
#: Inline code spans, but allowed to cross line breaks within a paragraph (never a blank line).
MULTILINE_CODE_RE = re.compile(r"(`+)(?:(?!\1)(?!\n[ \t]*\n)[\s\S])+?\1")


def rewrite_autolinks(text: str) -> str:
    """Turn CommonMark autolinks into Markdown links.

    ``Docs: <https://cbtw-apac.github.io/HarborRAG/>`` -> ``Docs: [https://cbtw-apac.github.io/HarborRAG/](https://cbtw-apac.github.io/HarborRAG/)``
    ``<mailto:security@example.com>``                 -> ``[security@example.com](mailto:security@example.com)``
    ``<details>``                                      -> unchanged (not a URL)
    """

    def _sub(match: re.Match[str]) -> str:
        url = match["url"]
        label = url.removeprefix("mailto:")
        return f"[{label}]({url})"

    return AUTOLINK_RE.sub(_sub, text)


def self_close_void_tags(text: str) -> str:
    """Close HTML void elements so MDX accepts them.

    ``<img src="a.png" alt="x" width="360">`` -> ``<img src="a.png" alt="x" width="360" />``
    ``<br>``                                  -> ``<br />``
    ``<img src="a.png" />``                   -> unchanged
    """
    return VOID_TAG_RE.sub(lambda m: f"<{m['tag']}{m['attrs']} />", text)


def html_comments_to_mdx(text: str) -> str:
    """Rewrite one-line HTML comments as MDX comments.

    ``<!-- branding-compat -->`` -> ``{/* branding-compat */}``

    Runs after ``guard.branding``, so the ``branding-compat`` marker has
    already done its job; keeping the text only helps someone reading the page source.
    A comment spanning several lines is left as is (and fails the build loudly).
    """

    def _sub(match: re.Match[str]) -> str:
        comment = match["text"].strip().replace("*/", "* /")
        return f"{{/* {comment} */}}"

    return HTML_COMMENT_RE.sub(_sub, text)


def _rewrite_prose(text: str) -> str:
    return html_comments_to_mdx(self_close_void_tags(rewrite_autolinks(text)))


def mdx_safe_line(line: str) -> str:
    """Apply the three rewrites above to one line outside a fenced block.

    Inline code spans are left alone: `` `<https://x>` `` stays as written.
    """
    parts = []
    last = 0
    for match in INLINE_CODE_RE.finditer(line):
        parts.append(_rewrite_prose(line[last : match.start()]))
        parts.append(match[0])
        last = match.end()
    parts.append(_rewrite_prose(line[last:]))

    return "".join(parts)


def mdx_sanitize(doc: Doc) -> Doc:
    """Rewrite ``doc.body`` in place so Docusaurus can compile it as MDX; return ``doc``.

    HarborRAG writes GitHub-flavoured Markdown, and ``website/docs/*.md`` is
    compiled as MDX, which rejects autolinks, unclosed void tags and HTML
    comments. Lines inside fenced code blocks are not touched (same fence
    tracking as ``links.rewrite_links``). What cannot be rewritten safely is
    reported by ``find_mdx_unsafe`` before this runs.
    """
    new_lines = []
    in_fence = False
    for line in doc.body.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            line = mdx_safe_line(line)
        new_lines.append(line)

    doc.body = "".join(new_lines)

    return doc


# --------------------------------------------------------------------------- detector


def _blank(match: re.Match[str]) -> str:
    """Replace a match with spaces, keeping its newlines so line numbers survive."""
    return re.sub(r"[^\n]", " ", match[0])


def _prose_only(text: str) -> str:
    """Return ``text`` with fenced blocks, inline code and closed HTML comments blanked out.

    Inline code may span lines (CommonMark allows it inside one paragraph), so it
    is matched on the whole text, not line by line.
    """
    lines = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            lines.append("\n" if line.endswith("\n") else "")
        elif in_fence:
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)

    prose = MULTILINE_CODE_RE.sub(_blank, "".join(lines))

    return HTML_COMMENT_RE.sub(_blank, prose)


def find_mdx_unsafe(source_path: Path, text: str) -> list[str]:
    """Return ``path:line: reason`` for prose that MDX would reject or evaluate.

    ``text`` is the source file as written upstream, so line numbers match the
    file a writer opens (bridged pages get a facts table prepended later, which
    would shift them). At most one failure per reason per line:

    - ``{`` in prose: MDX evaluates ``{...}`` as JavaScript (``${VAR}`` -> ReferenceError).
    - ``<`` followed by something that cannot start a tag (``<=``, ``<5``, ``<-``).
      ``a < b`` with a space is plain text in MDX and is accepted.
    - ``<!--`` with no ``-->`` on the same line (only one-line comments are rewritten).

    Fenced blocks, inline code (including spans across lines) and closed HTML
    comments are ignored.
    """
    path = source_path.as_posix()
    failures = []
    for line_number, line in enumerate(_prose_only(text).splitlines(), start=1):
        if HTML_COMMENT_OPEN_RE.search(line):
            failures.append(f"{path}:{line_number}: unclosed HTML comment")
            continue
        if ANGLE_BRACKET_RE.search(line):
            failures.append(f"{path}:{line_number}: unexpected '<' in prose")
        if CURLY_BRACE_RE.search(line):
            failures.append(f"{path}:{line_number}: stray '{{' in prose")

    return failures
