from pathlib import Path, PurePosixPath

import yaml

from ingest.frontmatter import (
    EDIT_URL_BASE,
    HIDDEN_SIDEBAR_CLASS,
    apply_frontmatter,
    build_frontmatter,
    extract_description,
    extract_title,
    fallback_title,
    render,
    sidebar_positions,
)
from ingest.models import Doc
from ingest.toc import Category, DocItem, LinkItem

SRC = PurePosixPath("docs/users/chat/models.md")


# --------------------------------------------------------------------------- title


def test_h1_with_trailing_content():
    body = "# Chat Models (beta) `v2`  #\n\nIntro paragraph.\n"

    title, rest = extract_title(body, source_path=SRC)

    assert title == "Chat Models (beta) v2"
    assert rest == "Intro paragraph.\n"


def test_h1_inside_code_fence_is_ignored():
    body = "Intro.\n\n```bash\n# not a title\n```\n\n# Real Title\n\nText.\n"

    title, rest = extract_title(body, source_path=SRC)

    assert title == "Real Title"
    assert "# not a title" in rest
    assert "Intro" in rest
    assert "Text" in rest
    assert "# Real Title" not in rest


def test_no_h1_falls_back_to_filename():
    body = "## Only a subheading\n\nText.\n"

    title, rest = extract_title(body, source_path=PurePosixPath("docs/users/ingestion-modes.md"))

    assert title == "Ingestion Modes"
    assert rest == body


def test_fallback_title():
    assert fallback_title(PurePosixPath("docs/getting-started/quick_start.md")) == "Quick Start"
    assert fallback_title(PurePosixPath("README.md")) == "Overview"
    assert fallback_title(PurePosixPath("docs/users/chat/README.md")) == "Chat"


def test_last_reviewed_footer_is_preserved():
    body = "# Title\n\nIntro.\n\n## Section\n\nMore.\n\nLast reviewed: 2026-08-27\n"

    _, rest = extract_title(body, source_path=SRC)

    assert rest.rstrip().endswith("Last reviewed: 2026-08-27")


# --------------------------------------------------------------------------- description


def test_description_first_paragraph_flattened():
    body = "[![badge](x.svg)](y)\n\nHarborRAG is a **RAG** [engine](e.md) for\n`docs`.\n\nSecond.\n"
    body_2 = "<p>x</p>\n\n---\n\n> note\n\nReal prose.\n"
    assert extract_description(body) == "HarborRAG is a RAG engine for docs."
    assert extract_description(body_2) == "Real prose."


def test_description_truncated_to_160():
    body = ("word " * 100).strip() + "\n"

    desc = extract_description(body)

    assert desc is not None
    assert len(desc) <= 160
    assert desc.endswith("…")
    assert not desc[:-1].endswith(" ")


def test_description_none_without_prose():
    assert extract_description("## Heading\n\n- a\n- b\n") is None


# --------------------------------------------------------------------------- sidebar


def test_sidebar_positions_follow_toc_order():
    toc = [
        Category("A", [DocItem("One", "a/one"), LinkItem("L", "https://x")]),
        Category("B", [DocItem("Two", "b/two", items=[DocItem("Three", "b/three")])]),
    ]

    assert sidebar_positions(toc) == {"a/one": 1, "b/two": 2, "b/three": 3}


# --------------------------------------------------------------------------- assemble


def test_build_frontmatter_in_toc():
    fm = build_frontmatter(
        title="T", description="D", position=3, source_path=SRC, source_sha="abc123"
    )

    assert list(fm) == [
        "title",
        "description",
        "sidebar_position",
        "custom_edit_url",
        "source_path",
        "source_sha",
    ]
    assert fm["custom_edit_url"] == EDIT_URL_BASE + SRC.as_posix()


def test_build_frontmatter_not_in_toc_is_hidden():
    fm = build_frontmatter(
        title="T", description=None, position=None, source_path=SRC, source_sha="abc123"
    )

    assert "sidebar_position" not in fm
    assert "description" not in fm
    assert fm["sidebar_class_name"] == HIDDEN_SIDEBAR_CLASS


def test_apply_and_render_round_trip():
    doc = Doc(
        source_path=Path(SRC),
        target_path=Path("users/chat/models.md"),
        title="",
        body="# Chat: Models\n\nPick a model.\n\nLast reviewed: 2026-08-27\n",
        frontmatter={},
    )

    apply_frontmatter(doc, positions={"users/chat/models": 7}, source_sha="abc123")
    out = render(doc)

    _, fm_text, body = out.split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    assert fm["title"] == "Chat: Models"
    assert fm["sidebar_position"] == 7
    assert fm["source_sha"] == "abc123"
    assert body.lstrip("\n").startswith("Pick a model.")
    assert out.endswith("Last reviewed: 2026-08-27\n")
