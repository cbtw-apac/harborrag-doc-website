from pathlib import Path

import pytest

from ingest.versions import (
    minor,
    plan_versions,
    read_versions,
    render_versions,
    sort_minors,
)

# --------------------------------------------------------------------------- minor()


@pytest.mark.parametrize(
    ("product_version", "expected"),
    [
        ("2.0.0", "2.0"),
        ("2.0.1", "2.0"),
        ("2.1.0a1", "2.1"),
        ("2.10.3", "2.10"),
        ("10.0.0", "10.0"),
        ("2.0", "2.0"),
        ("v2.0.0", "2.0"),  # PEP 440 permits the "v" prefix
    ],
)
def test_minor_collapses_patches(product_version: str, expected: str):
    assert minor(product_version) == expected


@pytest.mark.parametrize("bad", ["", "latest", "2.x", "main"])
def test_minor_rejects_non_versions(bad: str):
    with pytest.raises(ValueError, match="not a version"):
        minor(bad)


# --------------------------------------------------------------------------- sort_minors()


def test_sort_minors_is_newest_first():
    assert sort_minors(["2.0", "2.1", "1.9"]) == ["2.1", "2.0", "1.9"]


def test_sort_minors_orders_numerically_not_lexicographically():
    """A string sort puts "2.9" above "2.10"; versions.json[0] is lastVersion."""
    assert sort_minors(["2.9", "2.10"]) == ["2.10", "2.9"]
    assert sort_minors(["2.9", "2.10", "3.0"]) == ["3.0", "2.10", "2.9"]


def test_sort_minors_deduplicates():
    assert sort_minors(["2.0", "2.0", "2.1"]) == ["2.1", "2.0"]


@pytest.mark.parametrize("bad", ["2.0.1", "2", "v2.0", "latest"])
def test_sort_minors_rejects_non_minor_labels(bad: str):
    with pytest.raises(ValueError, match="(?i)major.minor"):
        sort_minors([bad])


# --------------------------------------------------------------------------- versions.json


def test_read_versions_of_missing_file_is_empty(tmp_path: Path):
    assert read_versions(tmp_path) == []


def test_read_versions_round_trips_render(tmp_path: Path):
    (tmp_path / "versions.json").write_text(render_versions(["2.1", "2.0"]), encoding="utf-8")

    assert read_versions(tmp_path) == ["2.1", "2.0"]


def test_render_versions_is_json_with_trailing_newline():
    assert render_versions(["2.1", "2.0"]) == '[\n  "2.1",\n  "2.0"\n]\n'
    assert render_versions([]) == "[]\n"


@pytest.mark.parametrize("content", ['{"2.0": 1}', '["2.0.1"]', "[2]", '["latest"]'])
def test_read_versions_rejects_malformed_files(tmp_path: Path, content: str):
    (tmp_path / "versions.json").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        read_versions(tmp_path)


# --------------------------------------------------------------------------- plan_versions()


def test_plan_versions_adds_the_first_minor():
    assert plan_versions([], "2.0", keep_minors=2) == (["2.0"], [])


def test_plan_versions_adds_a_second_minor_newest_first():
    assert plan_versions(["2.0"], "2.1", keep_minors=2) == (["2.1", "2.0"], [])


def test_plan_versions_prunes_the_oldest_beyond_keep_minors():
    assert plan_versions(["2.1", "2.0"], "2.2", keep_minors=2) == (["2.2", "2.1"], ["2.0"])


def test_plan_versions_reingesting_the_same_minor_is_not_a_change():
    """A patch release (2.1.1 -> minor 2.1) must not add a dropdown entry."""
    assert plan_versions(["2.1", "2.0"], "2.1", keep_minors=2) == (["2.1", "2.0"], [])


def test_plan_versions_prunes_several_at_once():
    kept, dropped = plan_versions(["2.2", "2.1", "2.0"], "2.3", keep_minors=2)

    assert kept == ["2.3", "2.2"]
    assert sorted(dropped) == ["2.0", "2.1"]


def test_plan_versions_keep_one_replaces_the_line():
    assert plan_versions(["2.0"], "2.1", keep_minors=1) == (["2.1"], ["2.0"])


def test_plan_versions_rejects_a_new_minor_that_would_be_pruned_immediately():
    """Back-filling an old line with no room for it is a mistake, not a silent no-op."""
    with pytest.raises(ValueError, match="older than"):
        plan_versions(["2.2", "2.1"], "1.9", keep_minors=2)


@pytest.mark.parametrize("keep", [0, -1])
def test_plan_versions_rejects_keep_minors_below_one(keep: int):
    with pytest.raises(ValueError, match="at least 1"):
        plan_versions([], "2.0", keep_minors=keep)
