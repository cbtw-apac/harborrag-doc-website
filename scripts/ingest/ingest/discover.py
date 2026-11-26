"""Find the docs versions that are out of date (used by the nightly cron in sync.yml).

The site should always hold:

    current  -> tip of HarborRAG ``main``              ("Next" follows main)
    "X.Y"    -> newest stable ``harborrag-vX.Y.Z`` tag, for the newest ``keep_minors`` lines

``discover_stale`` compares that expected set with ``sync-state.json`` and returns
the entries whose state is missing or points at another commit. Pre-release tags are
never part of the expected set: they are published through ``Next``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from ingest.models import Channel, SyncEntry, SyncState
from ingest.versions import minor, sort_minors
from ingest.writer import read_sync_state

DEFAULT_REPO_URL = "https://github.com/cbtw-apac/HarborRAG.git"
MAIN_BRANCH = "main"
CURRENT_KEY = "current"

# Product-wide release tags only. Package tags (harborrag-core-v2.0.0) and
# unrelated tags (qdrant-loader-core-v1.0.1, ocr-sweep/main) are ignored.
PRODUCT_TAG_RE = re.compile(r"^harborrag-v(?P<version>\d+\.\d+\.\d+\S*)$")

TAGS_PREFIX = "refs/tags/"
HEADS_PREFIX = "refs/heads/"
PEELED_SUFFIX = "^{}"


@dataclass(frozen=True)
class RemoteTag:
    """A HarborRAG product release tag as seen on the remote."""

    name: str  # "harborrag-v2.0.1"
    sha: str  # commit sha (peeled for annotated tags)
    version: Version


@dataclass(frozen=True)
class SyncTarget:
    """One ingest run. Field names match what the Reconcile step in sync.yml reads."""

    key: str  # "current" or "X.Y" - the sync-state.json slot this run writes
    ref: str  # "refs/heads/main" | "refs/tags/harborrag-v2.0.1"
    sha: str
    channel: Channel
    product_version: str  # "auto" for main (read from pyproject), else "X.Y.Z"
    label: str  # label sync-state.json gets: "Next" or "X.Y.Z"


# --------------------------------------------------------------------------- version policy


def parse_product_tag(tag: str) -> Version | None:
    """Return the version of a product release tag, or ``None`` for any other tag.

    Only ``harborrag-vX.Y.Z[suffix]`` counts. Package tags, tags of other projects
    and tags whose suffix is not valid PEP 440 are rejected.

    Args:
        tag: Tag name without ``refs/tags/``, e.g. ``"harborrag-v2.1.0a1"``.

    Returns:
        The parsed version, or ``None`` when the tag is not a product release.

    >>> parse_product_tag("harborrag-v2.0.1")
    <Version('2.0.1')>
    >>> parse_product_tag("harborrag-core-v2.0.1") is None
    True
    """
    match = PRODUCT_TAG_RE.match(tag)
    if match is None:
        return None
    try:
        return Version(match["version"])
    except InvalidVersion:
        return None


def channel_for_version(version: Version | str) -> Channel:
    """Return the channel a released version publishes to.

    Pre-releases (``a``, ``b``, ``rc``, ``.dev``) go to ``PRERELEASE`` (the Next
    docs); final releases go to ``STABLE`` (a versioned snapshot).

    Raises:
        packaging.version.InvalidVersion: ``version`` is a string that is not PEP 440.
    """
    return Channel.PRERELEASE if Version(str(version)).is_prerelease else Channel.STABLE


def newest_minor_lines(lines: Iterable[str], keep_minors: int) -> list[str]:
    """Return the ``keep_minors`` newest ``"X.Y"`` lines, newest first.

    Lines are compared as versions, so ``"2.10"`` is newer than ``"2.9"``. Duplicates
    are removed. The order matches ``versions.json``.

    Args:
        lines: Minor lines, in any order.
        keep_minors: How many lines to keep (``--keep-minors``). ``0`` or less keeps none.
    """
    if keep_minors <= 0:
        return []
    return sort_minors(lines)[:keep_minors]


def latest_stable_per_minor(tags: Iterable[RemoteTag]) -> dict[str, RemoteTag]:
    """Return the newest stable tag of each minor line.

    Pre-release tags are skipped. Tags are compared by version, so the input
    order does not matter.

    Returns:
        ``{"2.0": <harborrag-v2.0.1>, "2.1": <harborrag-v2.1.0>, ...}``.
    """
    latest: dict[str, RemoteTag] = {}

    for tag in tags:
        if channel_for_version(tag.version) != Channel.STABLE:
            continue

        line = minor(str(tag.version))
        if line not in latest or tag.version > latest[line].version:
            latest[line] = tag

    return latest


# --------------------------------------------------------------------------- git ls-remote


def parse_ls_remote(output: str) -> dict[str, str]:
    """Parse ``git ls-remote`` output into ``{ref: commit sha}``.

    For an annotated tag the peeled ``ref^{}`` line (the commit) wins over the
    tag object's own sha; a lightweight tag has only one line, already a commit.
    Blank lines are ignored.

    Args:
        output: Lines of ``<sha>\\t<ref>``, as printed by ``git ls-remote``.

    Returns:
        Refs without the ``^{}`` suffix, e.g. ``{"refs/tags/harborrag-v2.0.0": "60609c8..."}``.
    """
    refs: dict[str, str] = {}
    peeled: dict[str, str] = {}

    for line in output.splitlines():
        if not line.strip():
            continue

        sha, _, ref = line.partition("\t")
        if ref.endswith(PEELED_SUFFIX):
            peeled[ref.removesuffix(PEELED_SUFFIX)] = sha
        else:
            refs[ref] = sha

    return {**refs, **peeled}


def product_tags(refs: Mapping[str, str]) -> list[RemoteTag]:
    """Keep only the product release tags from a ``{ref: sha}`` mapping.

    Branches and any tag rejected by ``parse_product_tag`` are dropped.

    Returns:
        Product tags sorted by version, oldest first.
    """
    tags = []

    for ref, sha in refs.items():
        if not ref.startswith(TAGS_PREFIX):
            continue

        name = ref.removeprefix(TAGS_PREFIX)
        version = parse_product_tag(name)
        if version is not None:
            tags.append(RemoteTag(name=name, sha=sha, version=version))

    return sorted(tags, key=lambda t: t.version)


def ls_remote(repo_url: str, *args: str) -> str:
    """Run ``git ls-remote`` (no clone, no history) and return its stdout.

    Args:
        repo_url: Git URL of the repository.
        *args: Extra ``git ls-remote`` options, e.g. ``"--tags"`` or ``"--heads"``.

    Raises:
        subprocess.CalledProcessError: git exited non-zero (bad URL, no access).
        subprocess.TimeoutExpired: the remote did not answer within 120 seconds.
    """
    result = subprocess.run(
        ["git", "ls-remote", *args, repo_url],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout


def discover_remote_tags(repo_url: str = DEFAULT_REPO_URL) -> list[RemoteTag]:
    """List the HarborRAG product release tags on the remote, oldest first.

    One ``git ls-remote --tags`` call; annotated tags resolve to their commit sha.

    Raises:
        subprocess.CalledProcessError: see ``ls_remote``.
    """
    return product_tags(parse_ls_remote(ls_remote(repo_url, "--tags")))


def remote_branch_sha(repo_url: str = DEFAULT_REPO_URL, branch: str = MAIN_BRANCH) -> str:
    """Return the commit sha at the tip of ``branch`` on the remote.

    Raises:
        SystemExit: the branch does not exist on the remote.
        subprocess.CalledProcessError: see ``ls_remote``.
    """
    ref = f"{HEADS_PREFIX}{branch}"
    sha = parse_ls_remote(ls_remote(repo_url, "--heads")).get(ref)
    if not sha:
        raise SystemExit(f"branch not found on remote: {ref}")
    return sha


# --------------------------------------------------------------------------- expected vs state


def main_target(main_sha: str) -> SyncTarget:
    """Build the target that syncs Next (``sync-state.current``) from ``main``.

    ``product_version`` is ``"auto"`` so ingest reads it from the root
    ``pyproject.toml`` of that commit.
    """
    return SyncTarget(
        key=CURRENT_KEY,
        ref=f"{HEADS_PREFIX}{MAIN_BRANCH}",
        sha=main_sha,
        channel=Channel.MAIN,
        product_version="auto",
        label="Next",
    )


def stable_target(tag: RemoteTag) -> SyncTarget:
    """Build the target that syncs the ``"X.Y"`` snapshot from a stable tag.

    The key is the tag's minor line; the label is the full version, so a patch
    release (``2.0.1``) relabels the existing ``2.0`` snapshot.
    """
    return SyncTarget(
        key=minor(str(tag.version)),
        ref=f"{TAGS_PREFIX}{tag.name}",
        sha=tag.sha,
        channel=Channel.STABLE,
        product_version=str(tag.version),
        label=str(tag.version),
    )


def expected_targets(
    main_sha: str, tags: Iterable[RemoteTag], keep_minors: int
) -> list[SyncTarget]:
    """Return what the site should hold: Next at main, then the kept minor lines.

    Minor lines come oldest first. The writer prepends each new line to
    ``versions.json`` and prunes the oldest beyond ``keep_minors``, so running the
    targets in this order leaves ``versions.json`` newest-first and never prunes a
    line that is still wanted.

    Args:
        main_sha: Commit at the tip of HarborRAG ``main``.
        tags: Product release tags; pre-releases are ignored.
        keep_minors: Number of stable minor lines the site keeps.

    Returns:
        ``[current, "X.Y" (oldest kept), ..., "X.Y" (newest)]``.
    """
    latest = latest_stable_per_minor(tags)
    kept = newest_minor_lines(latest, keep_minors)
    targets = []
    targets.append(main_target(main_sha))

    for line in reversed(kept):
        targets.append(stable_target(latest[line]))

    return targets


def state_entry(state: SyncState, key: str) -> SyncEntry | None:
    """Return the ``sync-state.json`` entry for a target key.

    ``"current"`` maps to ``state.current``; ``"X.Y"`` maps to
    ``state.versions["X.Y"]``, or ``None`` when that line was never synced.
    """
    return state.current if key == CURRENT_KEY else state.versions.get(key)


def is_stale(target: SyncTarget, entry: SyncEntry | None) -> bool:
    """Tell whether ``target`` needs an ingest run.

    A slot is stale when it was never synced (no entry, or no ``source_sha``) or
    holds another commit, e.g. ``main`` moved on or a tag was re-pointed.
    """
    return entry is None or entry.source_sha != target.sha


def compute_stale_entries(state: SyncState, expected: Iterable[SyncTarget]) -> list[SyncTarget]:
    """Return the expected targets whose ``sync-state.json`` entry is stale.

    Entries in ``state`` that are not expected (older lines, beyond
    ``keep_minors``) are left alone; pruning is the writer's job.

    Returns:
        Stale targets, in the order of ``expected``.
    """
    result = []

    for target in expected:
        entry = state_entry(state, target.key)
        if is_stale(target, entry):
            result.append(target)

    return result


def discover_stale(site: Path, repo_url: str, keep_minors: int) -> list[SyncTarget]:
    """Compare the remote with ``site/sync-state.json`` and return what to re-sync.

    Makes two ``git ls-remote`` calls (heads, tags); nothing is cloned or written.

    Args:
        site: The website directory that holds ``sync-state.json``.
        repo_url: Git URL of HarborRAG.
        keep_minors: Number of stable minor lines the site keeps.

    Returns:
        Stale targets, Next first then minor lines oldest first; empty when the
        site is up to date.
    """
    state = read_sync_state(site)
    expected = expected_targets(
        remote_branch_sha(repo_url), discover_remote_tags(repo_url), keep_minors
    )
    return compute_stale_entries(state, expected)


# --------------------------------------------------------------------------- CLI


def to_json(targets: Iterable[SyncTarget]) -> str:
    """Serialize targets as a one-line JSON array.

    One line so the workflow can write it to ``$GITHUB_OUTPUT`` as ``targets=...``;
    the Reconcile step reads each element with ``jq``.
    """
    return json.dumps([asdict(t) for t in targets], separators=(",", ":"))


def build_parser() -> argparse.ArgumentParser:
    """Build the parser for ``ingest.discover``."""
    parser = argparse.ArgumentParser(
        prog="python -m ingest.discover",
        description="Print, as JSON, the docs versions whose sync-state is out of date.",
    )
    parser.add_argument("--site", required=True, help="Path to the website directory.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="HarborRAG git URL.")
    parser.add_argument(
        "--keep-minors",
        type=int,
        default=2,
        help="Number of minor versions to retain.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run stale-version discovery from the command line.

    Stale targets go to stdout as JSON (``[]`` when up to date); the human summary,
    one ``stale: ...`` line per target or ``no changes``, goes to stderr.

    Args:
        argv: Arguments without the program name; ``None`` reads ``sys.argv``.

    Returns:
        Exit code ``0``. Failures (git, missing branch) raise instead.
    """
    args = build_parser().parse_args(argv)
    stale = discover_stale(Path(args.site), args.repo_url, args.keep_minors)

    if stale:
        for t in stale:
            print(f"stale: {t.key} -> {t.ref} @ {t.sha[:7]} ({t.channel})", file=sys.stderr)
    else:
        print("no changes", file=sys.stderr)

    print(to_json(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
