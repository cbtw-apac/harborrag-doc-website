"""Minor-line policy for stable snapshots: ``versions.json`` and the retention rule.

Docusaurus versions documentation by *minor line*, not by patch: ``2.0.0`` and
``2.0.1`` are both the ``2.0`` snapshot, and only ``2.0`` appears in the version
dropdown. This module owns that mapping, the on-disk ``versions.json`` list and
the ``--keep-minors`` retention decision. The writer performs the file moves.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from packaging.version import InvalidVersion, Version

VERSIONS_FILE = Path("versions.json")
#: A Docusaurus version label: exactly ``MAJOR.MINOR``, no leading zeros
#: (``"2.01"`` would be a second spelling of ``"2.1"``).
MINOR_RE = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)")


def minor(product_version: str) -> str:
    """Return the minor line a product version belongs to.

    ``"2.0.1"`` -> ``"2.0"``, ``"2.1.0a1"`` -> ``"2.1"``.

    Raises:
        ValueError: ``product_version`` is not a PEP 440 version.
    """
    try:
        version = Version(product_version)
    except InvalidVersion as exc:
        raise ValueError(f"not a version: {product_version!r}") from exc

    return f"{version.major}.{version.minor}"


def sort_minors(minors: Iterable[str]) -> list[str]:
    """Return the unique minor labels newest-first, ordered numerically.

    Numerically, not lexicographically: ``"2.10"`` sorts above ``"2.9"``, which a
    string sort gets backwards — and ``versions.json[0]`` is what Docusaurus uses
    as ``lastVersion``, so the wrong order silently misroutes ``/docs/``.
    """
    unique = set(minors)

    for label in unique:
        if not MINOR_RE.fullmatch(label):
            raise ValueError(f"expected a MAJOR.MINOR version label like '2.0', got {label!r}")

    return sorted(unique, key=Version, reverse=True)


def _rejection(data: object) -> str | None:
    """Return why ``data`` is not a Docusaurus version list, or ``None`` if it is."""
    if not isinstance(data, list):
        return f"expected a JSON array, got {type(data).__name__}"

    for label in data:
        if not isinstance(label, str) or not MINOR_RE.fullmatch(label):
            return f"expected 'MAJOR.MINOR' entries, got {label!r}"

    return None


def read_versions(site: Path) -> list[str]:
    """Load ``site / versions.json``; a missing file is an empty list.

    Raises:
        ValueError: the file is not a JSON array of ``MAJOR.MINOR`` strings.
    """
    path = site / VERSIONS_FILE

    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    if rejection := _rejection(data):
        raise ValueError(f"{path}: {rejection}")

    return data


def render_versions(minors: Iterable[str]) -> str:
    """Serialize the version list the way Docusaurus writes it (indent 2, newest-first).

    Sorts itself: ``versions.json[0]`` is what ``/docs/`` routes to, so the order
    must not depend on the caller.
    """
    return json.dumps(sort_minors(minors), indent=2, ensure_ascii=False) + "\n"


def plan_versions(
    existing: Iterable[str],
    new_minor: str,
    keep_minors: int,
) -> tuple[list[str], list[str]]:
    """Return ``(kept, dropped)`` after adding ``new_minor`` and applying retention.

    ``kept`` is newest-first and at most ``keep_minors`` long; ``dropped`` is every
    minor line that falls off the end and whose snapshot the writer must delete.
    Re-ingesting a minor line that is already present is not a change to the list.

    Raises:
        ValueError: ``keep_minors`` is below 1, or ``new_minor`` is itself so old
            that it would be pruned by the same run that created it.
    """
    if keep_minors < 1:
        raise ValueError(f"--keep-minors must be at least 1, got {keep_minors}")

    ordered = sort_minors([*existing, new_minor])
    kept, dropped = ordered[:keep_minors], ordered[keep_minors:]

    if new_minor in dropped:
        raise ValueError(
            f"{new_minor} is older than the {keep_minors} retained minor line(s) "
            f"{kept}: the snapshot would be pruned by the run that created it. "
            f"Raise --keep-minors to publish it."
        )

    return kept, dropped