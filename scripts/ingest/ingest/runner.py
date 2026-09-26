from __future__ import annotations

from ingest.models import IngestRequest


def run(request: IngestRequest) -> None:
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
