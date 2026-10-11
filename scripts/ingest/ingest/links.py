from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from ingest.frontmatter import FENCE_RE
from ingest.models import Doc

REPOSITORY_URL = "https://github.com/cbtw-apac/HarborRAG"
#: ``[text](target)`` and ``![alt](target)``, optional ``"title"`` kept in the suffix.
LINK_RE = re.compile(r'(?P<prefix>!?\[[^\]]*\]\()(?P<target>[^)\s]+)(?P<suffix>(?:\s+"[^"]*")?\))')
#: ``https:``, ``mailto:`` ... and protocol-relative ``//host``.
EXTERNAL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


@dataclass(frozen=True)
class BrokenLink:
    source_path: PurePosixPath
    link: str

    def __str__(self) -> str:
        return f"{self.source_path}: {self.link}"


class BrokenLinksError(Exception):
    """Raised once with every broken link, so a single run lists them all."""

    def __init__(self, broken: list[BrokenLink]) -> None:
        self.broken = broken
        super().__init__("broken links:\n" + "\n".join(f"  {b}" for b in broken))


# --------------------------------------------------------------------------- parse


def is_rewritable(target: str) -> bool:
    """Return ``False`` for links left untouched: external URLs and pure anchors.

    ``https://github.com/...`` / ``mailto:x`` / ``//cdn`` -> False
    ``#section``                                          -> False
    ``../x.md`` / ``x.md#a`` / ``/abs``                   -> True
    """
    return not (EXTERNAL_RE.match(target) or target.startswith("#"))


def split_anchor(target: str) -> tuple[str, str]:
    """Split ``"x.md#anchor"`` -> ``("x.md", "#anchor")``; no ``#`` -> ``(target, "")``."""
    before, sep, after = target.partition("#")

    if sep:
        return before, "#" + after

    return target, ""


def resolve(source_path: PurePosixPath, link_path: str) -> PurePosixPath | None:
    """Return the HarborRAG-root-relative path ``link_path`` points to.

    ``docs/developers/README.md`` + ``../../CONTRIBUTING.md`` -> ``CONTRIBUTING.md``
    ``docs/getting-started/README.md`` + ``quick-start.md``   -> ``docs/getting-started/quick-start.md``
    ``docs/users/configuration/x.md`` + ``../../../config/``  -> ``config``

    Returns ``None`` when the link climbs above the repository root.
    """
    joined = posixpath.normpath(posixpath.join(str(source_path.parent), link_path))

    if joined == ".." or joined.startswith("../"):
        return None

    return PurePosixPath(joined)


# --------------------------------------------------------------------------- route


def site_link(value: str, *, from_target: PurePosixPath) -> str:
    """Turn a mapping value into the link written in the page at ``from_target``.

    ``from_target`` is the current doc's target path (``Doc.target_path``,
    relative to the docs dir).

    ``"/docs/project/contributing"`` (absolute)          -> unchanged
    ``"users/configuration/README.md"`` from
    ``users/chat/README.md``                             -> ``../configuration/README.md``
    ``"users/chat/models.md"`` from ``users/chat/README.md`` -> ``models.md``
    """
    if value.startswith("/"):
        return value

    return posixpath.relpath(value, start=str(from_target.parent))


def github_url(resolved: PurePosixPath, *, is_dir: bool) -> str:
    """Return the GitHub URL of a repository file that is not a site page.

    ``config/models.example.yaml`` -> ``REPOSITORY_URL/blob/main/config/models.example.yaml``
    ``clients/typescript`` (dir)   -> ``REPOSITORY_URL/tree/main/clients/typescript``
    """
    view = "tree" if is_dir else "blob"
    return f"{REPOSITORY_URL}/{view}/main/{quote(resolved.as_posix(), safe='/')}"


def rewrite_link(
    target: str,
    *,
    doc: Doc,
    mapping: dict[Path, str],
    source_root: Path,
) -> str | None:
    """Return the rewritten link, or ``None`` when it is broken.

    Order of the rules (first match wins):

    1. not ``is_rewritable``                       -> ``target`` unchanged
    2. ``resolve`` returns ``None``                -> broken
    3. resolved path in ``mapping``                -> ``site_link(...)`` + anchor
    4. resolved path exists in ``source_root`` and
       is **outside** ``docs/``                    -> ``github_url(...)`` + anchor
       (config/*.yaml, clients/typescript, unpublished package READMEs)
    5. anything else                               -> broken
       (missing file, or a docs/ page that is not published)
    """
    if not is_rewritable(target):
        return target

    path, anchor = split_anchor(target)
    source_path = PurePosixPath(doc.source_path.as_posix())

    resolved = resolve(source_path, path)

    if resolved is None:
        return None

    value = mapping.get(Path(resolved.as_posix()))
    if value is not None:
        return site_link(value, from_target=PurePosixPath(doc.target_path.as_posix())) + anchor

    full = source_root / resolved
    if resolved.parts and resolved.parts[0] != "docs" and full.exists():
        return github_url(resolved, is_dir=full.is_dir()) + anchor

    return None


# --------------------------------------------------------------------------- body


def rewrite_links(
    doc: Doc,
    *,
    mapping: dict[Path, str],
    source_root: Path,
) -> list[BrokenLink]:
    """Rewrite every link in ``doc.body`` in place; return the broken ones.

    Lines inside fenced code blocks are left alone (same fence tracking as
    ``frontmatter._paragraphs``). A broken link is kept unchanged in the body.
    """
    broken: list[BrokenLink] = []

    def _sub(match):
        new_link = rewrite_link(match["target"], doc=doc, mapping=mapping, source_root=source_root)
        if new_link is None:
            broken.append(BrokenLink(PurePosixPath(doc.source_path.as_posix()), match["target"]))
            return match[0]
        else:
            return match["prefix"] + new_link + match["suffix"]

    doc_lines = doc.body.splitlines(keepends=True)
    new_lines = []
    in_fence = False
    for line in doc_lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence

        if not in_fence:
            line = LINK_RE.sub(_sub, line)

        new_lines.append(line)

    doc.body = "".join(new_lines)

    return broken


def apply_links(docs: list[Doc], *, mapping: dict[Path, str], source_root: Path) -> None:
    """Rewrite links in every doc; raise ``BrokenLinksError`` listing all broken links.

    All docs are processed before raising, so one run shows every problem.
    """
    broken = []
    for doc in docs:
        bk = rewrite_links(doc, mapping=mapping, source_root=source_root)
        broken.extend(bk)

    if broken:
        raise BrokenLinksError(broken)
