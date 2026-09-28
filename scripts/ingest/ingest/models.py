from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Channel(StrEnum):
    MAIN = "main"
    PRERELEASE = "prerelease"
    STABLE = "stable"


@dataclass(frozen=True)
class SyncEntry:
    label: str
    channel: Channel
    source_ref: str | None
    source_sha: str | None
    synced_at: str | None  # ISO-8601 UTC


@dataclass(frozen=True)
class SyncState:
    current: SyncEntry
    versions: dict[str, SyncEntry]  # "2.0" -> entry


@dataclass(frozen=True)
class IngestRequest:
    source: Path
    site: Path
    channel: Channel
    product_version: str  # "2.0.1" | "2.1.0a1" | "auto" (read root pyproject)
    source_ref: str
    source_sha: str
    keep_minors: int = 2
    dry_run: bool = False
    force: bool = False


@dataclass
class Doc:
    source_path: Path  # relative to HarborRAG root, e.g. docs/users/chat/README.md
    target_path: Path  # relative to docs target dir, e.g. users/chat/README.md
    title: str
    body: str
    frontmatter: dict[str, object]
