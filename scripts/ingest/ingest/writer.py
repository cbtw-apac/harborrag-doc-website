from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from ingest import versions
from ingest.models import Channel, IngestRequest, SyncEntry, SyncState

DOCS_DIR = Path("docs")
VERSIONED_DOCS_DIR = Path("versioned_docs")
VERSIONED_SIDEBARS_DIR = Path("versioned_sidebars")
SIDEBARS_FILE = Path("sidebars.ts")
SYNC_STATE_FILE = Path("sync-state.json")
VERSIONS_FILE = Path("versions.json")
STAGING_PREFIX = ".ingest-"


class WriteOutcome(StrEnum):
    WRITTEN = "written"
    NO_CHANGES = "no-changes"
    ALREADY_SYNCED = "already-synced"
    DRY_RUN = "dry-run"


@dataclass(frozen=True)
class WritePlan:
    """Everything the writer puts on disk, already rendered.

    The writer does no Markdown work: runner builds this from the collected,
    guarded, linked and frontmattered docs, so a failing guard never reaches it.

    Both sidebar renderings are always present because the same TOC produces both;
    which one is written depends on the channel. A ``main``/``prerelease`` run
    writes ``sidebars.ts``; a ``stable`` run writes the versioned JSON and must
    leave ``sidebars.ts`` alone, since that file belongs to Next.
    """

    pages: dict[PurePosixPath, str]
    sidebars_ts: str
    sidebars_json: str = ""


# --------------------------------------------------------------------------- paths


def target_dir(site: Path, channel: Channel, minor: str | None = None) -> Path:
    """Return the docs directory the channel writes to.

    main / prerelease -> ``site / docs`` (the "Next" docs).
    stable           -> ``site / versioned_docs / version-<minor>``.

    Raises:
        ValueError: ``channel`` is ``STABLE`` and ``minor`` is missing or is not
            a ``MAJOR.MINOR`` label.
    """
    if channel == Channel.MAIN or channel == Channel.PRERELEASE:
        return site / DOCS_DIR

    if minor is None:
        raise ValueError("channel is STABLE: a MAJOR.MINOR version is required")

    if not versions.MINOR_RE.fullmatch(minor):
        raise ValueError(f"expected a MAJOR.MINOR version label like '2.0', got {minor!r}")

    return site / VERSIONED_DOCS_DIR / f"version-{minor}"


def versioned_sidebars_path(site: Path, minor: str) -> Path:
    """Return the ``versioned_sidebars/version-<minor>-sidebars.json`` path."""
    return site / VERSIONED_SIDEBARS_DIR / f"version-{minor}-sidebars.json"


def request_minor(request: IngestRequest) -> str | None:
    """Return the minor line a stable request targets, or ``None`` for Next."""
    if request.channel != Channel.STABLE:
        return None

    return versions.minor(request.product_version)


# --------------------------------------------------------------------------- sync-state


def read_sync_state(site: Path) -> SyncState:
    """Load ``site / sync-state.json`` into a ``SyncState``.

    The file looks like::

        {"current": {"label": "Next", "channel": "main", "source_ref": null, ...},
         "versions": {"2.0": {...}}}
    """
    with open(site / SYNC_STATE_FILE, encoding="utf-8") as f:
        sync_state = json.load(f)

    crt = sync_state["current"]
    current = SyncEntry(
        **{
            **crt,
            "channel": Channel(crt["channel"]),
        }
    )

    released = {}
    for ver, value in sync_state.get("versions", {}).items():
        released[ver] = SyncEntry(
            **{
                **value,
                "channel": Channel(value["channel"]),
            }
        )

    return SyncState(current, released)


def render_sync_state(state: SyncState) -> str:
    """Serialize ``state`` deterministically (same input -> same bytes).

    ``json.dumps(..., indent=2, ensure_ascii=False) + "\\n"``; versions sorted by key.
    """
    current = asdict(state.current)
    current["channel"] = state.current.channel.value

    released = {}

    for version in sorted(state.versions):
        entry = asdict(state.versions[version])
        entry["channel"] = state.versions[version].channel.value
        released[version] = entry

    data = {
        "current": current,
        "versions": released,
    }

    return (
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def updated_sync_state(
    state: SyncState,
    request: IngestRequest,
    *,
    synced_at: str,
    dropped: Iterable[str] = (),
    kept: Iterable[str] | None = None,
) -> SyncState:
    """Return ``state`` with this run's entry replaced.

    main/prerelease replace ``current`` and copy ``versions`` unchanged: they never
    touch released versions (nor versions.json).

    stable replaces ``versions[minor]`` and leaves ``current`` alone — the Next docs
    are not affected by publishing a snapshot. The entry's label is the full product
    version (``"2.0.1"``) while its key is the minor line (``"2.0"``), so the version
    dropdown can show the exact patch readers are looking at. Any minor line in
    ``dropped`` is removed, so a pruned snapshot leaves no orphan state entry.
    When ``kept`` is given, every minor line not in it is removed too: that also
    clears an entry left behind by a run that crashed after rewriting
    ``versions.json`` but before rewriting ``sync-state.json``.
    """
    if request.channel != Channel.STABLE:
        current = SyncEntry(
            label="Next",
            channel=request.channel,
            source_ref=request.source_ref,
            source_sha=request.source_sha,
            synced_at=synced_at,
        )

        return SyncState(current, state.versions)

    drop = set(dropped)
    keep = None if kept is None else set(kept)
    released = {
        m: e
        for m, e in state.versions.items()
        if m not in drop and (keep is None or m in keep)
    }
    released[versions.minor(request.product_version)] = SyncEntry(
        label=request.product_version,
        channel=request.channel,
        source_ref=request.source_ref,
        source_sha=request.source_sha,
        synced_at=synced_at,
    )

    return SyncState(state.current, released)


def already_synced(state: SyncState, request: IngestRequest) -> bool:
    """True when this run's recorded ``source_sha`` equals ``request.source_sha``.

    ``--force`` always returns False. A stable run compares against its own minor
    line's entry, not ``current``: comparing against ``current`` would report
    "already synced" for the first snapshot of a tag whose commit Next happens to
    sit on, and no snapshot would ever be written.
    """
    if request.force:
        return False

    if request.channel == Channel.STABLE:
        entry = state.versions.get(versions.minor(request.product_version))

        return (
            entry is not None
            and entry.source_sha == request.source_sha
            and entry.label == request.product_version
        )

    return state.current.source_sha == request.source_sha


# --------------------------------------------------------------------------- tree


def write_tree(root: Path, pages: dict[PurePosixPath, str]) -> None:
    """Write every page under ``root`` (which must exist and be empty)."""
    for path, content in pages.items():
        target = root / path

        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )


def tree_files(root: Path) -> dict[PurePosixPath, bytes]:
    """Return ``{relative POSIX path: bytes}`` for every file under ``root``.

    A missing ``root`` is an empty tree (first run on a fresh site).
    """
    if not root.exists():
        return {}

    tree = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        key = PurePosixPath(p.relative_to(root).as_posix())
        tree[key] = p.read_bytes()

    return tree


def trees_equal(a: Path, b: Path) -> bool:
    """True when both trees have the same file set with byte-identical content.

    Extra files on either side count as a difference (a page removed upstream
    must disappear from the site).
    """
    return tree_files(a) == tree_files(b)


def swap_dir(staged: Path, target: Path) -> None:
    """Replace ``target`` with ``staged`` so the target is never half-written.

    1. ``target`` -> ``target.with_name(STAGING_PREFIX + "old")`` (if it exists)
    2. ``staged`` -> ``target``
    3. delete the old copy

    If step 2 fails, move the old copy back before re-raising.
    ``staged`` must be on the same filesystem as ``target`` (see ``write``).
    """
    old = target.with_name(STAGING_PREFIX + "old")

    if old.exists():
        shutil.rmtree(old)

    if target.exists():
        os.replace(target, old)

    try:
        os.replace(staged, target)
    except Exception:
        if old.exists():
            os.replace(old, target)
        raise

    if old.exists():
        shutil.rmtree(old)


def prune_snapshots(site: Path, dropped: Iterable[str]) -> None:
    """Delete the snapshot of every minor line in ``dropped``.

    A snapshot lives in four places and all four must go, or Docusaurus either
    fails to build (a sidebar referencing a missing version) or leaves orphan
    files in the tree. This removes the two on disk; ``versions.json`` and
    ``sync-state.json`` are rewritten by the caller from the pruned lists.
    """
    for minor in dropped:
        shutil.rmtree(site / VERSIONED_DOCS_DIR / f"version-{minor}", ignore_errors=True)
        versioned_sidebars_path(site, minor).unlink(missing_ok=True)


def write_file_atomic(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` through a temp file + ``os.replace``."""
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=STAGING_PREFIX,
        delete=False,
    ) as f:
        f.write(content)

    try:
        os.replace(f.name, path)
    except Exception:
        Path(f.name).unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------- dry run


def format_plan(
    plan: WritePlan,
    *,
    site: Path,
    channel: Channel,
    minor: str | None = None,
    dropped: Iterable[str] = (),
) -> str:
    """Return the ``--dry-run`` file plan, one line per file, sorted.

    Example (main)::

        website/docs/getting-started/README.md
        website/docs/users/chat/README.md
        website/sidebars.ts
        website/sync-state.json

    A stable run lists the versioned paths plus ``versions.json`` instead of
    ``sidebars.ts``, so the dry run shows exactly the set the real run touches.
    """
    root = target_dir(site, channel, minor)

    files = [str(root / path) for path in plan.pages]

    if channel == Channel.STABLE:
        assert minor is not None  # target_dir already rejected a missing minor
        files.append(str(versioned_sidebars_path(site, minor)))
        files.append(str(site / VERSIONS_FILE))
    else:
        files.append(str(site / SIDEBARS_FILE))

    files.append(str(site / SYNC_STATE_FILE))

    for old in dropped:
        files.append(f"delete {site / VERSIONED_DOCS_DIR / f'version-{old}'}/")
        files.append(f"delete {versioned_sidebars_path(site, old)}")

    return "\n".join(sorted(files))


# --------------------------------------------------------------------------- entry point


def write(
    plan: WritePlan,
    request: IngestRequest,
    *,
    synced_at: str,
) -> WriteOutcome:
    """Write ``plan`` into ``request.site``.

    Order matters:

    1. ``--dry-run``          -> print ``format_plan``, return ``DRY_RUN``.
    2. ``already_synced``     -> return ``ALREADY_SYNCED`` (``--force`` skips this).
    3. Stage: ``tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=target.parent)``, ``write_tree``.
       Anything raised from here to step 5 must leave the site untouched and remove the
       staging dir (``try/finally``).
    4. Compare: staged tree == target tree AND the rendered sidebar == the one on disk
       -> print "no changes", return ``NO_CHANGES`` without writing anything (not even
       sync-state: a new ``synced_at`` alone would make a diff and open a PR).
    5. ``swap_dir``, write the sidebar, prune dropped snapshots, write ``versions.json``
       (stable only), then sync-state.json **last** — sync-state is the "done" marker,
       so a crash mid-sequence leaves a state that reports the previous sha and the
       next run redoes the work.
    6. Return ``WRITTEN``.

    A main/prerelease run writes ``docs/`` + ``sidebars.ts`` and never opens
    ``versions.json``. A stable run writes ``versioned_docs/version-<X.Y>/`` +
    ``versioned_sidebars/version-<X.Y>-sidebars.json`` + ``versions.json`` and never
    touches ``docs/`` or ``sidebars.ts``.
    """
    site = request.site
    stable = request.channel == Channel.STABLE
    minor = request_minor(request)

    if stable and not plan.sidebars_json.strip():
        raise ValueError("stable run needs plan.sidebars_json (runner left it empty)")

    if request.dry_run:
        dry_dropped: list[str] = []
        if stable:
            assert minor is not None
            _, dry_dropped = versions.plan_versions(
                versions.read_versions(site), minor, request.keep_minors
            )
        print(
            format_plan(
                plan,
                site=site,
                channel=request.channel,
                minor=minor,
                dropped=dry_dropped,
            )
        )
        return WriteOutcome.DRY_RUN

    state = read_sync_state(site)

    if already_synced(state, request):
        print(f"no changes: already synced {request.source_sha} (use --force to rewrite)")
        return WriteOutcome.ALREADY_SYNCED

    if stable:
        assert minor is not None  # guaranteed by request_minor for STABLE
        kept, dropped = versions.plan_versions(
            versions.read_versions(site), minor, request.keep_minors
        )
        sidebar_path = versioned_sidebars_path(site, minor)
        sidebar_content = plan.sidebars_json
    else:
        kept, dropped = [], []
        sidebar_path = site / SIDEBARS_FILE
        sidebar_content = plan.sidebars_ts

    target = target_dir(site, request.channel, minor)
    target.parent.mkdir(parents=True, exist_ok=True)

    staged = Path(
        tempfile.mkdtemp(
            prefix=STAGING_PREFIX,
            dir=target.parent,
        )
    )

    try:
        write_tree(staged, plan.pages)

        same_tree = tree_files(staged) == tree_files(target)

        current_sidebar = (
            sidebar_path.read_text(encoding="utf-8") if sidebar_path.exists() else ""
        )
        same_sidebar = current_sidebar == sidebar_content

        same_versions = not stable or versions.read_versions(site) == kept

        # A stable patch whose docs did not change (2.1.0 -> 2.1.1) still has to
        # relabel its entry, or the dropdown keeps showing the old patch. Next
        # stays exempt: only synced_at would change there, and that must not
        # open a PR.
        if stable:
            entry = state.versions.get(minor)
            same_entry = (
                entry is not None
                and entry.label == request.product_version
                and entry.source_sha == request.source_sha
                and set(state.versions) <= set(kept)
            )
        else:
            same_entry = True

        if same_tree and same_sidebar and same_versions and same_entry and not dropped:
            print("no changes")
            return WriteOutcome.NO_CHANGES

        swap_dir(staged, target)

        sidebar_path.parent.mkdir(parents=True, exist_ok=True)
        write_file_atomic(sidebar_path, sidebar_content)

        if stable:
            prune_snapshots(site, dropped)
            write_file_atomic(site / VERSIONS_FILE, versions.render_versions(kept))

        new_state = updated_sync_state(
            state,
            request,
            synced_at=synced_at,
            dropped=dropped,
            kept=kept if stable else None,
        )

        write_file_atomic(
            site / SYNC_STATE_FILE,
            render_sync_state(new_state),
        )

        return WriteOutcome.WRITTEN

    finally:
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)