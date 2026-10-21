from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from ingest import guard, writer
from ingest.bridge import bridge_docs, bridge_ids, bridge_mapping
from ingest.collect import collect
from ingest.frontmatter import apply_frontmatter, render, sidebar_positions
from ingest.links import apply_links
from ingest.models import Doc, IngestRequest
from ingest.toc import load_toc, render_sidebars_ts, toc_link_mapping

DENY_FILE = Path(__file__).resolve().parent.parent / "deny.txt"
DOCS_DIR = Path("docs")


def is_docs_page(source_path: Path) -> bool:
    """True for ``docs/**/*.md`` (collect() already left out docs/TOC.md)."""
    return source_path.parts[0] == DOCS_DIR.name and source_path.suffix == ".md"


def docs_page(source: Path, source_path: Path) -> Doc:
    """Return the ``Doc`` for one docs/ page; its target drops the leading ``docs/``."""
    body = (source / source_path).read_text(encoding="utf-8")

    return Doc(source_path, source_path.relative_to(DOCS_DIR), title="", body=body, frontmatter={})


def docs_pages(source: Path, files: list[Path]) -> list[Doc]:
    """Return a ``Doc`` for every docs/ page in ``files``; order follows ``files``."""
    return [docs_page(source, p) for p in files if is_docs_page(p)]


def link_mapping(files: list[Path], toc_mapping: dict[Path, str]) -> dict[Path, str]:
    """Return the ``links.apply_links`` mapping: docs/ pages, bridged files, docs/TOC.md."""
    mapping: dict[Path, str] = {
        p: p.relative_to(DOCS_DIR).as_posix() for p in files if is_docs_page(p)
    }
    mapping.update(bridge_mapping(files))
    mapping.update(toc_mapping)

    return mapping


def build_plan(request: IngestRequest) -> writer.WritePlan:
    """Collect, guard, link and render the source checkout into a ``WritePlan``.

    Every step that can fail runs here, before anything touches the site.
    """
    source = request.source
    files = collect(source)

    guard.publication(source, files, guard.load_deny_patterns(DENY_FILE))

    docs = docs_pages(source, files) + bridge_docs(source, files)
    guard.branding(docs)

    pages = {PurePosixPath(p.as_posix()) for p in files}
    toc = load_toc(source, pages=pages, bridge=bridge_ids(files))

    apply_links(docs, mapping=link_mapping(files, toc_link_mapping(toc)), source_root=source)

    positions = sidebar_positions(toc)
    for doc in docs:
        apply_frontmatter(doc, positions=positions, source_sha=request.source_sha)

    return writer.WritePlan(
        pages={PurePosixPath(d.target_path.as_posix()): render(d) for d in docs},
        sidebars_ts=render_sidebars_ts(toc),
    )


def run(request: IngestRequest) -> writer.WriteOutcome:
    """
    Execute the documentation ingestion workflow.
    """

    print("=== INGEST CONFIGURATION ===")
    print(f"source={request.source}")
    print(f"site={request.site}")
    print(f"channel={request.channel}")
    print(f"product_version={request.product_version}")
    print(f"source_ref={request.source_ref}")
    print(f"source_sha={request.source_sha}")
    print(f"keep_minors={request.keep_minors}")
    print(f"dry_run={request.dry_run}")
    print(f"force={request.force}")

    plan = build_plan(request)
    synced_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # NO_CHANGES / ALREADY_SYNCED print a "no changes" line and still exit 0;
    # the workflow reads that line to skip the PR.
    return writer.write(plan, request, synced_at=synced_at)
