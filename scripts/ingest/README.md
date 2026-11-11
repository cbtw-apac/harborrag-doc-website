# HarborRAG docs ingest

Copies the published documentation of a [HarborRAG](https://github.com/cbtw-apac/HarborRAG)
checkout into this Docusaurus site (`website/`), so the site always mirrors upstream.

It reads Markdown from HarborRAG, checks it, rewrites it for Docusaurus/MDX, and replaces
`website/docs/` and `website/sidebars.ts` in one atomic step. Nothing on the site is touched
until every check has passed.

## Quick start

From the repository root, with HarborRAG checked out next to this repo (`../HarborRAG`):

```bash
make sync-local                       # ingest HarborRAG HEAD into website/docs (the "Next" docs)
make sync-local HARBORRAG=/path/to/HarborRAG
make check                            # what CI runs: ingest tests + lint, then site typecheck + build
```

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

## What gets published

`collect.py` decides the published set (mirrors HarborRAG's `website/check_docs_publish_path.py`).
Everything else in the checkout is treated as internal and never reaches the site.

| HarborRAG source | Site page (under `website/docs/`) |
| --- | --- |
| `docs/**/*.md` (except `docs/TOC.md`) | same path, minus the leading `docs/` |
| `README.md` | `project/overview.md` |
| `CONTRIBUTING.md` | `project/contributing.md` |
| `SECURITY.md` | `project/security.md` |
| `CHANGELOG.md` | `project/changelog.md` |
| `packages/<name>/README.md` | `packages/<name>.md`, with a facts table read from `packages/<name>/pyproject.toml` |
| `docs/TOC.md` | not a page; it becomes `website/sidebars.ts` |

## Pipeline

`runner.build_plan` does all the work in memory; `writer.write` is the only step that touches disk.

1. **collect** (`collect.py`): list the published files.
2. **publication guard** (`guard.publication`): fail if any path or line matches a pattern in
   [`deny.txt`](deny.txt) (one case-insensitive regex per line).
3. **load pages** (`runner.py`, `bridge.py`): read `docs/` pages and bridge the root and package files.
4. **branding guard** (`guard.branding`): fail on predecessor branding. A line is exempt when it, or
   the line before it, contains `branding-compat`.
5. **TOC** (`toc.py`): parse `docs/TOC.md` into sidebar categories.
6. **MDX check** (`mdx.find_mdx_unsafe`): read each page's source file and fail with `path:line`
   (line numbers as in the source file) on what MDX would reject or evaluate: a `{` in prose,
   a `<` followed by something that cannot start a tag (`<=`, `<5`; `a < b` is fine), or a
   `<!--` without `-->` on the same line. Fenced blocks, inline code (also across lines) and
   closed comments are ignored.
7. **links** (`links.py`): rewrite relative links to site links; files that are not published
   point to GitHub (`blob`/`tree`) or `raw.githubusercontent.com` for images. Broken links fail.
8. **MDX rewrite** (`mdx.mdx_sanitize`): rewrite what MDX rejects but can be fixed: autolinks
   `<https://…>`, unclosed void tags, one-line `<!-- -->` comments.
9. **frontmatter** (`frontmatter.py`): move the H1 into `title`, take the first prose paragraph as
   `description`, and add `custom_edit_url` and `source_path`. No per-sync values (sha, position)
   go into pages, so a new upstream commit with the same docs produces no diff.
10. **write** (`writer.py`): see below.

Every guard collects all failures before raising, so one run reports every problem.

## How the site is written

`writer.write` returns one of these outcomes (all exit 0):

| Outcome | When | Effect on the site |
| --- | --- | --- |
| `dry-run` | `--dry-run` | none; prints the file plan |
| `already-synced` | `sync-state.json` already records this `--source-sha` (skipped by `--force`) | none |
| `no-changes` | the rendered pages and `sidebars.ts` equal what is on disk | none, not even `sync-state.json` |
| `written` | anything else | `docs/`, `sidebars.ts`, then `sync-state.json` |

Writes are atomic:

- Pages are rendered into a staging dir `website/.ingest-*`, then swapped with `website/docs/`
  (`swap_dir`). A failure leaves the old `docs/` in place.
- `sidebars.ts` and `sync-state.json` are written through a temp file + `os.replace`.
- `sync-state.json` is written last; it is the "done" marker.
- `versions.json` is never modified.

`.ingest-*` is in `.gitignore`, so a crash mid-write cannot leave staging files in `git status`.
If one is left behind, delete it.

## CLI

`make sync-local` is the normal entry point. To call the CLI directly:

```bash
cd scripts/ingest
uv run ingest.py \
  --source ../../../HarborRAG \
  --site ../../website \
  --channel main \
  --product-version auto \
  --source-ref local \
  --source-sha "$(git -C ../../../HarborRAG rev-parse HEAD)"
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `--source` | yes | Path to the HarborRAG checkout. |
| `--site` | yes | Path to the Docusaurus site (`website/`). |
| `--channel` | yes | `main` or `prerelease`: write the "Next" docs. `stable` is not available yet (Phase 5). |
| `--product-version` | yes | Version string such as `2.1.0a1`, or `auto` to read `[project].version` from the source `pyproject.toml`. For `prerelease`, the version must be a pre-release. |
| `--source-ref` | yes | Git ref being ingested (`local`, `main`, `refs/tags/…`); recorded in `sync-state.json`. |
| `--source-sha` | yes | Commit SHA being ingested; recorded in `sync-state.json` and used for `already-synced`. |
| `--keep-minors` | no | Minor versions to keep (default `2`); reserved for stable snapshots. |
| `--dry-run` | no | Print the file plan and exit without writing. |
| `--force` | no | Skip the `already-synced` check and rebuild. Guards still run. |

## Layout

```text
scripts/ingest/
├── ingest.py            # CLI: parses flags, resolves --product-version, calls ingest.run
├── deny.txt             # publication deny-list (regex per line)
├── pyproject.toml       # uv project; ruff and pytest config
├── uv.lock
├── ingest/
│   ├── models.py        # Channel, IngestRequest, Doc, SyncState
│   ├── runner.py        # build_plan (pipeline) and run (entry point)
│   ├── collect.py       # published file set
│   ├── bridge.py        # root files and package READMEs -> project/, packages/
│   ├── guard.py         # publication and branding guards
│   ├── toc.py           # docs/TOC.md -> sidebars.ts
│   ├── links.py         # link rewriting
│   ├── mdx.py           # MDX rewrites and unsafe-prose detector
│   ├── frontmatter.py   # title, description, edit URL; page rendering
│   ├── writer.py        # staging, atomic swap, sync-state.json
│   └── versions.py      # placeholder for stable snapshots (Phase 5)
└── tests/
    ├── fixtures/mini_harborrag/       # small HarborRAG checkout used end to end
    ├── fixtures/mini_harborrag_bad/   # same, with denied content
    └── test_*.py                      # one file per module; test_runner.py runs the whole pipeline
```

## Development

```bash
cd scripts/ingest
uv sync                    # install (CI uses `uv sync --frozen`)
uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # format
```

CI (`.github/workflows/pr-check.yml`) runs `uv run pytest` and `uv run ruff check .` on every PR.

`tests/test_runner.py` snapshots the full page list and `sidebars.ts` produced from
`mini_harborrag`. When you change the fixture, `TOC.md` handling or the sidebar format on
purpose, update `EXPECTED_PAGES` / `EXPECTED_SIDEBARS_TS` there and review the diff.

## Troubleshooting

| Error | Fix |
| --- | --- |
| `Publication denied. Forbidden content found in:` | Remove the content upstream, or (if it is safe) adjust `deny.txt`. |
| `path:line: <match>` from the branding guard | Update the wording upstream, or mark an intended mention with `<!-- branding-compat -->` on that line or the line above. |
| `MDX-unsafe content in source docs:` | Upstream: wrap the text in backticks or a code fence, or escape it. |
| Broken link errors | Fix the link upstream, or publish the target file. |
| `Could not determine product version from source` | The source has no `pyproject.toml` with `[project].version`; pass `--product-version` explicitly. |
| `Version/channel mismatch` | Use `prerelease` only for pre-release versions (`2.1.0a1`); `main` accepts any version. |
| `Stable snapshots are not available yet` | `--channel stable` (and `make sync-stable`) lands in Phase 5. |
