from __future__ import annotations

import argparse

import ingest


def build_parser() -> argparse.ArgumentParser:
    """
    Build and configure the CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Ingest published documentation into a website repository.",
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Path to the source checkout.",
    )

    parser.add_argument(
        "--site",
        required=True,
        help="Path to the website repository.",
    )

    parser.add_argument(
        "--channel",
        required=True,
        choices=["main", "prerelease", "stable"],
        help="Target publication channel.",
    )

    parser.add_argument(
        "--product-version",
        required=True,
        help="Product version (for example: 2.0.1).",
    )

    parser.add_argument(
        "--source-ref",
        required=True,
        help="Git reference used for ingestion.",
    )

    parser.add_argument(
        "--source-sha",
        required=True,
        help="Git commit SHA.",
    )

    parser.add_argument(
        "--keep-minors",
        type=int,
        default=2,
        help="Number of minor versions to retain.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even when safeguards fail.",
    )

    return parser


def main() -> None:
    """
    Parse CLI arguments and execute the ingest workflow.
    """
    parser = build_parser()
    args = parser.parse_args()

    ingest.run(
        source=args.source,
        site=args.site,
        channel=args.channel,
        product_version=args.product_version,
        source_ref=args.source_ref,
        source_sha=args.source_sha,
        keep_minors=args.keep_minors,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    main()