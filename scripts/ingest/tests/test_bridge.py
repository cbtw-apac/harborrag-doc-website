from pathlib import Path

import pytest

from ingest.bridge import (
    PackageFacts,
    bridge_doc,
    bridge_docs,
    bridge_ids,
    bridge_mapping,
    bridge_target,
    facts_table,
    prepend_facts,
    read_package_facts,
)
from ingest.collect import collect
from ingest.frontmatter import apply_frontmatter

FIXTURE = Path(__file__).parent / "fixtures" / "mini_harborrag"
FACTS = PackageFacts(name="demo", version="1.2.3", description="A demo package")


# --------------------------------------------------------------------------- route


@pytest.mark.parametrize(
    ("source_path", "expected"),
    [
        ("README.md", "project/overview.md"),
        ("CONTRIBUTING.md", "project/contributing.md"),
        ("SECURITY.md", "project/security.md"),
        ("CHANGELOG.md", "project/changelog.md"),
        ("packages/demo/README.md", "packages/demo.md"),
        ("packages/demo/docs/README.md", None),
        ("packages/demo/pyproject.toml", None),
        ("docs/users/guide.md", None),
        ("NOTES.md", None),
    ],
)
def test_bridge_target(source_path, expected):
    result = bridge_target(Path(source_path))
    if expected is not None:
        assert result == Path(expected)
    else:
        assert result == expected


def test_bridge_ids_feed_the_toc():
    expected_result = {
        "README.md": "project/overview",
        "CONTRIBUTING.md": "project/contributing",
        "SECURITY.md": "project/security",
        "CHANGELOG.md": "project/changelog",
        "packages/demo/README.md": "packages/demo",
    }

    result = bridge_ids(collect(FIXTURE))
    assert result == expected_result
    assert result.get("pyproject.toml") is None
    assert not any("docs/" in key for key in result)


def test_bridge_mapping_values_are_target_paths():
    assert bridge_mapping([Path("SECURITY.md")]) == {Path("SECURITY.md"): "project/security.md"}


# --------------------------------------------------------------------------- facts


def test_read_package_facts_from_fixture():
    result = read_package_facts(FIXTURE / "packages/demo/pyproject.toml")
    assert result.name == "harborrag"
    assert result.version == "2.0.0a1"
    assert result.description == ""


def test_read_package_facts_requires_version(tmp_path):
    tmp_path.joinpath("pyproject.toml").write_text(
        '[project]\nname = "x"\n',
        encoding="utf-8",
    )
    pyproject_path = tmp_path / "pyproject.toml"

    with pytest.raises(KeyError, match="version"):
        read_package_facts(pyproject_path)


def test_read_package_facts_requires_name(tmp_path):
    tmp_path.joinpath("pyproject.toml").write_text(
        '[project]\nversion = "x"\n',
        encoding="utf-8",
    )
    pyproject_path = tmp_path / "pyproject.toml"

    with pytest.raises(KeyError, match="name"):
        read_package_facts(pyproject_path)


def test_facts_table_rows():
    result_1 = facts_table(PackageFacts("demo", "1.0", ""))
    expected_1 = """| | |
| --- | --- |
| Package | `demo` |
| Version | `1.0` |
| PyPI | [demo](https://pypi.org/project/demo/) |
"""
    result_2 = facts_table(PackageFacts("demo", "1.0", "comment"))
    expected_2 = """| | |
| --- | --- |
| Package | `demo` |
| Version | `1.0` |
| Description | comment |
| PyPI | [demo](https://pypi.org/project/demo/) |
"""

    assert result_1 == expected_1
    assert result_2 == expected_2
    assert "| Description |" not in result_1
    assert "| Description | comment |" in result_2
    assert r"\|" in facts_table(PackageFacts("demo", "1.0", "a|b"))


def test_prepend_facts_goes_after_h1():
    assert (
        prepend_facts("# demo\n\nIntro.\n", FACTS)
        == "# demo\n\n" + facts_table(FACTS) + "\nIntro.\n"
    )
    assert (
        prepend_facts("# demo\nIntro.\n", FACTS) == "# demo\n\n" + facts_table(FACTS) + "\nIntro.\n"
    )


def test_prepend_facts_ignores_hash_in_code_fence():
    text = "```bash\n # comment\n```\n\n# demo\n\nIntro.\n"
    assert (
        prepend_facts(text, FACTS)
        == "```bash\n # comment\n```\n\n# demo\n\n" + facts_table(FACTS) + "\nIntro.\n"
    )


def test_prepend_facts_without_h1_goes_on_top():
    assert prepend_facts("Intro.\n", FACTS) == facts_table(FACTS) + "\nIntro.\n"


# --------------------------------------------------------------------------- docs


def test_bridge_docs_from_fixture():
    docs = bridge_docs(FIXTURE, collect(FIXTURE))
    target_paths = {doc.target_path for doc in docs}
    source_paths = {doc.source_path for doc in docs}

    assert target_paths == {
        Path("project/overview.md"),
        Path("project/contributing.md"),
        Path("project/security.md"),
        Path("project/changelog.md"),
        Path("packages/demo.md"),
    }
    assert source_paths == {
        Path("README.md"),
        Path("CONTRIBUTING.md"),
        Path("SECURITY.md"),
        Path("CHANGELOG.md"),
        Path("packages/demo/README.md"),
    }
    assert any("| Package | `harborrag` |" in doc.body for doc in docs)


def test_bridged_doc_goes_through_frontmatter():
    doc = apply_frontmatter(
        bridge_doc(FIXTURE, Path("packages/demo/README.md")),
        positions={"packages/demo": 3},
        source_sha="abc",
    )

    assert doc.frontmatter["sidebar_position"] == 3
    assert doc.frontmatter["source_path"] == "packages/demo/README.md"
    assert not doc.frontmatter["description"].startswith("|")
