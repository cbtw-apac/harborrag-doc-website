from pathlib import Path, PurePosixPath

import pytest

from ingest.links import (
    BrokenLink,
    BrokenLinksError,
    apply_links,
    github_url,
    raw_url,
    resolve,
    rewrite_link,
    rewrite_links,
    site_link,
    split_anchor,
)
from ingest.models import Doc

MAPPING: dict[Path, str] = {
    Path("docs/users/configuration/README.md"): "users/configuration/README.md",
    Path("docs/users/chat/README.md"): "users/chat/README.md",
    Path("docs/developers/checkout-quick-start.md"): "developers/checkout-quick-start.md",
    Path("docs/getting-started/quick-start.md"): "getting-started/quick-start.md",
    Path("CONTRIBUTING.md"): "/docs/project/contributing",
    Path("packages/harborrag-adapters/README.md"): "/docs/packages/harborrag-adapters",
}
NO_ROOT = Path("/nonexistent")


def _doc(source: str, body: str = "") -> Doc:
    """Doc whose target path is its source path without the leading docs/."""
    source_path = Path(source)
    return Doc(
        source_path=source_path,
        target_path=source_path.relative_to("docs"),
        title="",
        body=body,
        frontmatter={},
    )


def _rewrite(source: str, link: str, root: Path = NO_ROOT) -> str | None:
    return rewrite_link(link, doc=_doc(source), mapping=MAPPING, source_root=root)


# --------------------------------------------------------------------------- helpers


def test_split_anchor():
    assert split_anchor("x.md#a") == ("x.md", "#a")
    assert split_anchor("x.md") == ("x.md", "")


def test_resolve_climbs_to_root_and_rejects_escape():
    source = PurePosixPath("docs/developers/README.md")

    assert resolve(source, "../../CONTRIBUTING.md") == PurePosixPath("CONTRIBUTING.md")
    assert resolve(source, "../../config/advance_chat/") == PurePosixPath("config/advance_chat")
    assert resolve(PurePosixPath("docs/x.md"), "../../outside.md") is None


def test_site_link_relative_and_absolute():
    chat = PurePosixPath("users/chat/README.md")

    assert site_link("users/configuration/README.md", from_target=chat) == (
        "../configuration/README.md"
    )
    assert site_link("users/chat/models.md", from_target=chat) == "models.md"
    assert site_link("/docs/project/contributing", from_target=chat) == (
        "/docs/project/contributing"
    )
    assert site_link("users/x.md", from_target=PurePosixPath("README.md")) == "users/x.md"


def test_github_url_blob_and_tree():
    assert github_url(PurePosixPath("config/models.example.yaml"), is_dir=False) == (
        "https://github.com/cbtw-apac/HarborRAG/blob/main/config/models.example.yaml"
    )
    assert github_url(PurePosixPath("clients/typescript"), is_dir=True) == (
        "https://github.com/cbtw-apac/HarborRAG/tree/main/clients/typescript"
    )


# --------------------------------------------------------------------------- 2.7 table (real links)


def test_sibling_section_stays_relative_md():
    assert _rewrite("docs/users/configuration/workspace-mode.md", "../chat/README.md") == (
        "../chat/README.md"
    )


def test_same_dir_link_stays_relative_md():
    assert _rewrite("docs/getting-started/README.md", "quick-start.md") == "quick-start.md"


def test_root_bridge_becomes_absolute_route():
    assert _rewrite("docs/developers/README.md", "../../CONTRIBUTING.md") == (
        "/docs/project/contributing"
    )


def test_package_bridge_becomes_absolute_route():
    assert _rewrite("docs/users/README.md", "../../packages/harborrag-adapters/README.md") == (
        "/docs/packages/harborrag-adapters"
    )


@pytest.mark.parametrize(
    ("source", "link", "expected"),
    [
        (
            "docs/getting-started/README.md",
            "../developers/checkout-quick-start.md#5-create-the-env-folder",
            "../developers/checkout-quick-start.md#5-create-the-env-folder",
        ),
        (
            "docs/developers/README.md",
            "../../CONTRIBUTING.md#quality-gates",
            "/docs/project/contributing#quality-gates",
        ),
    ],
)
def test_anchor_is_kept(source, link, expected):
    assert _rewrite(source, link) == expected


@pytest.mark.parametrize(
    "link",
    [
        "https://github.com/cbtw-apac/HarborRAG/pull/62",
        "mailto:team@example.com",
        "//cdn.example.com/x.png",
        "#capability-status",
    ],
)
def test_external_and_anchor_links_unchanged(link):
    assert _rewrite("docs/users/detailed-guides/mcp-server/README.md", link) == link


def test_repository_file_outside_docs_links_to_github(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/models.example.yaml").write_text("")
    (tmp_path / "clients/typescript").mkdir(parents=True)

    assert _rewrite(
        "docs/users/configuration/x.md", "../../../config/models.example.yaml", tmp_path
    ) == github_url(PurePosixPath("config/models.example.yaml"), is_dir=False)
    assert _rewrite("docs/users/x.md", "../../clients/typescript#setup", tmp_path) == (
        github_url(PurePosixPath("clients/typescript"), is_dir=True) + "#setup"
    )


@pytest.mark.parametrize(
    "link",
    [
        "hidden.md",  # docs page that exists but is not published
        "../../packages/gone/README.md",  # file that does not exist
        "../../../x.md",  # climbs above the repository root
    ],
)
def test_unmapped_link_is_broken(tmp_path, link):
    (tmp_path / "docs/users").mkdir(parents=True)
    (tmp_path / "docs/users/hidden.md").write_text("")

    assert _rewrite("docs/users/README.md", link, tmp_path) is None


# --------------------------------------------------------------------------- body


def test_rewrite_links_in_body_skips_code_fences():
    body = "See [c](../../CONTRIBUTING.md).\n\n```md\n[c](../../CONTRIBUTING.md)\n```\n"
    doc = _doc("docs/developers/README.md", body)

    assert rewrite_links(doc, mapping=MAPPING, source_root=NO_ROOT) == []
    assert doc.body == (
        "See [c](/docs/project/contributing).\n\n```md\n[c](../../CONTRIBUTING.md)\n```\n"
    )


def test_rewrite_links_keeps_image_and_title():
    doc = _doc("docs/developers/README.md", '![logo](../users/chat/README.md "t")\n')

    assert rewrite_links(doc, mapping=MAPPING, source_root=NO_ROOT) == []
    assert doc.body == '![logo](../users/chat/README.md "t")\n'


def test_rewrite_links_keeps_broken_link_in_body():
    body = "[a](missing.md) and [c](../../CONTRIBUTING.md)\n"
    doc = _doc("docs/developers/README.md", body)

    assert rewrite_links(doc, mapping=MAPPING, source_root=NO_ROOT) == [
        BrokenLink(PurePosixPath("docs/developers/README.md"), "missing.md")
    ]
    assert doc.body == "[a](missing.md) and [c](/docs/project/contributing)\n"


def test_apply_links_reports_every_broken_link():
    docs = [
        _doc("docs/users/README.md", "[a](missing.md)\n"),
        _doc("docs/developers/README.md", "[b](gone.md)\n"),
    ]

    with pytest.raises(BrokenLinksError) as exc:
        apply_links(docs, mapping=MAPPING, source_root=NO_ROOT)

    assert exc.value.broken == [
        BrokenLink(PurePosixPath("docs/users/README.md"), "missing.md"),
        BrokenLink(PurePosixPath("docs/developers/README.md"), "gone.md"),
    ]
    assert "docs/users/README.md: missing.md" in str(exc.value)


# --------------------------------------------------------------------------- images


def _root_doc(body: str) -> Doc:
    """Root README bridged to project/overview.md (where the logo <picture> lives)."""
    return Doc(
        source_path=Path("README.md"),
        target_path=Path("project/overview.md"),
        title="",
        body=body,
        frontmatter={},
    )


def _logo_root(tmp_path: Path) -> Path:
    logos = tmp_path / "website/assets/logos"
    logos.mkdir(parents=True)
    (logos / "logo-dark.png").write_text("")
    (logos / "logo-light.png").write_text("")
    return tmp_path


LOGO_DARK = raw_url(PurePosixPath("website/assets/logos/logo-dark.png"))
LOGO_LIGHT = raw_url(PurePosixPath("website/assets/logos/logo-light.png"))


def test_raw_url():
    assert raw_url(PurePosixPath("website/assets/logos/a b.png")) == (
        "https://raw.githubusercontent.com/cbtw-apac/HarborRAG/main/website/assets/logos/a%20b.png"
    )


def test_markdown_image_outside_docs_uses_raw_url(tmp_path):
    doc = _root_doc("![logo](website/assets/logos/logo-light.png)\n")

    assert rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path)) == []
    assert doc.body == f"![logo]({LOGO_LIGHT})\n"


def test_markdown_image_inside_docs_uses_raw_url(tmp_path):
    (tmp_path / "docs/users").mkdir(parents=True)
    (tmp_path / "docs/users/image.png").write_text("")
    doc = _doc("docs/users/guide.md", "![shot](image.png)\n")

    assert rewrite_links(doc, mapping=MAPPING, source_root=tmp_path) == []
    assert doc.body == f"![shot]({raw_url(PurePosixPath('docs/users/image.png'))})\n"


def test_badge_inside_link_is_an_image(tmp_path):
    doc = _root_doc("[![b](website/assets/logos/logo-dark.png)](https://x.example)\n")

    rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path))

    assert doc.body == f"[![b]({LOGO_DARK})](https://x.example)\n"


def test_html_picture_src_and_srcset_use_raw_url(tmp_path):
    body = (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" srcset="website/assets/logos/logo-dark.png">\n'
        '  <img src="website/assets/logos/logo-light.png" alt="HarborRAG" width="360">\n'
        "</picture>\n"
    )
    doc = _root_doc(body)

    assert rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path)) == []
    assert doc.body == (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{LOGO_DARK}">\n'
        f'  <img src="{LOGO_LIGHT}" alt="HarborRAG" width="360">\n'
        "</picture>\n"
    )


def test_html_srcset_keeps_descriptors(tmp_path):
    doc = _root_doc(
        "<img srcset='website/assets/logos/logo-light.png, "
        "website/assets/logos/logo-dark.png 2x'>\n"
    )

    rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path))

    assert doc.body == f"<img srcset='{LOGO_LIGHT}, {LOGO_DARK} 2x'>\n"


@pytest.mark.parametrize(
    "line",
    [
        '<img src="https://img.shields.io/badge/x.svg">\n',  # external
        '<img src="data:image/png;base64,AAAA">\n',  # data URI
        '<img data-src="website/assets/logos/missing.png">\n',  # not src
        '```html\n<img src="website/assets/logos/missing.png">\n```\n',  # code fence
    ],
)
def test_html_src_left_alone(tmp_path, line):
    doc = _root_doc(line)

    assert rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path)) == []
    assert doc.body == line


def test_html_broken_image_is_reported_and_kept(tmp_path):
    body = '<img src="website/assets/logos/missing.png">\n'
    doc = _root_doc(body)

    assert rewrite_links(doc, mapping=MAPPING, source_root=_logo_root(tmp_path)) == [
        BrokenLink(PurePosixPath("README.md"), "website/assets/logos/missing.png")
    ]
    assert doc.body == body


def test_apply_links_passes_when_all_links_resolve():
    doc = _doc("docs/developers/README.md", "[c](../../CONTRIBUTING.md)\n")
    apply_links([doc], mapping=MAPPING, source_root=NO_ROOT)

    assert doc.body == "[c](/docs/project/contributing)\n"


def test_link_to_toc_goes_to_first_sidebar_page():
    mapping = {**MAPPING, Path("docs/TOC.md"): "getting-started/README.md"}
    doc = Doc(
        source_path=Path("README.md"),
        target_path=Path("project/overview.md"),
        title="",
        body="[Documentation index](docs/TOC.md)\n",
        frontmatter={},
    )

    assert rewrite_links(doc, mapping=mapping, source_root=NO_ROOT) == []
    assert doc.body == "[Documentation index](../getting-started/README.md)\n"
