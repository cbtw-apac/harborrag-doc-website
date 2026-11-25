from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

from ingest.anchors import page_anchors
from ingest.frontmatter import FENCE_RE
from ingest.models import Doc

REPOSITORY_URL = "https://github.com/cbtw-apac/HarborRAG"
#: Serves the file bytes, so ``<img>`` can render it (a ``blob`` URL is an HTML page).
RAW_URL = "https://raw.githubusercontent.com/cbtw-apac/HarborRAG"
#: ``[text](target)`` and ``![alt](target)``, optional ``"title"`` kept in the suffix.
LINK_RE = re.compile(r'(?P<prefix>!?\[[^\]]*\]\()(?P<target>[^)\s]+)(?P<suffix>(?:\s+"[^"]*")?\))')
#: ``src="..."`` / ``srcset="..."`` in raw HTML (``<img>``, ``<source>``); not ``data-src``.
HTML_ATTR_RE = re.compile(
    r"""(?<![\w-])(?P<attr>src|srcset)=(?P<quote>["'])(?P<value>[^"']*)(?P=quote)""",
    re.IGNORECASE,
)
#: ``https:``, ``mailto:`` ... and protocol-relative ``//host``.
EXTERNAL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


@dataclass(frozen=True)
class BrokenLink:
    source_path: PurePosixPath
    link: str
    #: 1-based line in the doc body (for bridged package READMEs the facts
    #: table shifts it by a few lines). Not part of equality.
    line: int | None = field(default=None, compare=False)
    #: ``"broken link"`` (target missing) or ``"broken anchor"`` (target exists,
    #: ``#anchor`` is not on it).
    reason: str = field(default="broken link", compare=False)

    def __str__(self) -> str:
        where = f"{self.source_path}:{self.line}" if self.line else f"{self.source_path}"
        return f"{where}: {self.reason} {self.link}"

#: ``{target path (docs-dir relative, POSIX): anchor ids}``, see ``build_anchor_index``.
AnchorIndex = dict[str, set[str]]

def build_anchor_index(docs: list[Doc]) -> AnchorIndex:
    """Return the anchors of every page, keyed by ``Doc.target_path``.

    Keyed by target (not source) path because that is what the link mapping
    values are: ``docs/TOC.md`` maps to the first sidebar doc, bridged files to
    ``project/*.md`` / ``packages/*.md``, so one lookup covers all of them.
    Must run on the raw bodies, before ``rewrite_links`` / ``apply_frontmatter``.
    """
    return {d.target_path.as_posix(): page_anchors(d.body) for d in docs}


def anchor_ok(anchor: str, *, target: str, anchors: AnchorIndex | None) -> bool:
    """``True`` unless ``anchor`` (``"#x"``) is known to be missing from page ``target``.

    No index, empty anchor (``x.md#``) or a target that is not an ingested page
    (absolute ``/docs/...`` mapping values) -> nothing to check -> ``True``.
    """
    if anchors is None or anchor in ("", "#") or target not in anchors:
        return True

    fragment = anchor[1:]
    page = anchors[target]
    return fragment in page or unquote(fragment) in page

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


def raw_url(resolved: PurePosixPath) -> str:
    """Return the raw-content URL of a repository file, for images.

    ``website/assets/logos/logo.png`` -> ``RAW_URL/main/website/assets/logos/logo.png``
    """
    return f"{RAW_URL}/main/{quote(resolved.as_posix(), safe='/')}"


def rewrite_link(
    target: str,
    *,
    doc: Doc,
    mapping: dict[Path, str],
    source_root: Path,
    image: bool = False,
    anchors: AnchorIndex | None = None,
    on_broken_anchor=None,
) -> str | None:
    """Return the rewritten link, or ``None`` when it is broken.

    Order of the rules (first match wins):

    1. not ``is_rewritable``                       -> ``target`` unchanged
    2. ``resolve`` returns ``None``                -> broken
    3. resolved path in ``mapping``                -> ``site_link(...)`` + anchor
    4. ``image`` and resolved path is a file in
       ``source_root`` (``docs/`` included)        -> ``raw_url(...)``
       (the site does not copy assets, so the image is served from GitHub)
    5. resolved path exists in ``source_root`` and
       is **outside** ``docs/``                    -> ``github_url(...)`` + anchor
       (config/*.yaml, clients/typescript, unpublished package READMEs)
    6. anything else                               -> broken
       (missing file, or a docs/ page that is not published)
    """

    if target.startswith("#"):
        own = doc.target_path.as_posix()
        if not anchor_ok(target, target=own, anchors=anchors):
            if on_broken_anchor:
                on_broken_anchor()
            return None
        return target

    if not is_rewritable(target):
        return target

    path, anchor = split_anchor(target)
    source_path = PurePosixPath(doc.source_path.as_posix())

    resolved = resolve(source_path, path)

    if resolved is None:
        return None

    value = mapping.get(Path(resolved.as_posix()))
    if value is not None:
        if not anchor_ok(anchor, target=value, anchors=anchors):
            if on_broken_anchor:
                on_broken_anchor()
            return None
        return site_link(value, from_target=PurePosixPath(doc.target_path.as_posix())) + anchor

    full = source_root / resolved
    if image and full.is_file():
        return raw_url(resolved)

    if resolved.parts and resolved.parts[0] != "docs" and full.exists():
        return github_url(resolved, is_dir=full.is_dir()) + anchor

    return None


# --------------------------------------------------------------------------- body


def _rewrite_srcset(value: str, rewrite) -> str | None:
    """Rewrite each URL of a ``srcset``, keeping its descriptor; ``None`` if any is broken.

    ``"a.png, b.png 2x"`` -> ``"<raw a.png>, <raw b.png> 2x"``
    Every broken URL is reported by ``rewrite`` before ``None`` is returned.
    """
    candidates = []
    ok = True
    for candidate in value.split(","):
        url, _, descriptor = candidate.strip().partition(" ")
        if not url:
            continue

        new_url = rewrite(url, image=True)
        if new_url is None:
            ok = False
            continue

        candidates.append(f"{new_url} {descriptor.strip()}".rstrip())

    return ", ".join(candidates) if ok else None


def rewrite_links(
    doc: Doc,
    *,
    mapping: dict[Path, str],
    source_root: Path,
    anchors: AnchorIndex | None = None,
) -> list[BrokenLink]:
    """Rewrite every link in ``doc.body`` in place; return the broken ones.

    Covers Markdown links/images and the ``src`` / ``srcset`` of raw HTML
    (``<img>``, ``<picture><source>``), whose values are always images.
    Lines inside fenced code blocks are left alone (same fence tracking as
    ``frontmatter._paragraphs``). A broken link is kept unchanged in the body.
    """
    broken: list[BrokenLink] = []
    source_path = PurePosixPath(doc.source_path.as_posix())
    line_no = 0
    
    def _rewrite(target: str, *, image: bool) -> str | None:
        reason = ["broken link"]

        def _anchor():
            reason[0] = "broken anchor"

        new_link = rewrite_link(
            target,
            doc=doc,
            mapping=mapping,
            source_root=source_root,
            image=image,
            anchors=anchors,
            on_broken_anchor=_anchor,
        )
        if new_link is None:
            broken.append(BrokenLink(source_path, target, line=line_no, reason=reason[0]))
        return new_link

    def _sub(match):
        new_link = _rewrite(match["target"], image="![" in match["prefix"])
        if new_link is None:
            return match[0]
        return match["prefix"] + new_link + match["suffix"]

    def _sub_attr(match):
        value = match["value"]
        if match["attr"].lower() == "srcset":
            new_value = _rewrite_srcset(value, _rewrite)
        else:
            new_value = _rewrite(value, image=True) if value else value

        if new_value is None:
            return match[0]
        return f"{match['attr']}={match['quote']}{new_value}{match['quote']}"

    doc_lines = doc.body.splitlines(keepends=True)
    new_lines = []
    in_fence = False
    for line_no, line in enumerate(doc_lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence

        if not in_fence:
            line = LINK_RE.sub(_sub, line)
            line = HTML_ATTR_RE.sub(_sub_attr, line)

        new_lines.append(line)

    doc.body = "".join(new_lines)

    return broken


def apply_links(docs: list[Doc], *, mapping: dict[Path, str], source_root: Path) -> None:
    """Rewrite links in every doc; raise ``BrokenLinksError`` listing all broken links.

    All docs are processed before raising, so one run shows every problem.
    """
    broken = []
    anchors = build_anchor_index(docs)
    for doc in docs:
        bk = rewrite_links(doc, mapping=mapping, source_root=source_root, anchors=anchors)
        broken.extend(bk)

    if broken:
        raise BrokenLinksError(broken)
