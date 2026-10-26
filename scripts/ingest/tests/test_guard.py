from pathlib import Path

import pytest

from ingest.collect import collect
from ingest.guard import branding, load_deny_patterns, publication
from ingest.models import Doc

FIXTURE_GOOD = Path(__file__).parent / "fixtures" / "mini_harborrag"
FIXTURE_BAD = Path(__file__).parent / "fixtures" / "mini_harborrag_bad"
DENY = Path(__file__).parent.parent / "deny.txt"


def test_publication_passes_when_clean():
    deny = load_deny_patterns(DENY)
    files = collect(FIXTURE_GOOD)
    result = publication(FIXTURE_GOOD, files, deny)

    assert result is None


def test_publication_rejects_denied_files_and_content():
    deny = load_deny_patterns(DENY)
    files = collect(FIXTURE_BAD)

    with pytest.raises(ValueError) as exc:
        publication(FIXTURE_BAD, files, deny)

    assert "HARBORRAG_ARCHITECTURE.md" in str(exc.value)
    assert "README.md" in str(exc.value)
    assert "OLD_HARBORRAG_ARCHITECTURE.md" in str(exc.value)


def test_branding_passes_when_clean() -> None:
    docs = [
        Doc(
            source_path=Path("docs/README.md"),
            target_path=Path("README.md"),
            title="HarborRAG",
            body="Welcome to HarborRAG.",
            frontmatter={},
        )
    ]

    branding(docs)


def test_branding_fails_when_forbidden_branding_present() -> None:
    docs = [
        Doc(
            source_path=Path("docs/README.md"),
            target_path=Path("README.md"),
            title="HarborRAG",
            body="""Welcome to HarborRAG.
This project was migrated from Qdrant Loader.
""",
            frontmatter={},
        )
    ]

    with pytest.raises(ValueError) as exc:
        branding(docs)

    message = str(exc.value)

    assert "docs/README.md" in message
    assert "Qdrant Loader" in message


def test_branding_ignores_compatibility_exemption() -> None:
    docs = [
        Doc(
            source_path=Path("docs/README.md"),
            target_path=Path("README.md"),
            title="Migration",
            body="""
<!-- branding-compat -->
Qdrant Loader
""",
            frontmatter={},
        )
    ]

    branding(docs)


def test_branding_reports_all_failures() -> None:
    docs = [
        Doc(
            source_path=Path("docs/one.md"),
            target_path=Path("one.md"),
            title="",
            body="Qdrant Loader",
            frontmatter={},
        ),
        Doc(
            source_path=Path("docs/two.md"),
            target_path=Path("two.md"),
            title="",
            body="martin-papy",
            frontmatter={},
        ),
    ]

    with pytest.raises(ValueError) as exc:
        branding(docs)

    message = str(exc.value)

    assert "docs/one.md" in message
    assert "Qdrant Loader" in message

    assert "docs/two.md" in message
    assert "martin-papy" in message


def test_load_deny_patterns(tmp_path) -> None:
    doc = tmp_path / "index.txt"
    doc.write_text(r"""
# Comment
HARBORRAG_ARCHITECTURE\.md
""")

    patterns = load_deny_patterns(doc)

    assert len(patterns) == 1
    assert patterns[0].search("HARBORRAG_ARCHITECTURE.md")
