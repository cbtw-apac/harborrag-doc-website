# HarborRAG documentation website — two-repo sync architecture

| | |
|---|---|
| Status | Draft for review (Nguyen, Huy) |
| Target release | HarborRAG v2.0.0 stable |
| Repos | Source: `cbtw-apac/HarborRAG` · Site: `cbtw-apac/harborrag-doc-website` (public since 16 Sep 2026, `main`) |
| Related | HARBORRAG-837 (docs & website), Notification epic, ragflow-docs (reference pattern) |
| Last updated | 15 Sep 2026 (§8 tokens per DevOps review) |

## 1. Purpose

Decouple the public documentation website from the HarborRAG monorepo so that the site has its own toolchain, release cadence and design, while `docs/` in HarborRAG stays the single source of truth for content, and the site updates itself on every HarborRAG release — including sub-package hotfixes — without anyone copying files by hand.

This document is the architecture. The companion page "HarborRAG documentation website — scaffold and build guide" is the step-by-step implementation.

## 2. Decisions (agreed 14 Sep 2026)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Site framework | Docusaurus 3.x (TypeScript, classic preset) | Built-in versioned docs, MDX, search; React page for the three.js landing; same stack as ragflow-docs so the pattern is copyable. |
| D2 | How the site learns about changes | Push: `repository_dispatch` from HarborRAG Actions on every published release and on `docs/**` pushes to `main`; plus a nightly cron and manual dispatch as fallbacks | ragflow-docs polls every 3 h. Push removes the lag for hotfixes; cron covers a lost event or an expired token. |
| D3 | Hosting | GitHub Pages on `harborrag-doc-website`, deployed from Actions | Same as today; `DOCS_SITE_URL` already exists in HarborRAG; custom domain can be added later without changing the pipeline. |
| D4 | Versions shown | `Next` (= HarborRAG `main`) + the last 2 stable minor lines (`2.0`, then `2.1` …); patch/hotfix releases refresh their minor line's snapshot; pre-releases (a/b/rc) only refresh `Next` and show a banner | Small, predictable site; hotfix docs land in the right place; no per-tag sprawl. |
| D5 | Where synced content lives | Committed to the site repo under `website/docs/` (Next) and `website/versioned_docs/version-<X.Y>/` via an auto-merged PR (ragflow pattern) | Every content change is a reviewable commit; the site repo builds standalone; rollback is `git revert`. |
| D6 | Ingest tooling | Python (`uv`) script in the site repo; Docusaurus build in Node | Team is Python-first; the link-rewrite rules already exist in `website/builder/markdown_links.py` and can be ported. Two toolchains in CI is acceptable. |
| D7 | Contribution rule | Content PRs go to `cbtw-apac/HarborRAG/docs`; PRs that edit synced content in the site repo are closed by policy (README + CODEOWNERS) | Same rule ragflow-docs states in its README. `editUrl` on every page points at HarborRAG. |

## 3. Current state (as-is, HarborRAG 2.0.0a1)

The website lives inside the monorepo: `website/build.py` plus `website/builder/*` (≈2.6k lines of Python, Jinja2 templates, Bootstrap). It renders `docs/TOC.md` (section order), `docs/**/*.md` (29 files, no frontmatter, no images), the four root files (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`), `packages/*/README.md` and version metadata from `pyproject.toml`. Two workflows drive it:

| Workflow | Triggers | Deploys? |
|---|---|---|
| `docs-auto.yml` | push to `main` touching docs/website paths; `workflow_run` of "Test and Coverage"; `release: published` | Only when the release tag matches `harborrag-v*` |
| `docs-manual.yml` | `workflow_dispatch` with `deploy` flag | Yes, if asked |

Consequences: a hotfix released as `harborrag-adapters-v2.0.1` never redeploys the site; a docs fix merged to `main` is built but not published until the next main-package release; and the site's look is coupled to the monorepo's Python toolchain. The same mechanism existed in qdrant-loader 1.0.3 (tag prefix `qdrant-loader-v*`).

Two guards in `website/` are worth keeping in spirit: `check_publication.py` (blocks private reference material — currently the `HARBORRAG_ARCHITECTURE.md` / `harborrag-architecture.html` names — from reaching the public build) and `check_branding.py`.

## 4. Reference pattern: ragflow-docs

`infiniflow/ragflow-docs` is Docusaurus 3.9 with `versioned_docs/`, `versioned_sidebars/`, `versions.json`. `.github/workflows/sync_docs.yml` runs on a 3-hour cron and manual dispatch: check out `infiniflow/ragflow` and `ragflow-docs` side by side, run `website/sync_docs.sh`, which (1) regenerates `versions.json` from the source repo's semver tags (newest tag per major.minor, last N), (2) for each version checks out the tag and `rsync --delete`s `docs/` into `versioned_docs/version-<tag>/`, copying a default sidebar, (3) syncs `main` into `docs/`, then (4) opens a PR with `peter-evans/create-pull-request`, auto-approves it with a bot identity and enables squash auto-merge. Vercel deploys on merge. Its README says PRs to the docs repo are not merged.

What we keep: the two-checkout layout, tag-derived `versions.json`, rsync-per-version, auto-merged PR. What we change: push trigger instead of polling, a real ingest step (frontmatter, link rewriting, TOC → sidebar, publication guard) instead of a raw rsync, snapshot keyed by minor line instead of by tag, and GitHub Pages instead of Vercel.

## 5. Target architecture

```
cbtw-apac/HarborRAG                              cbtw-apac/harborrag-doc-website
─────────────────────────────                    ─────────────────────────────────────────────
docs/**  README  CHANGELOG  ...                  .github/workflows/
packages/*/README.md  pyproject.toml               sync.yml     (repository_dispatch | schedule | workflow_dispatch)
                                                   pr-check.yml (build + link check on PRs)
.github/workflows/docs-dispatch.yml                deploy.yml   (push main -> build -> Pages)
  on: release.published (any package tag)        scripts/ingest/        (Python, uv)
      push main paths docs/** README ...           ingest.py  toc.py  links.py  guard.py
      workflow_dispatch                          website/               (Docusaurus)
  -> POST repository_dispatch ───────────────►     docs/                 = Next (HarborRAG main)
     event_type: harborrag-docs-sync               versioned_docs/version-2.0/   = 2.0.x stable
     client_payload: {ref, tag, version, ...}      versioned_sidebars/  versions.json
                                                   sync-state.json      (source commit per version)
                                                   src/pages/index.tsx  (three.js landing)
                                                 ────────────────────────────────────────────
                                                 GitHub Pages: https://cbtw-apac.github.io/harborrag-doc-website/
```

### 5.1 Components

| Component | Repo | Responsibility |
|---|---|---|
| `docs-dispatch.yml` | HarborRAG | Emit one `repository_dispatch` to the site repo with a typed payload whenever docs may have changed: any `release: published` (all 8 package tag prefixes), any push to `main` touching the published path set, or manual. Also posts the existing Teams card on failure. |
| `sync.yml` | site | Receive the event (or cron/manual), resolve which snapshot(s) to refresh, run the ingest, open/refresh the sync PR, auto-approve, enable auto-merge. Idempotent: a re-run for the same source commit produces no diff and no PR. |
| `scripts/ingest/` | site | Deterministic transform of a HarborRAG checkout at a given ref into a Docusaurus docs tree: copy, frontmatter, link rewrite, TOC → sidebar, publication guard, branding check. |
| `pr-check.yml` | site | On every PR: `pnpm build` with `onBrokenLinks: 'throw'`, upload the built site as an artifact for preview. |
| `deploy.yml` | site | On push to `main`: build, upload Pages artifact, deploy. Concurrency group `pages`, no cancel-in-progress. |
| `versions.json` + `sync-state.json` | site | `versions.json` is what Docusaurus reads (`["2.0"]`). `sync-state.json` records `{current: SyncEntry, versions: {"X.Y": SyncEntry}}` with `SyncEntry = {label, channel, source_ref, source_sha, synced_at}` for idempotency and audit; the site config validates it at build time. |
| GitHub Pages | site | Static hosting. Source = GitHub Actions. |

### 5.2 Event contract

`repository_dispatch` to `cbtw-apac/harborrag-doc-website`:

```json
{
  "event_type": "harborrag-docs-sync",
  "client_payload": {
    "source_repo": "cbtw-apac/HarborRAG",
    "ref": "refs/tags/harborrag-adapters-v2.0.1",
    "sha": "60609c80…",
    "reason": "release",                 // release | push | manual
    "tag": "harborrag-adapters-v2.0.1",  // null for push
    "package": "harborrag-adapters",      // null for push
    "product_version": "2.0.1",           // root pyproject.toml [project].version at sha
    "channel": "stable",                  // stable | prerelease | main
    "run_url": "https://github.com/cbtw-apac/HarborRAG/actions/runs/…"
  }
}
```

Rules the site applies (payload is a hint, never trusted blindly — see §8):

| `channel` | Derived from | Snapshot(s) refreshed |
|---|---|---|
| `main` | push to `main` | `Next` (`website/docs/`) from `main` |
| `prerelease` | PEP 440 `is_prerelease` of `product_version` (a1, b1, rc1) | `Next` from the tag, with `versionBanner`/label "2.0.0a1" |
| `stable` | otherwise | `versioned_docs/version-<major.minor>/` from the tag; `Next` untouched |

Product version comes from the root `pyproject.toml` at the release commit, not from the tag name. That is why a sub-package hotfix tag (`harborrag-adapters-v2.0.1`) still lands in the `2.0` snapshot: what matters is which product line the commit belongs to.

### 5.3 Flows

**A. Stable release (incl. hotfix).** `release.py` creates GitHub releases for the 8 packages → each `release: published` fires `docs-dispatch.yml` → 8 dispatches arrive within minutes → `sync.yml` concurrency group `sync-<major.minor>` serialises them → the first run refreshes `version-2.0` from the tag commit and opens PR `sync/2.0@<shortsha>`; subsequent runs see the same `source_commit` in `sync-state.json` and exit "no change" → PR auto-approved by the bot identity, auto-merged (squash) once `pr-check` is green → `deploy.yml` publishes. End-to-end target: under 15 minutes from release to live.

**B. Docs fix merged to `main` (no release).** Push matching the path filter → dispatch `channel: main` → `Next` refreshed → same PR/merge/deploy path. Docs fixes are therefore visible on `Next` the same day, and reach the stable snapshot with the next patch release.

**C. Pre-release (`2.1.0a1`).** Refreshes `Next` only and sets the version label so readers see they are on a pre-release. Stable readers on `2.0` see nothing change.

**D. New minor line (`2.1.0` stable).** Ingest adds `version-2.1`, prepends `"2.1"` to `versions.json`, and drops the oldest entry when more than 2 stable lines exist (its folder is deleted in the same PR — the snapshot is still recoverable from git history and from the HarborRAG tag). `lastVersion` becomes `2.1`; `/docs/` routes to it.

**E. Fallbacks.** Nightly cron: list HarborRAG tags via the API, compute the expected snapshot set, compare against `sync-state.json`, refresh anything stale. Manual `workflow_dispatch` with `ref` and `channel` inputs for one-off repairs.

## 6. Content ingest pipeline (site repo)

Input: a shallow, sparse checkout of HarborRAG at `sha` limited to `docs/`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, `LICENSE`, `pyproject.toml`, `packages/*/README.md`, `packages/*/pyproject.toml`. Output: a Docusaurus docs tree plus a sidebar file. Steps, all deterministic:

1. **Publication guard** (port of `check_publication.py`): fail the run if any input file name or content matches the private-reference deny-list; keep the list in the site repo so it can grow without a HarborRAG release.
2. **Copy** `docs/**/*.md` → target docs dir, preserving paths; drop `docs/TOC.md` (it becomes the sidebar, not a page).
3. **Bridge root and package files** into the docs tree so relative links resolve: `README.md` → `project/overview.md`, `CONTRIBUTING.md` → `project/contributing.md`, `SECURITY.md` → `project/security.md`, `CHANGELOG.md` → `project/changelog.md`, `packages/<name>/README.md` → `packages/<name>.md` with version/PyPI facts from its `pyproject.toml` injected as a small info table at the top (the current builder already does the equivalent).
4. **Frontmatter**: HarborRAG docs have none. Generate `title` (first H1, then strip it), `sidebar_position` (order from TOC.md), `description` (first paragraph, truncated), `custom_edit_url` (HarborRAG blob URL at the source path on `main`), `source_ref`/`source_sha` (for the "synced from" footer). Never require frontmatter in the source repo.
5. **Link rewrite** (port of `markdown_links.py`): `../../CONTRIBUTING.md` → `/project/contributing`; `../packages/harborrag/README.md` → `/packages/harborrag`; intra-docs `x/README.md` → directory route; `.md#anchor` preserved; absolute `github.com/cbtw-apac/HarborRAG` links untouched; the "Last reviewed" footer line kept.
6. **Sidebar generation**: `docs/TOC.md` sections and order → `sidebars.ts` (Next) or `versioned_sidebars/version-<X.Y>-sidebars.json`. Curated links in TOC that point outside docs (LICENSE, GitHub) become `type: link` items.
7. **Branding check** (port of `check_branding.py`), then **strict build** in `pr-check.yml` with `onBrokenLinks: 'throw'` and `onBrokenMarkdownLinks: 'throw'` — a broken link in source docs blocks the sync PR and is reported back with the source path, which is the right pressure on the source repo.

Not ingested: CI coverage and test-status pages (today under `site/coverage/`). They are CI artifacts, not documentation; keep them as an Actions artifact link from the Testing page until a separate decision is made (§11).

## 7. Versioning model

| Site version | Source | Route | Label |
|---|---|---|---|
| `Next` (Docusaurus `current`) | HarborRAG `main`, or the latest pre-release tag | `/docs/next/…` | "Next" or "2.1.0a1 (pre-release)" |
| `2.0` | newest `*-v2.0.x` stable tag's commit | `/docs/…` when it is `lastVersion`, else `/docs/2.0/…` | "2.0.x" (patch shown) |
| `1.x` | none — qdrant-loader 1.0.3 docs are not migrated | — | Landing links to the old site/README for 1.x |

`versions.json` holds minor lines only (`["2.0"]`). Docusaurus `lastVersion` = first entry. Each snapshot's `sync-state.json` entry carries the exact patch and commit so the UI can show "2.0.1 · synced from 60609c8".

## 8. Security and permissions

| Concern | Design |
|---|---|
| Token to send `repository_dispatch` | Fine-grained PAT (or GitHub App installation token) scoped to `harborrag-doc-website` only, permission `Contents: read & write`, stored in HarborRAG as secret `DOCS_DISPATCH_TOKEN`. Setting repo secrets needs **Admin** on HarborRAG — Nguyen holds Maintain, so this is an IT/org-owner action. |
| Tokens for the sync PR | PRs created with the default `GITHUB_TOKEN` do not trigger other workflows, so `pr-check` would never run. Use a PAT `DOCS_SYNC_TOKEN` (account A: Contents + Pull requests + Workflows write, this repo only) for `create-pull-request` and auto-merge, and a second PAT `APPROVER_PAT` (account B ≠ A: Pull requests write, this repo only) to post the `APPROVE` review — GitHub forbids self-approval. `GITHUB_TOKEN` is deliberately **not** used for approval: that needs "Allow GitHub Actions to create and approve pull requests", which in an org is gated by the org-level Actions policy and widens every workflow's token (DevOps review, 15 Sep 2026). Follow-up: a ruleset bypass for a dedicated bot account removes the approval step altogether. |
| Payload trust | The site never executes anything from the payload. It validates `source_repo == cbtw-apac/HarborRAG`, resolves `ref` via `git ls-remote` on that repo, and checks `sha` matches. Anything else is rejected and reported. |
| Public-content guard | Deny-list in the site repo, run before any file is copied; failing the guard fails the run and pings Teams. |
| Branch protection (site `main`) | Require `pr-check` status, allow auto-merge, restrict direct pushes. Dependabot for the Docusaurus toolchain. |
| Pages | Source: GitHub Actions; `deploy.yml` uses `id-token: write` + `pages: write` only. |
| Supply chain | Pin actions by SHA as HarborRAG already does; `pnpm install --frozen-lockfile`. |

## 9. Failure modes and runbook

| Failure | Effect on readers | Detection | Recovery |
|---|---|---|---|
| Dispatch token expired/revoked | Site goes stale after a release | Teams card from `docs-dispatch.yml` failure step; nightly cron still refreshes | Rotate `DOCS_DISPATCH_TOKEN` (admin) |
| Publication guard trips | No PR created; site unchanged | `sync.yml` fails, Teams card with the offending path | Fix source docs or the deny-list; re-run |
| Broken link in source docs | Sync PR fails `pr-check`; site unchanged | PR status + Teams | Fix link in HarborRAG `docs/`; next push re-syncs |
| Docusaurus build breaks on `main` | Previous deployment stays live | `deploy.yml` red | Fix/revert in site repo |
| 8 release dispatches at once | None | Concurrency group per minor line + `sync-state.json` dedupe | — |
| Snapshot needs a redo (bad ingest) | Wrong content on `2.0` | Reader report | `workflow_dispatch` with `ref` + `force: true`, or `git revert` the sync commit |
| GitHub Pages outage | Site down | Status page | Nothing to do; artifact of the last build is downloadable |

## 10. Migration from the in-repo website

| Phase | HarborRAG | Site repo | Exit check |
|---|---|---|---|
| 0 — Scaffold (week 1) | none | Docusaurus scaffold, ingest script, `pr-check`, `deploy`, first manual sync from `harborrag-v2.0.0a1` | Site builds and deploys to `cbtw-apac.github.io/harborrag-doc-website`; every 2.0.0a1 doc reachable; zero broken links |
| 1 — Parallel run | add `docs-dispatch.yml`; secrets set by admin | `sync.yml` live | A docs push to `main` appears on `Next` within 15 min; a test pre-release tag refreshes `Next` |
| 2 — Cut-over (with 2.0.0 stable) | set `DOCS_SITE_URL` to the new origin; `docs-auto.yml` stops deploying (build-only for the smoke check) or is removed; README/`pyproject` URLs updated | Landing page live; `2.0` snapshot created by the real release | New URL in release notes; old Pages site shows a redirect page |
| 3 — Clean-up (post-2.0.0) | delete `website/`, `tests/test_website_*.py`; keep `check_docs_publish_path.py` logic if still useful for authors | remove redirect after 30 days | HarborRAG CI no longer builds a site |

## 11. Open decisions

1. Coverage/test-status pages: drop from the public site (recommended), or ingest as a static "Quality" page fed by a second dispatch from "Test and Coverage"?
2. Repo/URL naming: keep `harborrag-doc-website` as the Pages path, or request a custom domain (`docs.harborrag.…`) from IT before cut-over so links in release notes are final?
3. Bot identity: fine-grained PATs on a service account vs. a GitHub App owned by the org (App is cleaner for rotation and audit; needs org-owner setup).
4. Does the landing page live in the site repo only (recommended), or should marketing copy also be synced from somewhere?
5. Search: Docusaurus local search plugin (no external service) vs. Algolia DocSearch (free for OSS, needs application).

## 12. Traceability to the 2.0.0 plan

| Brainstorm item | Covered by |
|---|---|
| 1. Doc-website | §5–7, scaffold guide |
| 2. Notification (docs ↔ repo) | `docs-dispatch.yml` (HarborRAG → site) and Teams cards on sync/deploy outcomes (site → team). If a site → HarborRAG signal is wanted later, `sync.yml` can post a commit status on the source `sha`. |
| Lam's test strategy §5.2 rows | Docs-sync mirrors correctly = ingest idempotency test; CI fails visibly = guard + Teams; visual identity = landing page; navigation/orphans = TOC-generated sidebar + `onBrokenLinks: throw`; release notes = `project/changelog` page per snapshot |
