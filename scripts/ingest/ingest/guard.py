from __future__ import annotations

import re
from pathlib import Path

from ingest.models import Doc

FORBIDDEN = re.compile(
    r"QDrant Loader|Qdrant Loader|qdrant-loader|martin-papy|github\.com/harborrag/harborrag",
    re.IGNORECASE,
)


def publication(source: Path, files: list[Path], deny: list[re.Pattern]) -> None:
    """Reject private reference material in the published set.

    ``files`` are the repository-relative paths returned by ``collect(source)``;
    each is read from ``source / path``. A file fails when a deny pattern
    matches its relative path or any line of its content. Every match is
    collected before raising, so one run reports all of them.

    Raises:
        ValueError: listing each failure as ``path: denied file name (match)``
            or ``path:line: match``.
    """
    failures: list[str] = []

    for path in files:
        lines = (source / path).read_text(encoding="utf-8").splitlines()
        path = path.as_posix()

        for pattern in deny:
            # Check the relative path
            if match := pattern.search(path):
                failures.append(f"{path}: denied file name ({match.group(0)})")

            # Check content line by line
            for line_number, line in enumerate(lines, start=1):
                if match := pattern.search(line):
                    failures.append(f"{path}:{line_number}: {match.group(0)}")

    if failures:
        raise ValueError(
            "Publication denied. Forbidden content found in:\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )


def branding(docs: list[Doc]) -> None:
    """Reject stale predecessor branding in published documentation.

    Port of HarborRAG's ``website/check_branding.py``: each line of ``doc.body``
    is matched against ``FORBIDDEN``. A line is exempt when it, or the line
    before it, contains ``branding-compat``. Line numbers are relative to the
    body, not to the source file.

    Raises:
        ValueError: listing each failure as ``source_path:line: match``.
    """

    failures: list[str] = []

    for doc in docs:
        lines = doc.body.splitlines()

        for line_number, line in enumerate(lines, start=1):
            previous_line = lines[line_number - 2] if line_number > 1 else ""

            if "branding-compat" in line or "branding-compat" in previous_line:
                continue

            if match := FORBIDDEN.search(line):
                failures.append(f"{doc.source_path.as_posix()}:{line_number}: {match.group(0)}")

    if failures:
        raise ValueError(
            "Stale branding detected:\n" + "\n".join(f"- {failure}" for failure in failures)
        )


def load_deny_patterns(path: Path) -> list[re.Pattern]:
    """Load the publication deny-list from ``path`` (e.g. ``deny.txt``).

    Each non-blank line not starting with ``#`` is a regex, compiled with
    ``re.IGNORECASE``. Lines are stripped, so leading/trailing spaces are not
    part of a pattern.

    Raises:
        re.error: if a line is not a valid regex.
    """
    patterns: list[re.Pattern] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        patterns.append(re.compile(line, re.IGNORECASE))

    return patterns
