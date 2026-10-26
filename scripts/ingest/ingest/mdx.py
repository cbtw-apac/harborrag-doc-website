from __future__ import annotations

import re

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
#: Inline code spans (`` `x` ``) - their content is literal, never rewritten.
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")


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
    tracking as ``links.rewrite_links``).
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
