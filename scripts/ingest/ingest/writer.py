from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from ingest.models import Channel, IngestRequest, SyncEntry, SyncState

DOCS_DIR = Path("docs")
SIDEBARS_FILE = Path("sidebars.ts")
SYNC_STATE_FILE = Path("sync-state.json")
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
    """

    pages: dict[PurePosixPath, str]
    sidebars_ts: str


# --------------------------------------------------------------------------- paths


def target_dir(site: Path, channel: Channel) -> Path:
    """Return the docs directory the channel writes to.

    main / prerelease -> ``site / docs`` (the "Next" docs).

    Raises:
        ValueError: ``channel`` is ``STABLE`` (versioned snapshots are 2.10, not here).
    """
    if channel == Channel.MAIN or channel == Channel.PRERELEASE:
        return site / DOCS_DIR
    raise ValueError(f"channel is {channel.upper()}")


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

    versions = {}
    for ver, value in sync_state.get("versions", {}).items():
        versions[ver] = SyncEntry(
            **{
                **value,
                "channel": Channel(value["channel"]),
            }
        )

    return SyncState(current, versions)


def render_sync_state(state: SyncState) -> str:
    """Serialize ``state`` deterministically (same input -> same bytes).

    ``json.dumps(..., indent=2, ensure_ascii=False) + "\\n"``; versions sorted by key.
    """
    current = asdict(state.current)
    current["channel"] = state.current.channel.value

    versions = {}

    for version in sorted(state.versions):
        entry = asdict(state.versions[version])
        entry["channel"] = state.versions[version].channel.value
        versions[version] = entry

    data = {
        "current": current,
        "versions": versions,
    }

    return (
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def updated_sync_state(state: SyncState, request: IngestRequest, *, synced_at: str) -> SyncState:
    """Return ``state`` with ``current`` replaced for this run.

    ``versions`` is copied unchanged: main/prerelease never touch released versions
    (and never touch versions.json either).
    """
    current = SyncEntry(
        label="Next",
        channel=request.channel,
        source_ref=request.source_ref,
        source_sha=request.source_sha,
        synced_at=synced_at,
    )

    return SyncState(current, state.versions)


def already_synced(state: SyncState, request: IngestRequest) -> bool:
    """True when ``current.source_sha`` equals ``request.source_sha`` and not ``--force``.

    A ``None`` sha (local run without ``--source-sha``) never counts as synced.
    """
    return (
        not request.force
        and request.source_sha is not None
        and state.current.source_sha == request.source_sha
    )


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


def format_plan(plan: WritePlan, *, site: Path, channel: Channel) -> str:
    """Return the ``--dry-run`` file plan, one line per file, sorted.

    Example::

        website/docs/getting-started/README.md
        website/docs/users/chat/README.md
        website/sidebars.ts
        website/sync-state.json
    """
    root = target_dir(site, channel)

    files = [str(root / path) for path in plan.pages]

    files.append(str(site / "sidebars.ts"))
    files.append(str(site / "sync-state.json"))

    return "\n".join(sorted(files))


# --------------------------------------------------------------------------- entry point


def write(
    plan: WritePlan,
    request: IngestRequest,
    *,
    synced_at: str,
) -> WriteOutcome:
    """Write ``plan`` into ``request.site`` for a main/prerelease run.

    Order matters:

    1. ``--dry-run``          -> print ``format_plan``, return ``DRY_RUN``.
    2. ``already_synced``     -> return ``ALREADY_SYNCED`` (``--force`` skips this).
    3. Stage: ``tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=target.parent)``, ``write_tree``.
       Anything raised from here to step 5 must leave the site untouched and remove the
       staging dir (``try/finally``).
    4. Compare: staged tree == target tree AND rendered sidebars == current sidebars.ts
       AND ``current.source_sha == request.source_sha`` -> print "no changes",
       return ``NO_CHANGES`` without writing anything (not even sync-state: a new
       ``synced_at`` alone would make a diff and open a PR).
    5. ``swap_dir``, ``write_file_atomic`` sidebars.ts, then sync-state.json last
       (sync-state is the "done" marker).
    6. Return ``WRITTEN``. ``versions.json`` is never opened.
    """
    if request.dry_run:
        print(format_plan(plan, site=request.site, channel=request.channel))
        return WriteOutcome.DRY_RUN

    state = read_sync_state(request.site)

    if already_synced(state, request):
        print(f"no changes: already synced {request.source_sha} (use --force to rewrite)")
        return WriteOutcome.ALREADY_SYNCED

    target = target_dir(request.site, request.channel)
    staged = Path(
        tempfile.mkdtemp(
            prefix=STAGING_PREFIX,
            dir=target.parent,
        )
    )

    try:
        write_tree(staged, plan.pages)

        same_tree = tree_files(staged) == tree_files(target)

        sidebars_path = request.site / "sidebars.ts"
        current_sidebars = (
            sidebars_path.read_text(encoding="utf-8") if sidebars_path.exists() else ""
        )

        same_sidebars = current_sidebars == plan.sidebars_ts
        same_sha = state.current.source_sha == request.source_sha

        if same_tree and same_sidebars and same_sha:
            print("no changes")
            return WriteOutcome.NO_CHANGES

        swap_dir(staged, target)

        write_file_atomic(
            request.site / "sidebars.ts",
            plan.sidebars_ts,
        )

        new_state = updated_sync_state(
            state,
            request,
            synced_at=synced_at,
        )

        write_file_atomic(
            request.site / "sync-state.json",
            render_sync_state(new_state),
        )

        return WriteOutcome.WRITTEN

    finally:
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)
