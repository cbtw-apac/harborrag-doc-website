from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

from packaging.version import Version

import ingest
from ingest.models import Channel, IngestRequest


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
        type=Channel,
        choices=list(Channel),
        help="Target publication channel.",
    )

    parser.add_argument(
        "--product-version",
        required=True,
        help="Product version (for example: 2.0.1).",
    )

    parser.add_argument(
        "--source-ref",
        default=None,
        help="Git reference used for ingestion.",
    )

    parser.add_argument(
        "--source-sha",
        default=None,
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


def resolve_product_version(source: Path, raw: str) -> str:
    """
    Resolve --product-version. "auto" means: read it from the source
    checkout instead of trusting the caller.
    """
    if raw != "auto":
        return raw

    pyproject = source / "pyproject.toml"

    try:
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        return data["project"]["version"]
    except (FileNotFoundError, KeyError):
        raise SystemExit(f"Could not determine product version from source: {source}")


def main() -> None:
    """
    Parse CLI arguments and execute the ingest workflow.
    """
    parser = build_parser()
    args = parser.parse_args()

    source = Path(args.source)
    product_version = resolve_product_version(source, args.product_version)

    if args.channel in {Channel.STABLE, Channel.PRERELEASE}:
        is_prerelease = Version(product_version).is_prerelease

        expected_channel = (
            Channel.PRERELEASE
            if is_prerelease
            else Channel.STABLE
        )

        if args.channel != expected_channel:
            raise SystemExit(
                f"Version/channel mismatch: "
                f"version={product_version!r} "
                f"requires channel={expected_channel.value!r}, "
                f"got channel={args.channel.value!r}"
            )

    request = IngestRequest(
        source=source,
        site=Path(args.site),
        channel=args.channel,
        product_version=product_version,
        source_ref=args.source_ref,
        source_sha=args.source_sha,
        keep_minors=args.keep_minors,
        dry_run=args.dry_run,
        force=args.force,
    )

    ingest.run(request)


if __name__ == "__main__":
    main()