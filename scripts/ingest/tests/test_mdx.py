from pathlib import Path

from ingest.mdx import (
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

    result = mdx_sanitize(doc)

    assert result is doc
    assert doc.body == "See [https://a](https://a)\n\n```html\n<img src='x'>\n```\n"
