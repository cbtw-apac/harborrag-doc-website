import json
import subprocess
from pathlib import Path

import pytest

from ingest import discover
from ingest.discover import (
    RemoteTag,
    SyncTarget,
    channel_for_version,
    compute_stale_entries,
    expected_targets,
    latest_stable_per_minor,
    newest_minor_lines,
    parse_ls_remote,
    parse_product_tag,
    product_tags,
    remote_branch_sha,
    to_json,
)
from ingest.models import Channel, SyncEntry, SyncState
from ingest.writer import render_sync_state

MAIN_SHA = "a" * 40
OLD_SHA = "b" * 40


def sha(n: int) -> str:
    return f"{n:040x}"


def tag(name: str, n: int) -> RemoteTag:
    version = parse_product_tag(name)
    assert version is not None
    return RemoteTag(name=name, sha=sha(n), version=version)


def state(current_sha: str | None = None, **versions: str) -> SyncState:
    return SyncState(
        current=SyncEntry(label="Next", channel=Channel.MAIN, source_sha=current_sha),
        versions={
            line.replace("_", "."): SyncEntry(
                label=f"{line.replace('_', '.')}.0", channel=Channel.STABLE, source_sha=s
            )
            for line, s in versions.items()
        },
    )


# --------------------------------------------------------------------------- version policy


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("harborrag-v2.0.1", "2.0.1"),
        ("harborrag-v2.1.0a1", "2.1.0a1"),
        ("harborrag-v2.1.0rc2", "2.1.0rc2"),
        ("harborrag-core-v2.0.1", None),
        ("harborrag-mcp-server-v2.0.0a2", None),
        ("qdrant-loader-core-v1.0.1", None),
        ("ocr-sweep/main", None),
        ("v2.0.1", None),
        ("harborrag-v2.0", None),
    ],
)
def test_parse_product_tag(name, expected):
    result = parse_product_tag(name)
    assert (str(result) if result else None) == expected


def test_channel_for_version():
    assert channel_for_version("2.0.1") == Channel.STABLE
    assert channel_for_version("2.1.0a1") == Channel.PRERELEASE
    assert channel_for_version("2.1.0rc1") == Channel.PRERELEASE
    assert channel_for_version("2.1.0.dev3") == Channel.PRERELEASE


def test_newest_minor_lines_sorts_numerically():
    assert newest_minor_lines(["2.9", "2.10", "1.0", "2.10"], 2) == ["2.10", "2.9"]
    assert newest_minor_lines(["2.0"], 0) == []


def test_latest_stable_per_minor_ignores_prereleases():
    tags = [
        tag("harborrag-v2.0.0", 1),
        tag("harborrag-v2.0.1", 2),
        tag("harborrag-v2.0.10", 3),
        tag("harborrag-v2.1.0a1", 4),
        tag("harborrag-v2.1.0rc1", 5),
    ]
    latest = latest_stable_per_minor(tags)
    assert list(latest) == ["2.0"]
    assert latest["2.0"].name == "harborrag-v2.0.10"


# --------------------------------------------------------------------------- ls-remote


LS_REMOTE = f"""\
{sha(10)}\trefs/tags/harborrag-v2.0.0
{sha(11)}\trefs/tags/harborrag-v2.0.0^{{}}
{sha(20)}\trefs/tags/harborrag-v2.0.1
{sha(30)}\trefs/tags/harborrag-core-v2.0.1
{sha(31)}\trefs/tags/harborrag-core-v2.0.1^{{}}
{sha(40)}\trefs/tags/harborrag-v2.1.0a1
{sha(41)}\trefs/tags/harborrag-v2.1.0a1^{{}}
{sha(50)}\trefs/tags/ocr-sweep/main
"""


def test_parse_ls_remote_prefers_peeled_commit():
    refs = parse_ls_remote(LS_REMOTE)
    assert refs["refs/tags/harborrag-v2.0.0"] == sha(11)  # annotated: commit, not tag object
    assert refs["refs/tags/harborrag-v2.0.1"] == sha(20)  # lightweight: single line
    assert not any(ref.endswith("^{}") for ref in refs)


def test_product_tags_filters_and_sorts():
    tags = product_tags(parse_ls_remote(LS_REMOTE))
    assert [t.name for t in tags] == [
        "harborrag-v2.0.0",
        "harborrag-v2.0.1",
        "harborrag-v2.1.0a1",
    ]


def test_product_tags_ignores_branches():
    assert product_tags({"refs/heads/harborrag-v2.0.0": sha(1)}) == []


LS_REMOTE_HEADS = f"""\
{sha(60)}\trefs/heads/feature/main
{MAIN_SHA}\trefs/heads/main
{sha(61)}\trefs/heads/main-old
{sha(62)}\trefs/heads/release/2.0
"""


@pytest.fixture
def fake_heads(monkeypatch):
    """Replace ``ls_remote`` with a stub; returns the list of calls it received."""
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_ls_remote(repo_url, *args):
        calls.append((repo_url, args))
        return LS_REMOTE_HEADS

    monkeypatch.setattr(discover, "ls_remote", fake_ls_remote)
    return calls


def test_remote_branch_sha_returns_main_tip(fake_heads):
    assert remote_branch_sha() == MAIN_SHA
    # One call, heads only, against the default repo
    assert fake_heads == [(discover.DEFAULT_REPO_URL, ("--heads",))]


def test_remote_branch_sha_matches_exact_ref_only(fake_heads):
    # "main" must not pick up refs/heads/main-old or refs/heads/feature/main
    assert remote_branch_sha(branch="main") == MAIN_SHA
    assert remote_branch_sha(branch="main-old") == sha(61)


def test_remote_branch_sha_custom_repo_and_nested_branch(fake_heads):
    url = "https://example.invalid/fork.git"
    assert remote_branch_sha(url, "release/2.0") == sha(62)
    assert fake_heads == [(url, ("--heads",))]


@pytest.mark.parametrize("output", ["", "\n", f"{sha(1)}\trefs/heads/develop\n"])
def test_remote_branch_sha_missing_branch_exits(monkeypatch, output):
    monkeypatch.setattr(discover, "ls_remote", lambda url, *args: output)
    with pytest.raises(SystemExit, match="branch not found on remote: refs/heads/main"):
        remote_branch_sha()


def test_remote_branch_sha_ignores_tag_with_same_name(monkeypatch):
    # A tag called "main" is not the branch, even if ls-remote ever returned it
    monkeypatch.setattr(discover, "ls_remote", lambda url, *args: f"{sha(1)}\trefs/tags/main\n")
    with pytest.raises(SystemExit):
        remote_branch_sha()


def test_remote_branch_sha_propagates_git_failure(monkeypatch):
    def failing_ls_remote(repo_url, *args):
        raise subprocess.CalledProcessError(128, ["git", "ls-remote", *args, repo_url])

    monkeypatch.setattr(discover, "ls_remote", failing_ls_remote)
    with pytest.raises(subprocess.CalledProcessError):
        remote_branch_sha()


# --------------------------------------------------------------------------- expected vs state


def test_expected_targets_without_stable_tags_is_only_next():
    tags = [tag("harborrag-v2.0.0a1", 1), tag("harborrag-v2.0.0a2", 2)]
    assert expected_targets(MAIN_SHA, tags, keep_minors=2) == [
        SyncTarget(
            key="current",
            ref="refs/heads/main",
            sha=MAIN_SHA,
            channel=Channel.MAIN,
            product_version="auto",
            label="Next",
        )
    ]


def test_expected_targets_keeps_newest_minors_oldest_first():
    tags = [
        tag("harborrag-v1.9.0", 1),
        tag("harborrag-v2.0.0", 2),
        tag("harborrag-v2.0.1", 3),
        tag("harborrag-v2.1.0", 4),
        tag("harborrag-v2.2.0a1", 5),
    ]
    targets = expected_targets(MAIN_SHA, tags, keep_minors=2)

    assert [t.key for t in targets] == ["current", "2.0", "2.1"]
    stable = targets[1]
    assert stable == SyncTarget(
        key="2.0",
        ref="refs/tags/harborrag-v2.0.1",
        sha=sha(3),
        channel=Channel.STABLE,
        product_version="2.0.1",
        label="2.0.1",
    )


def test_compute_stale_empty_state_enqueues_everything():
    targets = expected_targets(MAIN_SHA, [tag("harborrag-v2.0.0", 1)], keep_minors=2)
    assert compute_stale_entries(state(), targets) == targets


def test_compute_stale_up_to_date_is_empty():
    targets = expected_targets(MAIN_SHA, [tag("harborrag-v2.0.0", 1)], keep_minors=2)
    assert compute_stale_entries(state(MAIN_SHA, **{"2_0": sha(1)}), targets) == []


def test_compute_stale_detects_moved_main_and_moved_tag():
    targets = expected_targets(
        MAIN_SHA, [tag("harborrag-v2.0.0", 1), tag("harborrag-v2.1.0", 2)], keep_minors=2
    )
    stale = compute_stale_entries(state(OLD_SHA, **{"2_0": sha(1), "2_1": OLD_SHA}), targets)
    assert [t.key for t in stale] == ["current", "2.1"]


def test_compute_stale_next_follows_main_after_prerelease_sync():
    synced = SyncState(
        current=SyncEntry(label="Next", channel=Channel.PRERELEASE, source_sha=OLD_SHA),
        versions={},
    )
    stale = compute_stale_entries(synced, expected_targets(MAIN_SHA, [], keep_minors=2))
    assert [(t.key, t.channel) for t in stale] == [("current", Channel.MAIN)]


def test_to_json_is_one_line_matrix_friendly():
    out = to_json(expected_targets(MAIN_SHA, [tag("harborrag-v2.0.0", 1)], keep_minors=2))
    assert "\n" not in out
    data = json.loads(out)
    assert data[0]["channel"] == "main"
    assert data[1] == {
        "key": "2.0",
        "ref": "refs/tags/harborrag-v2.0.0",
        "sha": sha(1),
        "channel": "stable",
        "product_version": "2.0.0",
        "label": "2.0.0",
    }


# --------------------------------------------------------------------------- CLI


def test_main_prints_stale_json(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "sync-state.json").write_text(render_sync_state(state(OLD_SHA)))

    def fake_ls_remote(repo_url, *args):
        if "--heads" in args:
            return f"{MAIN_SHA}\trefs/heads/main\n"
        return LS_REMOTE

    monkeypatch.setattr(discover, "ls_remote", fake_ls_remote)

    assert discover.main(["--site", str(tmp_path)]) == 0
    captured = capsys.readouterr()
    keys = [t["key"] for t in json.loads(captured.out)]
    assert keys == ["current", "2.0"]
    assert "stale: current" in captured.err
    assert "stale: 2.0" in captured.err


def test_main_reports_no_changes(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "sync-state.json").write_text(render_sync_state(state(MAIN_SHA)))
    monkeypatch.setattr(
        discover,
        "ls_remote",
        lambda url, *args: f"{MAIN_SHA}\trefs/heads/main\n" if "--heads" in args else "",
    )

    discover.main(["--site", str(tmp_path)])
    captured = capsys.readouterr()
    assert json.loads(captured.out) == []
    assert "no changes" in captured.err
