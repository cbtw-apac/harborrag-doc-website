import json
from pathlib import Path, PurePosixPath

import pytest

import ingest
from ingest import writer
from ingest.models import Channel, IngestRequest, SyncEntry, SyncState
from ingest.writer import (
    WriteOutcome,
    WritePlan,
    already_synced,
    format_plan,
    read_sync_state,
    render_sync_state,
    swap_dir,
    target_dir,
    tree_files,
    trees_equal,
    updated_sync_state,
    write,
)

FIXTURE = Path(__file__).parent / "fixtures" / "mini_harborrag"
BAD_FIXTURE = Path(__file__).parent / "fixtures" / "mini_harborrag_bad"
SYNCED_AT = "2026-01-01T00:00:00Z"
LATER = "2026-02-01T00:00:00Z"

EMPTY_STATE = SyncState(
    current=SyncEntry(
        label="Next", channel=Channel.MAIN, source_ref=None, source_sha=None, synced_at=None
    ),
    versions={},
)


@pytest.fixture
def site(tmp_path: Path) -> Path:
    site = tmp_path / "website"
    site.mkdir()

    (site / "docs").mkdir()
    (site / "sidebars.ts").write_text("", encoding="utf-8", newline="\n")
    (site / "sync-state.json").write_text(
        render_sync_state(EMPTY_STATE), encoding="utf-8", newline="\n"
    )
    (site / "versions.json").write_text("[]\n", encoding="utf-8", newline="\n")

    return site


def make_request(site: Path, **overrides) -> IngestRequest:
    fields = {
        "source": FIXTURE,
        "site": site,
        "channel": Channel.MAIN,
        "product_version": "2.1.0",
        "source_ref": "main",
        "source_sha": "abc123",
        **overrides,
    }
    return IngestRequest(**fields)


def staging_leftovers(site: Path) -> list[Path]:
    # rglob: a stable run stages inside versioned_docs/, not at the site root.
    return list(site.rglob(f"{writer.STAGING_PREFIX}*"))


PLAN = WritePlan(
    pages={
        PurePosixPath("getting-started/README.md"): "# Getting started\n",
        PurePosixPath("users/chat/README.md"): "# Chat\n",
    },
    sidebars_ts="export default {};\n",
    sidebars_json='{"docs": []}\n',
)


def stable_request(site: Path, product_version: str, **overrides) -> IngestRequest:
    """A stable-channel request; source_sha defaults to one derived from the version."""
    return make_request(
        site,
        channel=Channel.STABLE,
        product_version=product_version,
        source_ref=f"refs/tags/harborrag-v{product_version}",
        source_sha=overrides.pop("source_sha", f"sha-{product_version}"),
        **overrides,
    )


def snapshot_dir(site: Path, minor: str) -> Path:
    return site / "versioned_docs" / f"version-{minor}"


def snapshot_sidebar(site: Path, minor: str) -> Path:
    return site / "versioned_sidebars" / f"version-{minor}-sidebars.json"


def versions_json(site: Path) -> list[str]:
    return json.loads((site / "versions.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- helpers


def test_target_dir_main_and_prerelease(site: Path):
    assert target_dir(site, Channel.MAIN) == site / "docs"
    assert target_dir(site, Channel.PRERELEASE) == site / "docs"


def test_target_dir_stable_is_versioned_docs(site: Path):
    assert target_dir(site, Channel.STABLE, "2.0") == site / "versioned_docs" / "version-2.0"


def test_target_dir_stable_requires_a_minor_version(site: Path):
    with pytest.raises(ValueError, match="(?i)major.minor"):
        target_dir(site, Channel.STABLE)


@pytest.mark.parametrize("version", ["2.0.1", "2", "v2.0", "latest", "../2.0", "2.01"])
def test_target_dir_stable_rejects_non_minor_version(site: Path, version: str):
    with pytest.raises(ValueError, match="(?i)major.minor"):
        target_dir(site, Channel.STABLE, version)


def test_versioned_sidebars_path_is_docusaurus_path(site: Path):
    assert writer.versioned_sidebars_path(site, "2.0") == snapshot_sidebar(site, "2.0")


def test_sync_state_round_trip(tmp_path):
    state = SyncState(
        current=SyncEntry("Next", Channel.PRERELEASE, "v2.1.0a1", "abc123", SYNCED_AT),
        versions={"2.0": SyncEntry("2.0", Channel.STABLE, "v2.0.1", "def456", SYNCED_AT)},
    )
    (tmp_path / "sync-state.json").write_text(render_sync_state(state), encoding="utf-8")

    assert read_sync_state(tmp_path) == state


def test_render_sync_state_is_deterministic_and_sorted():
    entry = SyncEntry("x", Channel.STABLE, None, None, None)
    a = SyncState(EMPTY_STATE.current, {"2.1": entry, "2.0": entry})
    b = SyncState(EMPTY_STATE.current, {"2.0": entry, "2.1": entry})

    assert render_sync_state(a) == render_sync_state(b)
    assert render_sync_state(a).index('"2.0"') < render_sync_state(a).index('"2.1"')
    assert render_sync_state(a).endswith("}\n")


def test_updated_sync_state_keeps_versions(tmp_path):
    released = SyncEntry("2.0", Channel.STABLE, "v2.0.1", "def456", SYNCED_AT)
    state = SyncState(EMPTY_STATE.current, {"2.0": released})
    request = make_request(tmp_path, channel=Channel.PRERELEASE, source_ref="v2.1.0a1")

    result = updated_sync_state(state, request, synced_at=LATER)

    assert result.versions == {"2.0": released}
    assert result.current == SyncEntry("Next", Channel.PRERELEASE, "v2.1.0a1", "abc123", LATER)


@pytest.mark.parametrize(
    ("current_sha", "request_sha", "force", "expected"),
    [
        ("abc", "abc", False, True),
        ("abc", "abc", True, False),
        ("abc", "def", False, False),
        (None, "abc", False, False),
    ],
)
def test_already_synced(tmp_path, current_sha, request_sha, force, expected):
    state = SyncState(SyncEntry("Next", Channel.MAIN, "main", current_sha, SYNCED_AT), {})
    request = make_request(tmp_path, source_sha=request_sha, force=force)

    assert already_synced(state, request) is expected


def test_trees_equal_detects_extra_and_changed_files(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    writer.write_tree(a, PLAN.pages)
    writer.write_tree(b, PLAN.pages)
    assert trees_equal(a, b)

    (b / "extra.md").write_text("x", encoding="utf-8")
    assert not trees_equal(a, b)

    (b / "extra.md").unlink()
    (b / "users/chat/README.md").write_text("# Chat!\n", encoding="utf-8")
    assert not trees_equal(a, b)


def test_tree_files_of_missing_dir_is_empty(tmp_path):
    assert tree_files(tmp_path / "missing") == {}


def test_swap_dir_replaces_target(tmp_path):
    target, staged = tmp_path / "docs", tmp_path / ".ingest-new"
    (target / "old").mkdir(parents=True)
    (target / "old/page.md").write_text("old", encoding="utf-8")
    writer.write_tree(staged, PLAN.pages)

    swap_dir(staged, target)

    assert set(tree_files(target)) == set(PLAN.pages)
    assert not staged.exists()
    assert staging_leftovers(tmp_path) == []


def test_swap_dir_creates_missing_target(tmp_path):
    target, staged = tmp_path / "docs", tmp_path / ".ingest-new"
    writer.write_tree(staged, PLAN.pages)

    swap_dir(staged, target)

    assert set(tree_files(target)) == set(PLAN.pages)


def test_format_plan_lists_files_sorted(site):
    lines = format_plan(PLAN, site=site, channel=Channel.MAIN).splitlines()

    assert lines == [
        str(site / "docs/getting-started/README.md"),
        str(site / "docs/users/chat/README.md"),
        str(site / "sidebars.ts"),
        str(site / "sync-state.json"),
    ]


# --------------------------------------------------------------------------- write()


def test_first_write(site):
    outcome = write(PLAN, make_request(site), synced_at=SYNCED_AT)

    assert outcome is WriteOutcome.WRITTEN
    assert tree_files(site / "docs") == {p: c.encode() for p, c in PLAN.pages.items()}
    assert (site / "sidebars.ts").read_text(encoding="utf-8") == PLAN.sidebars_ts
    assert read_sync_state(site).current == SyncEntry(
        "Next", Channel.MAIN, "main", "abc123", SYNCED_AT
    )
    assert staging_leftovers(site) == []


def test_dry_run_touches_nothing(site, capsys):
    before = tree_files(site)

    outcome = write(PLAN, make_request(site, dry_run=True), synced_at=SYNCED_AT)

    assert outcome is WriteOutcome.DRY_RUN
    assert tree_files(site) == before
    assert str(site / "docs/users/chat/README.md") in capsys.readouterr().out
    assert staging_leftovers(site) == []


def test_write_then_second_run_has_no_changes(site, capsys):
    """Spec: running twice yields no diff the second time."""
    assert write(PLAN, make_request(site), synced_at=SYNCED_AT) is WriteOutcome.WRITTEN
    after_first = tree_files(site)
    capsys.readouterr()

    outcome = write(PLAN, make_request(site, force=True), synced_at=LATER)

    assert outcome is WriteOutcome.NO_CHANGES
    assert "no changes" in capsys.readouterr().out
    assert tree_files(site) == after_first  # synced_at not bumped either
    assert staging_leftovers(site) == []


def test_already_synced_without_force(site, capsys):
    write(PLAN, make_request(site), synced_at=SYNCED_AT)
    after_first = tree_files(site)
    capsys.readouterr()

    outcome = write(PLAN, make_request(site), synced_at=LATER)

    assert outcome is WriteOutcome.ALREADY_SYNCED
    assert capsys.readouterr().out.startswith("no changes")
    assert tree_files(site) == after_first


def test_new_sha_with_same_content_is_no_changes(site):
    write(PLAN, make_request(site), synced_at=SYNCED_AT)

    outcome = write(PLAN, make_request(site, source_sha="def456"), synced_at=LATER)

    assert outcome is WriteOutcome.NO_CHANGES
    assert read_sync_state(site).current.source_sha == "abc123"


def test_write_leaves_versions_json_untouched(site):
    (site / "versions.json").write_text('["2.0"]\n', encoding="utf-8")

    write(PLAN, make_request(site), synced_at=SYNCED_AT)

    assert (site / "versions.json").read_text(encoding="utf-8") == '["2.0"]\n'


def test_removed_page_disappears(site):
    write(PLAN, make_request(site), synced_at=SYNCED_AT)
    smaller = WritePlan(
        pages={PurePosixPath("getting-started/README.md"): "# Getting started\n"},
        sidebars_ts=PLAN.sidebars_ts,
    )

    outcome = write(smaller, make_request(site, source_sha="def456"), synced_at=LATER)

    assert outcome is WriteOutcome.WRITTEN
    assert not (site / "docs/users/chat/README.md").exists()
    assert set(tree_files(site / "docs")) == set(smaller.pages)


def test_failure_while_staging_leaves_target_untouched(site, monkeypatch):
    """Spec: a failure mid-write leaves the target untouched (temp-dir swap)."""
    write(PLAN, make_request(site), synced_at=SYNCED_AT)
    before = tree_files(site)

    def broken_write_tree(root, pages):
        (root / "half.md").write_text("half", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(writer, "write_tree", broken_write_tree)

    with pytest.raises(OSError, match="disk full"):
        write(PLAN, make_request(site, source_sha="def456"), synced_at=LATER)

    assert tree_files(site) == before
    assert staging_leftovers(site) == []


def test_run_twice_on_fixture_has_no_diff(site):
    """Spec: running twice on the fixture yields no diff the second time."""
    assert ingest.run(make_request(site)) is WriteOutcome.WRITTEN
    after_first = tree_files(site)

    assert PurePosixPath("docs/project/overview.md") in after_first
    assert PurePosixPath("docs/packages/demo.md") in after_first

    assert ingest.run(make_request(site, force=True)) is WriteOutcome.NO_CHANGES
    assert tree_files(site) == after_first


def test_failing_guard_leaves_target_untouched(site):
    """Spec: a failing guard leaves the target untouched."""
    ingest.run(make_request(site))
    before = tree_files(site)

    with pytest.raises(ValueError, match="Publication denied"):
        ingest.run(make_request(site, source=BAD_FIXTURE, source_sha="bad"))

    assert tree_files(site) == before
    assert staging_leftovers(site) == []


# --------------------------------------------------------------------------- stable channel


def test_stable_write_creates_the_snapshot(site):
    outcome = write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)

    assert outcome is WriteOutcome.WRITTEN
    assert tree_files(snapshot_dir(site, "2.0")) == {p: c.encode() for p, c in PLAN.pages.items()}
    # read_bytes, not read_text: read_text would hide a CRLF file.
    assert snapshot_sidebar(site, "2.0").read_bytes() == PLAN.sidebars_json.encode()
    assert versions_json(site) == ["2.0"]
    assert read_sync_state(site).versions["2.0"] == SyncEntry(
        "2.0.0", Channel.STABLE, "refs/tags/harborrag-v2.0.0", "sha-2.0.0", SYNCED_AT
    )
    assert staging_leftovers(site) == []


def test_stable_write_leaves_next_alone(site):
    """A snapshot must not touch docs/ or sidebars.ts: those belong to Next."""
    write(PLAN, make_request(site), synced_at=SYNCED_AT)
    next_docs = tree_files(site / "docs")
    next_current = read_sync_state(site).current

    write(PLAN, stable_request(site, "2.0.0"), synced_at=LATER)

    assert tree_files(site / "docs") == next_docs
    assert (site / "sidebars.ts").read_text(encoding="utf-8") == PLAN.sidebars_ts
    assert read_sync_state(site).current == next_current


def test_two_stable_ingests_list_both_newest_first(site):
    """Spec 5.1: two stable ingests (2.0 then 2.1) produce ["2.1", "2.0"]."""
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    write(PLAN, stable_request(site, "2.1.0"), synced_at=LATER)

    assert versions_json(site) == ["2.1", "2.0"]
    assert snapshot_dir(site, "2.0").is_dir()
    assert snapshot_dir(site, "2.1").is_dir()
    assert set(read_sync_state(site).versions) == {"2.0", "2.1"}


def test_third_stable_ingest_prunes_the_oldest(site):
    """Spec 5.1: a third (2.2) prunes 2.0 and deletes its folder."""
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)

    outcome = write(PLAN, stable_request(site, "2.2.0", keep_minors=2), synced_at=LATER)

    assert outcome is WriteOutcome.WRITTEN
    assert versions_json(site) == ["2.2", "2.1"]
    assert not snapshot_dir(site, "2.0").exists()
    assert not snapshot_sidebar(site, "2.0").exists()
    assert set(read_sync_state(site).versions) == {"2.1", "2.2"}
    assert staging_leftovers(site) == []


def test_patch_release_overwrites_its_minor_and_relabels(site):
    """Spec 5.1: a patch (2.1.1) overwrites version-2.1 and relabels."""
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)
    patched = WritePlan(
        pages={PurePosixPath("getting-started/README.md"): "# Patched\n"},
        sidebars_ts=PLAN.sidebars_ts,
        sidebars_json=PLAN.sidebars_json,
    )

    outcome = write(patched, stable_request(site, "2.1.1"), synced_at=LATER)

    assert outcome is WriteOutcome.WRITTEN
    assert versions_json(site) == ["2.1", "2.0"]  # no new dropdown entry
    assert set(tree_files(snapshot_dir(site, "2.1"))) == set(patched.pages)
    entry = read_sync_state(site).versions["2.1"]
    assert entry.label == "2.1.1"
    assert entry.source_sha == "sha-2.1.1"


def test_stable_rerun_on_same_sha_is_already_synced(site, capsys):
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    after_first = tree_files(site)
    capsys.readouterr()

    outcome = write(PLAN, stable_request(site, "2.0.0"), synced_at=LATER)

    assert outcome is WriteOutcome.ALREADY_SYNCED
    assert tree_files(site) == after_first


def test_stable_is_not_confused_by_the_next_sha(site):
    """A tag whose commit Next already sits on must still produce a snapshot."""
    write(PLAN, make_request(site, source_sha="shared"), synced_at=SYNCED_AT)

    outcome = write(
        PLAN, stable_request(site, "2.0.0", source_sha="shared"), synced_at=LATER
    )

    assert outcome is WriteOutcome.WRITTEN
    assert versions_json(site) == ["2.0"]


def test_stable_rerun_with_force_and_same_content_is_no_changes(site, capsys):
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    after_first = tree_files(site)
    capsys.readouterr()

    outcome = write(PLAN, stable_request(site, "2.0.0", force=True), synced_at=LATER)

    assert outcome is WriteOutcome.NO_CHANGES
    assert "no changes" in capsys.readouterr().out
    assert tree_files(site) == after_first


def test_stable_dry_run_touches_nothing(site, capsys):
    before = tree_files(site)

    outcome = write(PLAN, stable_request(site, "2.0.0", dry_run=True), synced_at=SYNCED_AT)

    assert outcome is WriteOutcome.DRY_RUN
    assert tree_files(site) == before
    out = capsys.readouterr().out
    assert str(snapshot_dir(site, "2.0") / "users/chat/README.md") in out
    assert str(site / "versions.json") in out
    assert str(site / "sidebars.ts") not in out


def test_format_plan_stable_lists_versioned_paths(site):
    lines = format_plan(PLAN, site=site, channel=Channel.STABLE, minor="2.0").splitlines()

    assert lines == sorted(
        [
            str(snapshot_dir(site, "2.0") / "getting-started/README.md"),
            str(snapshot_dir(site, "2.0") / "users/chat/README.md"),
            str(snapshot_sidebar(site, "2.0")),
            str(site / "sync-state.json"),
            str(site / "versions.json"),
        ]
    )


def test_stable_run_twice_on_fixture_has_no_diff(site):
    """Idempotency, end to end through the real pipeline."""
    assert ingest.run(stable_request(site, "2.0.0")) is WriteOutcome.WRITTEN
    after_first = tree_files(site)

    assert PurePosixPath("versioned_docs/version-2.0/project/overview.md") in after_first
    assert PurePosixPath("versioned_sidebars/version-2.0-sidebars.json") in after_first

    assert ingest.run(stable_request(site, "2.0.0", force=True)) is WriteOutcome.NO_CHANGES
    assert tree_files(site) == after_first


def test_stable_backfill_that_would_prune_itself_is_rejected(site):
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)
    write(PLAN, stable_request(site, "2.2.0"), synced_at=SYNCED_AT)
    before = tree_files(site)

    with pytest.raises(ValueError, match="older than"):
        write(PLAN, stable_request(site, "1.9.0", keep_minors=2), synced_at=LATER)

    assert tree_files(site) == before
    assert staging_leftovers(site) == []


def test_patch_release_with_unchanged_docs_still_relabels(site):
    """A patch that only changes code (2.1.0 -> 2.1.1) must still relabel the dropdown."""
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)

    outcome = write(PLAN, stable_request(site, "2.1.1"), synced_at=LATER)

    assert outcome is WriteOutcome.WRITTEN
    entry = read_sync_state(site).versions["2.1"]
    assert (entry.label, entry.source_sha) == ("2.1.1", "sha-2.1.1")
    assert versions_json(site) == ["2.1"]


@pytest.mark.parametrize(
    ("label", "sha", "expected"),
    [
        ("2.0.0", "sha-2.0.0", True),
        ("2.0.0", "other", False),
        ("2.0.1", "sha-2.0.0", False),  # two tags on one commit: still relabel
    ],
)
def test_already_synced_stable_compares_its_own_entry(tmp_path, label, sha, expected):
    entry = SyncEntry("2.0.0", Channel.STABLE, "refs/tags/harborrag-v2.0.0", "sha-2.0.0", SYNCED_AT)
    state = SyncState(EMPTY_STATE.current, {"2.0": entry})

    request = stable_request(tmp_path, label, source_sha=sha)

    assert already_synced(state, request) is expected


def test_stable_write_drops_orphan_state_entries(site):
    """An entry left by a crash between versions.json and sync-state.json is cleaned up."""
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)
    orphan = SyncEntry("1.9.0", Channel.STABLE, "refs/tags/harborrag-v1.9.0", "sha-1.9.0", SYNCED_AT)
    state = read_sync_state(site)
    (site / "sync-state.json").write_text(
        render_sync_state(SyncState(state.current, {**state.versions, "1.9": orphan})),
        encoding="utf-8",
        newline="\n",
    )

    outcome = write(PLAN, stable_request(site, "2.1.0", force=True), synced_at=LATER)

    assert outcome is WriteOutcome.WRITTEN
    assert set(read_sync_state(site).versions) == {"2.1"}


def test_stable_write_requires_versioned_sidebar(site):
    no_json = WritePlan(pages=PLAN.pages, sidebars_ts=PLAN.sidebars_ts)
    before = tree_files(site)

    with pytest.raises(ValueError, match="sidebars_json"):
        write(no_json, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)

    assert tree_files(site) == before


def test_stable_dry_run_lists_pruned_snapshots(site, capsys):
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    write(PLAN, stable_request(site, "2.1.0"), synced_at=SYNCED_AT)
    before = tree_files(site)
    capsys.readouterr()

    write(PLAN, stable_request(site, "2.2.0", dry_run=True), synced_at=LATER)

    out = capsys.readouterr().out.splitlines()
    assert f"delete {snapshot_dir(site, '2.0')}/" in out
    assert f"delete {snapshot_sidebar(site, '2.0')}" in out
    assert tree_files(site) == before


def test_next_write_after_snapshot_leaves_versioned_files_alone(site):
    write(PLAN, stable_request(site, "2.0.0"), synced_at=SYNCED_AT)
    versioned = tree_files(site / "versioned_docs"), tree_files(site / "versioned_sidebars")
    before_versions = (site / "versions.json").read_bytes()

    write(PLAN, make_request(site), synced_at=LATER)

    assert (tree_files(site / "versioned_docs"), tree_files(site / "versioned_sidebars")) == versioned
    assert (site / "versions.json").read_bytes() == before_versions
    assert read_sync_state(site).versions["2.0"].label == "2.0.0"