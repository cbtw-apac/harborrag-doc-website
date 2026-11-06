from pathlib import Path

import pytest

from ingest.mdx import (
    find_mdx_unsafe,
    html_comments_to_mdx,
    mdx_safe_line,
    mdx_sanitize,
    rewrite_autolinks,
    self_close_void_tags,
)
from ingest.models import Doc


def _doc(body: str) -> Doc:
    return Doc(Path("README.md"), Path("project/overview.md"), title="", body=body, frontmatter={})


def test_rewrite_autolinks_http_and_mailto():
    # From HarborRAG packages/harborrag/README.md.
    line = "- Documentation: <https://cbtw-apac.github.io/HarborRAG/>"

    assert rewrite_autolinks(line) == (
        "- Documentation: [https://cbtw-apac.github.io/HarborRAG/]"
        "(https://cbtw-apac.github.io/HarborRAG/)"
    )
    assert rewrite_autolinks("<mailto:a@b.c>") == "[a@b.c](mailto:a@b.c)"


def test_rewrite_autolinks_leaves_html_tags_alone():
    for line in ("<details>", "<summary><strong>x</strong></summary>"):
        assert rewrite_autolinks(line) == line


def test_self_close_void_tags():
    # From HarborRAG README.md:3-5.
    source = '<source media="(prefers-color-scheme: dark)" srcset="logo-dark.png">'
    img = '<img src="logo-light.png" alt="HarborRAG" width="360">'

    assert self_close_void_tags(source) == (
        '<source media="(prefers-color-scheme: dark)" srcset="logo-dark.png" />'
    )
    assert self_close_void_tags(img) == '<img src="logo-light.png" alt="HarborRAG" width="360" />'
    assert self_close_void_tags("<br>") == "<br />"
    assert self_close_void_tags("<img src='a' />") == "<img src='a' />"
    assert self_close_void_tags("<br/>") == "<br/>"


def test_html_comments_to_mdx():
    assert html_comments_to_mdx("<!-- branding-compat -->") == "{/* branding-compat */}"
    assert html_comments_to_mdx("<!-- a */ b -->") == "{/* a * / b */}"


def test_mdx_safe_line_skips_inline_code():
    line = "Use `<https://x>` or <https://y>"

    assert mdx_safe_line(line) == "Use `<https://x>` or [https://y](https://y)"


def test_mdx_sanitize_skips_fenced_blocks():
    doc = _doc("See <https://a>\n\n```html\n<img src='x'>\n```\n")

    assert mdx_sanitize(doc) is doc
    assert doc.body == "See [https://a](https://a)\n\n```html\n<img src='x'>\n```\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Set ${VAR} here\n", ["README.md:1: stray '{' in prose"]),
        ("{VAR} at start\n", ["README.md:1: stray '{' in prose"]),
        ("Run `x` with {VAR}\n", ["README.md:1: stray '{' in prose"]),
        ("if a <= b\n", ["README.md:1: unexpected '<' in prose"]),
        ("x <5 y\n", ["README.md:1: unexpected '<' in prose"]),
        ("a <- b\n", ["README.md:1: unexpected '<' in prose"]),
        ("text <!-- open\n", ["README.md:1: unclosed HTML comment"]),
        ("<!-- open\n", ["README.md:1: unclosed HTML comment"]),
        ("ok\n\nsee {x}\n", ["README.md:3: stray '{' in prose"]),
        # One failure per reason per line, however many times it occurs.
        (
            "`a` <= `b` <= `c` {x} {y}\n",
            [
                "README.md:1: unexpected '<' in prose",
                "README.md:1: stray '{' in prose",
            ],
        ),
        # A backtick left open at a blank line does not hide the next paragraph.
        ("a `b\n\nsee {x}\n", ["README.md:3: stray '{' in prose"]),
    ],
)
def test_find_mdx_unsafe_reports_unsafe_prose(text, expected):
    assert find_mdx_unsafe(Path("README.md"), text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Use `{x}` and `a <= b`\n",
        "```bash\necho ${VAR} <!--\n```\n",
        "<details>\n<summary>More</summary>\n</details>\n",
        "See <https://x> or <mailto:a@b.c>\n",
        "<!-- x -->\n",
        "a <!-- {x} --> b\n",
        '<img src="a.png">\n',
        # MDX reads ``<`` followed by whitespace as text (HarborRAG harborrag-memory README).
        "Ties break toward the narrower scope (`SESSION` < `USER` < `PROJECT`).\n",
        # Inline code spanning two lines (HarborRAG docs/users/cli-reference/README.md).
        '`--json` returns `{"ok", "data": {"checks": [...],\n"diagnostics": {...}}, "error"}`.\n',
        "``a ` {b}``\n",
    ],
)
def test_find_mdx_unsafe_accepts_safe_prose(text):
    assert find_mdx_unsafe(Path("README.md"), text) == []
