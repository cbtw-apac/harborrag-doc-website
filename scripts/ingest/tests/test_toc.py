import json
from pathlib import Path, PurePosixPath

import pytest

from ingest.collect import collect
from ingest.toc import (
    EXTERNAL_LINKS,
    Category,
    DocItem,
    LinkItem,
    TocError,
    doc_id,
    load_toc,
    parse_toc,
    render_sidebars_ts,
    render_versioned_sidebars,
    to_sidebar_items,
    write_sidebars_ts,
    write_versioned_sidebars,
)

FIXTURE = Path(__file__).parent / "fixtures" / "mini_harborrag"

BRIDGE = {
    **{
        f"packages/{name}/README.md": f"packages/{name}"
        for name in (
            "harborrag",
            "harborrag-core",
            "harborrag-adapters",
            "harborrag-engine",
            "harborrag-memory",
            "harborrag-runtime",
            "harborrag-app",
            "harborrag-mcp-server",
        )
    },
    "CONTRIBUTING.md": "project/contributing",
    "SECURITY.md": "project/security",
    "CHANGELOG.md": "project/changelog",
}

SMALL_TOC = [
    Category(
        label="User guides",
        items=[
            DocItem(label="User Documentation", id="users/README"),
            DocItem(
                label="Chat",
                id="users/chat/README",
                items=[DocItem(label="Chat Models", id="users/chat/models")],
            ),
        ],
    ),
    Category(label="Project", items=[LinkItem(label="License", href=EXTERNAL_LINKS["LICENSE"])]),
]


def test_doc_id_keeps_readme_explicit():
    assert doc_id(PurePosixPath("users/chat/README.md")) == "users/chat/README"
    assert doc_id(PurePosixPath("users/chat/models.md")) == "users/chat/models"


def test_small_toc_yields_nested_structure():
    text = """# Title

## User guides

- [Chat](users/chat/README.md)
  - [Chat Models](users/chat/models.md)
- [Ingestion Modes](users/ingestion-modes.md)

## Project

- [Contributing](../CONTRIBUTING.md)
- [License](../LICENSE)

Last reviewed: 2026-08-27
"""
    expected = [
        Category(
            "User guides",
            [
                DocItem("Chat", "users/chat/README", [DocItem("Chat Models", "users/chat/models")]),
                DocItem("Ingestion Modes", "users/ingestion-modes"),
            ],
        ),
        Category(
            "Project",
            [
                DocItem("Contributing", "project/contributing"),
                LinkItem("License", EXTERNAL_LINKS["LICENSE"]),
            ],
        ),
    ]
    assert parse_toc(text, bridge=BRIDGE) == expected


def test_fixture_toc_categories_and_nesting():
    toc = load_toc(FIXTURE, bridge=BRIDGE)

    assert [c.label for c in toc] == [
        "Getting started",
        "User guides",
        "Developer guides",
        "Package reference",
        "Project",
    ]
    assert len(toc[1].items[1].items) == 4
    assert toc[1].items[1].id == "users/chat/README"
    assert toc[3].items[0].id == "packages/harborrag"
    assert isinstance(toc[4].items[-1], LinkItem)


def test_unknown_target_is_hard_error_naming_the_line():
    text = "## Project\n\n- [Ghost](../GHOST.md)\n"
    with pytest.raises(TocError, match=r"docs/TOC\.md:3: .*GHOST\.md"):
        parse_toc(text, bridge=BRIDGE)


def test_docs_target_missing_from_pages_is_error():
    with pytest.raises(TocError, match=r"docs/TOC\.md:2: .*x\.md"):
        parse_toc("## A\n- [X](x.md)\n", pages={Path("docs/y.md")}, bridge=BRIDGE)


def test_item_before_heading_is_error():
    with pytest.raises(TocError, match=r"docs/TOC\.md:1: "):
        parse_toc("- [X](x.md)\n", pages={Path("docs/x.md")}, bridge=BRIDGE)


def test_nested_item_without_parent_is_error():
    with pytest.raises(TocError, match=r"docs/TOC\.md:2: nested item without a parent"):
        parse_toc("## A\n  - [X](x.md)\n", pages={Path("docs/x.md")}, bridge=BRIDGE)


def test_sidebar_items_shape():
    assert to_sidebar_items(SMALL_TOC) == [
        {
            "type": "category",
            "label": "User guides",
            "items": [
                {
                    "type": "doc",
                    "id": "users/README",
                    "label": "User Documentation",
                },
                {
                    "type": "category",
                    "label": "Chat",
                    "link": {"type": "doc", "id": "users/chat/README"},
                    "items": [
                        {
                            "type": "doc",
                            "id": "users/chat/models",
                            "label": "Chat Models",
                        }
                    ],
                },
            ],
        },
        {
            "type": "category",
            "label": "Project",
            "items": [{"type": "link", "label": "License", "href": EXTERNAL_LINKS["LICENSE"]}],
        },
    ]


def test_render_sidebars_ts_has_satisfies_and_docs_key():
    out = render_sidebars_ts(SMALL_TOC)

    assert "export default {" in out and "} satisfies SidebarsConfig;" in out
    assert "docs:" in out and out.endswith("\n")


@pytest.mark.parametrize(
    "line",
    [
        "- [X](x.md) extra",
        "\t- [X](x.md)",
        "- X",
    ],
)
def test_malformed_list_item_is_error(line):
    with pytest.raises(TocError, match=r"docs/TOC\.md:2: malformed list item"):
        parse_toc(f"## A\n{line}\n", bridge=BRIDGE)


def test_render_sidebars_ts_indents_items_under_docs_key():
    toc = [Category("A", [DocItem("X", "x")])]

    out = render_sidebars_ts(toc)

    assert "  docs: [\n" in out
    assert "\n  ],\n} satisfies SidebarsConfig;\n" in out


def test_pages_from_collect_are_accepted():
    pages = collect(FIXTURE)
    toc = parse_toc(
        "## Getting started\n- [Getting Started](getting-started/README.md)\n",
        pages=pages,
        bridge=BRIDGE,
    )
    assert toc == [
        Category("Getting started", [DocItem("Getting Started", "getting-started/README")])
    ]


@pytest.mark.parametrize("indent", [" ", "   ", "    "])
def test_invalid_indentation_is_error(indent):
    text = f"## User guides\n- [User Documentation](users/README.md)\n{indent}- [Chat](users/chat/README.md)\n"
    with pytest.raises(TocError, match=r"docs/TOC\.md:3: (?i:invalid indentation)"):
        parse_toc(text, bridge=BRIDGE)


def test_nested_item_under_link_is_error():
    text = "## A\n- [License](../LICENSE)\n  - [Chat](users/chat/README.md)\n"
    with pytest.raises(TocError, match=r"docs/TOC\.md:3: nested item without a parent"):
        parse_toc(text, bridge=BRIDGE)


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com/page.md",
        "#section",
        "../../outside.md",
    ],
)
def test_rejected_targets_are_error(target):
    text = f"## User guides\n- [User Documentation]({target})\n"
    with pytest.raises(TocError, match=r"docs/TOC\.md:2: unknown link target"):
        parse_toc(text, bridge=BRIDGE)


def test_write_sidebars_ts_writes_file_and_returns_path(tmp_path):
    path = write_sidebars_ts(
        tmp_path, [Category("User guides", [DocItem("User Documentation", "users/README")])]
    )
    assert path == tmp_path / "sidebars.ts"
    assert path.read_text(encoding="utf-8") == render_sidebars_ts(
        [Category("User guides", [DocItem("User Documentation", "users/README")])]
    )


def test_render_versioned_sidebars_is_docs_json_matching_sidebars_ts():
    toc = [Category("A", [DocItem("X", "x"), LinkItem("License", EXTERNAL_LINKS["LICENSE"])])]

    out = render_versioned_sidebars(toc)

    assert json.loads(out) == {"docs": to_sidebar_items(toc)}
    assert out.endswith("}\n")


def test_write_versioned_sidebars_writes_docusaurus_path(tmp_path):
    toc = [Category("A", [DocItem("X", "x")])]

    path = write_versioned_sidebars(tmp_path, "2.0", toc)

    assert path == tmp_path / "versioned_sidebars" / "version-2.0-sidebars.json"
    assert path.read_text(encoding="utf-8") == render_versioned_sidebars(toc)


@pytest.mark.parametrize("version", ["2.0.1", "2", "v2.0", "../2.0"])
def test_write_versioned_sidebars_rejects_non_minor_version(tmp_path, version):
    with pytest.raises(ValueError, match="MAJOR.MINOR"):
        write_versioned_sidebars(tmp_path, version, [])
    assert not (tmp_path / "versioned_sidebars").exists()
