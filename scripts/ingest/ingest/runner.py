def run(
    *,
    source: str,
    site: str,
    channel: str,
    product_version: str,
    source_ref: str,
    source_sha: str,
    keep_minors: int,
    dry_run: bool,
    force: bool,
) -> None:
    """
    Execute the documentation ingestion workflow.

    Args:
        source: Path to the source checkout.
        site: Path to the website repository.
        channel: Publication channel.
        product_version: Product version.
        source_ref: Source git reference.
        source_sha: Source git commit SHA.
        keep_minors: Number of minor versions to keep.
        dry_run: Whether writes should be skipped.
        force: Whether safeguards should be bypassed.
    """
    print("=== INGEST CONFIGURATION ===")
    print(f"source={source}")
    print(f"site={site}")
    print(f"channel={channel}")
    print(f"product_version={product_version}")
    print(f"source_ref={source_ref}")
    print(f"source_sha={source_sha}")
    print(f"keep_minors={keep_minors}")
    print(f"dry_run={dry_run}")
    print(f"force={force}")