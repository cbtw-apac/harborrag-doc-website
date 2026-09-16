# HarborRAG documentation website — scaffold and build guide

| | |
|---|---|
| Status | Draft for review (Nguyen, Huy; implementers Huyen, Hoang) |
| Repo | `cbtw-apac/harborrag-doc-website` (public since 16 Sep 2026, `main`) |
| Companion | "HarborRAG documentation website — two-repo sync architecture" (read that first) |
| Last updated | 16 Sep 2026 (§2 `future` flags corrected to `{v4, faster}` for 3.10, mermaid theme install, navbar parking, `/docs/next` route; §3 MDX 1 compat note. Earlier: 15 Sep — §2 typed JSON boundary, sync-state shape, TS 6 tsconfig; pnpm; §6.2 + §7 two-PAT approval per DevOps review) |

This is the implementation guide for the architecture page. It is written so that someone can scaffold the repo from zero, run it locally against a HarborRAG checkout, and wire the CI, in that order. Steps are numbered; each ends with a check.

## 0. Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Node.js | 20 LTS (22 also fine) | Docusaurus |
| pnpm | 10.33.0, pinned via `"packageManager"` in `website/package.json` | package manager — commit `pnpm-lock.yaml`; corepack is not needed. **Never run bare `pnpm self-update`**: pnpm 12 ships as `@pnpm/exe`, whose `pnpm` bin is a placeholder shell script that an *install build script* must replace with the native binary. pnpm 10 blocks dependency build scripts by default, so the upgrade leaves an unexecutable shim and every `pnpm` command dies (on Windows it opens the "how do you want to open this file" dialog). Pass a version — `pnpm self-update 10.33.0` — or use `$env:PNPM_VERSION` with `https://get.pnpm.io/install.ps1` |
| Python | 3.12 | ingest script (`uv`-managed, same as HarborRAG) |
| uv | latest | Python env for `scripts/ingest` |
| gh CLI | latest | testing `repository_dispatch`, PR automation locally, and repo settings (§7) without the browser |
| GNU Make | 4.x | the root `Makefile`. Windows: `winget install ezwinports.make`, and put `C:\Program Files\Git\bin` on PATH so make gets an `sh.exe` — without it make silently uses `cmd.exe` and every recipe fails on `grep`/`[ -d … ]` |
| actionlint | latest | linting `.github/workflows/`. PowerShell does not expand globs for external commands — run bare `actionlint` from the repo root and it auto-discovers them |
| A local HarborRAG checkout | any ref | local sync (`make sync-local`) |

Permissions you will need at some point: **Admin** on `harborrag-doc-website` (Pages settings, branch protection, secrets) and **Admin** on `HarborRAG` for one secret (`DOCS_DISPATCH_TOKEN`) — the latter is an IT/org-owner action.

## 1. Repository layout (target)

```
harborrag-doc-website/
├── .github/
│   ├── workflows/
│   │   ├── sync.yml            # repository_dispatch | schedule | workflow_dispatch → ingest → PR
│   │   ├── pr-check.yml        # build + link check on every PR; uploads site artifact
│   │   └── deploy.yml          # push main → build → GitHub Pages
│   ├── CODEOWNERS
│   └── dependabot.yml
├── scripts/
│   └── ingest/                 # Python, uv project
│       ├── pyproject.toml
│       ├── ingest.py           # CLI entry
│       ├── toc.py              # docs/TOC.md → sidebar JSON
│       ├── links.py            # link rewriting (ported from HarborRAG website/builder/markdown_links.py)
│       ├── frontmatter.py
│       ├── guard.py            # publication + branding guards (ported from check_publication.py / check_branding.py)
│       ├── versions.py         # tag discovery, minor-line policy, versions.json / sync-state.json
│       └── tests/
├── website/                    # Docusaurus site
│   ├── docusaurus.config.ts
│   ├── sidebars.ts             # GENERATED for Next — do not hand-edit
│   ├── versions.json           # GENERATED
│   ├── sync-state.json         # GENERATED
│   ├── docs/                   # GENERATED = Next
│   ├── versioned_docs/         # GENERATED
│   ├── versioned_sidebars/     # GENERATED
│   ├── src/
│   │   ├── css/custom.css      # theme tokens from the prototype
│   │   ├── pages/index.tsx     # landing page
│   │   ├── components/
│   │   │   ├── HeroGraph/      # three.js hero, lazy-loaded, poster fallback
│   │   │   ├── PipelineRail/   # "Six stages, one route" section
│   │   │   ├── PackageBasin/   # "Eight packages, one basin"
│   │   │   └── SyncedFrom.tsx  # footer chip: "synced from HarborRAG @ <sha>"
│   │   └── theme/              # swizzled DocItem footer (SyncedFrom), Navbar tweaks
│   ├── static/
│   │   ├── img/                # logo (designs/HarborRAG_logo-shape-SVG.svg), og image
│   │   └── fonts/              # only if licence allows self-hosting (see §6)
│   ├── package.json
│   └── tsconfig.json
├── Makefile                    # sync-local, dev, build, check
├── README.md                   # "content PRs go to cbtw-apac/HarborRAG/docs" + how to run
└── LICENSE
```

Generated paths are committed (decision D5) but marked in `.gitattributes` as `linguist-generated` and owned by the bot in `CODEOWNERS`, so human PRs touching them are flagged.

## 2. Scaffold Docusaurus

```bash
git clone git@github.com:cbtw-apac/harborrag-doc-website.git && cd harborrag-doc-website
printf 'auto-install-peers=true\n' > .npmrc          # Docusaurus has a wide peer tree; keeps pnpm quiet
pnpm dlx create-docusaurus@latest website classic --typescript --package-manager pnpm
cd website && pnpm install
rm -rf blog docs/* src/pages/markdown-page.md   # blog off, docs will be generated
# the classic preset does NOT include the mermaid theme, but the config below declares it:
pnpm add @docusaurus/theme-mermaid@3.10.2
# pin the manager so CI and every laptop use the same one:
pnpm pkg set packageManager="pnpm@$(pnpm --version)"
```

(Do not run `corepack enable` — it is unnecessary with pnpm already installed, and on macOS with the official Node installer it fails with `EACCES` on `/usr/local/bin`.)

**Seed the generated files once.** `versions.json`, `sync-state.json`, `sidebars.ts` and `docs/` are normally written by the ingest script (§3), which does not exist yet at this point, so the config below would fail to import them. Create them by hand once with empty content; after the first sync the script owns them.

```bash
cd website
echo '[]' > versions.json
cat > sync-state.json <<'EOF'
{
  "current": { "label": "Next", "channel": "main", "source_ref": null, "source_sha": null, "synced_at": null },
  "versions": {}
}
EOF
cat > sidebars.ts <<'EOF'
import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';
const sidebars: SidebarsConfig = { docs: [{ type: 'autogenerated', dirName: '.' }] };  // key must be "docs" (navbar sidebarId)
export default sidebars;
EOF
mkdir -p docs && printf -- '---\ntitle: HarborRAG documentation\n---\nContent is synced from `cbtw-apac/HarborRAG/docs`. First sync pending.\n' > docs/index.md
```

(Docusaurus refuses to build a docs version with zero documents, hence the placeholder page.)

`docusaurus.config.ts` essentials (only the parts that matter for this design). Under `strict`, TypeScript types a JSON import from its literal contents, so the empty seed files come out as `never[]` and `{ current: … }` with no index signature — indexing them by version string fails (TS7053). Parse both files once at a typed boundary and use only the parsed values; the runtime guards also make a malformed file from the ingest script fail the build with a readable message:

```ts
import type { Config } from '@docusaurus/types';
import type { VersionOptions } from '@docusaurus/plugin-content-docs';
import versionsJson from './versions.json';
import syncStateJson from './sync-state.json';

type Channel = 'main' | 'prerelease' | 'stable';
interface SyncEntry {
  label: string;
  channel: Channel;
  source_ref: string | null;
  source_sha: string | null;
  synced_at: string | null;
}
interface SyncState {
  current: SyncEntry;                      // Next
  versions: Record<string, SyncEntry>;     // "2.0", "2.1", … (same keys as versions.json)
}

const CHANNELS: readonly Channel[] = ['main', 'prerelease', 'stable'];
const isRecord = (x: unknown): x is Record<string, unknown> =>
  typeof x === 'object' && x !== null && !Array.isArray(x);
const isNullableString = (x: unknown): x is string | null => x === null || typeof x === 'string';
const isSyncEntry = (x: unknown): x is SyncEntry =>
  isRecord(x) && typeof x.label === 'string' && CHANNELS.includes(x.channel as Channel) &&
  isNullableString(x.source_ref) && isNullableString(x.source_sha) && isNullableString(x.synced_at);

function parseSyncState(x: unknown): SyncState {
  if (!isRecord(x) || !isSyncEntry(x.current) || !isRecord(x.versions) || !Object.values(x.versions).every(isSyncEntry)) {
    throw new Error('website/sync-state.json is malformed — regenerate it with scripts/ingest');
  }
  return x as SyncState; // every field was just checked
}
function parseVersions(x: unknown): string[] {
  if (!Array.isArray(x) || !x.every((v): v is string => typeof v === 'string' && /^\d+\.\d+$/.test(v))) {
    throw new Error('website/versions.json must be ["X.Y", ...] newest-first');
  }
  return x;
}

const versions = parseVersions(versionsJson);
const syncState = parseSyncState(syncStateJson);
const latest = versions[0]; // string | undefined (noUncheckedIndexedAccess)

// Explicit tuple return type: without it TS infers (string | {...})[] and Object.fromEntries rejects it.
const versionOptions: Record<string, VersionOptions> = Object.fromEntries(
  versions.map((v, i): [string, VersionOptions] => [v, {
    label: syncState.versions[v]?.label ?? v,   // e.g. "2.0.1"
    path: i === 0 ? '' : v,
    banner: i === 0 ? 'none' : 'unmaintained',
  }]),
);

const config: Config = {
  title: 'HarborRAG',
  tagline: 'Open-source RAG framework',
  url: 'https://cbtw-apac.github.io',
  baseUrl: '/harborrag-doc-website/',          // change once a custom domain exists
  organizationName: 'cbtw-apac',
  projectName: 'harborrag-doc-website',
  trailingSlash: false,
  // 3.10 renamed `experimental_faster` to `faster`. `faster` implies ssgWorkerThreads,
  // which REQUIRES future.v4.removeLegacyPostBuildHeadAttribute — so v4 comes along.
  // v4 also turns on useCssCascadeLayers (helps §5 theming), siteStorageNamespacing,
  // fasterByDefault and mdx1CompatDisabledByDefault (see §3, step 6).
  future: { v4: true, faster: true },
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: { mermaid: true, hooks: { onBrokenMarkdownLinks: 'throw' } },  // top-level onBrokenMarkdownLinks is deprecated in 3.10
  themes: ['@docusaurus/theme-mermaid'],   // NOT in the classic preset — `pnpm add` it (see above)
  presets: [['classic', {
    docs: {
      path: 'docs',
      routeBasePath: 'docs',
      sidebarPath: './sidebars.ts',
      // Edit links go to the SOURCE repo, never to this one.
      editUrl: ({ docPath }: { docPath: string }) => `https://github.com/cbtw-apac/HarborRAG/edit/main/docs/${docPath}`,
      lastVersion: latest ?? 'current',
      versions: {
        current: {
          label: syncState.current.label,
          path: 'next',
          banner: syncState.current.channel === 'prerelease' ? 'unreleased' : 'none',
        },
        ...versionOptions,
      },
    },
    blog: false,
    theme: { customCss: './src/css/custom.css' },
  }]],
  themeConfig: {
    colorMode: { defaultMode: 'dark', respectPrefersColorScheme: true },
    navbar: { items: [
      { type: 'docSidebar', sidebarId: 'docs', label: 'Docs' },
      // The next three pages do not exist until the first ingest. Docusaurus link-checks
      // navbar targets and the navbar renders on every page, so under onBrokenLinks: 'throw'
      // each one fails the build. Keep them commented out until step 2.10.
      { to: '/docs/developers/architecture', label: 'Architecture' },
      { to: '/docs/users/detailed-guides/mcp-server', label: 'MCP' },
      { to: '/docs/project/changelog', label: 'Changelog' },
      { type: 'docsVersionDropdown', position: 'right' },
      { href: 'https://github.com/cbtw-apac/HarborRAG', label: 'GitHub', position: 'right' },
      { href: 'https://pypi.org/p/harborrag', label: 'PyPI', position: 'right' },
    ]},
  },
};
export default config;
```

`tsconfig.json` (the scaffold ships TypeScript 6, which rejects the scaffold's own `baseUrl` with TS5101 before type-checking anything; `@docusaurus/tsconfig` still sets it too, hence `ignoreDeprecations`). `resolveJsonModule` is not needed — TS 6 accepts the JSON imports as-is:

```json
{
  "extends": "@docusaurus/tsconfig",
  "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true, "ignoreDeprecations": "6.0" },
  "exclude": [".docusaurus", "build"]
}
```

Check: `pnpm typecheck` is clean and `pnpm start` serves an empty docs site with the landing placeholder at `http://localhost:3000/harborrag-doc-website/`.

**Routes before the first stable sync.** While `versions.json` is `[]`, `current` is the only version and it is configured with `path: 'next'`, so the docs live at `/docs/next` and **`/docs` does not exist** — a landing-page link to `/docs` fails the strict build. Once a stable snapshot exists (§7, Phase 5), `lastVersion` becomes that minor line with `path: ''` and `/docs` starts resolving. Link to the version root rather than hardcoding either, so the landing page survives that switch:

```tsx
import { useLatestVersion } from '@docusaurus/plugin-content-docs/client';
// …
const docs = useLatestVersion(undefined);   // pluginId is a required positional
<Link to={docs.path}>Read the docs</Link>   // /docs/next today, /docs after the first stable sync
```

`GlobalVersion.path` already carries `baseUrl`; `<Link>` handles that, which is what the theme's own version dropdown does.

## 3. Ingest script

`scripts/ingest` is a small uv project (`ruff`, `pytest`, `pyyaml`, `packaging`). One CLI:

```
uv run ingest.py \
  --source <path-to-HarborRAG-checkout> \
  --site   ../website \
  --channel {main|prerelease|stable} \
  --product-version 2.0.1 \
  --source-ref refs/tags/harborrag-adapters-v2.0.1 --source-sha 60609c8… \
  [--keep-minors 2] [--dry-run] [--force]
```

Behaviour by channel:

| channel | target dir | sidebar file | versions.json | sync-state.json key |
|---|---|---|---|---|
| `main` | `website/docs/` | `website/sidebars.ts` | unchanged | `current` (label "Next") |
| `prerelease` | `website/docs/` | `website/sidebars.ts` | unchanged | `current` (label "2.1.0a1 (pre-release)", channel prerelease) |
| `stable` | `website/versioned_docs/version-<X.Y>/` | `website/versioned_sidebars/version-<X.Y>-sidebars.json` | ensure `"X.Y"` present, newest-first, prune to `--keep-minors` | `versions["X.Y"]` (label "X.Y.Z") |

Pipeline inside the script (each step is a pure function with a unit test):

1. `guard.publication(source)` — deny-list regex over file names and contents of the published set (`docs/**`, four root files, `packages/*/README.md`). Start the list with the two names from HarborRAG's `check_publication.py`; keep it in `scripts/ingest/deny.txt`.
2. `collect(source)` — the published set only (mirror `website/check_docs_publish_path.py` semantics from HarborRAG: everything else is an internal note).
3. `toc.parse(source/docs/TOC.md)` → ordered sections → sidebar model; external items (LICENSE, GitHub) become `{type: 'link'}`.
4. `bridge(...)` — root files → `project/{overview,contributing,security,changelog}.md`; `packages/<name>/README.md` → `packages/<name>.md` prefixed with a facts table (version, PyPI link, description) read from that package's `pyproject.toml`.
5. `frontmatter.apply(doc)` — `title` from first H1 (H1 removed from body), `sidebar_position` from TOC order, `description` from first paragraph, `custom_edit_url` to HarborRAG `main`, `source_path`, `source_sha`.
6. `links.rewrite(doc, mapping)` — port of `markdown_links.py` rules: `../../CONTRIBUTING.md` → `/project/contributing`; `../packages/x/README.md` → `/packages/x`; `dir/README.md` → `dir`; strip `.md`; preserve `#anchors`; leave `https://` links alone. Any relative link with no target in the published set → hard error naming the source file (this is how broken source links surface).
7. `guard.branding(docs)` — port of `check_branding.py`.
8. `mdx_sanitize(doc)` — **new, because of the v4 future flags in §2.** `future.v4` turns on `mdx1CompatDisabledByDefault`, which flips `markdown.mdx1Compat` from `{comments: true, admonitions: true, headingIds: true}` to all-false, and Docusaurus 3 runs `.md` through MDX. HarborRAG's 29 markdown files have never been through an MDX pipeline, so anything MDX 1 used to paper over now fails the strict build: HTML comments (`<!-- … -->`), and any bare `{` or `<` that MDX reads as an expression or JSX tag. Strip HTML comments here — they are author notes that should not reach a public site anyway — and escape stray braces/angle brackets, naming the source file on anything ambiguous. The fallback, if a source file legitimately needs the old behaviour, is to re-enable one switch in the site config (`markdown: { mdx1Compat: { comments: true } }`) rather than to weaken the guard.
9. `write(target)` — `rm -rf` target dir, write files, sidebar JSON, then update `versions.json` / `sync-state.json`. Write is atomic per run (build in a temp dir, then swap) so a failing step never leaves a half-written snapshot.
10. Exit code 0 with "no changes" when the resulting tree is byte-identical to what is committed for the same `source_sha` (idempotency — the workflow uses this to skip the PR).

Check: `uv run pytest` green; `uv run ingest.py --source ~/HarborRAG --channel main --dry-run` prints the file plan for 29 docs + 4 root + 8 package pages and zero unresolved links.

## 4. Sidebar from `docs/TOC.md`

`TOC.md` is already the curated navigation (Getting started / User guides / Developer guides / Package reference / Project). The generator maps: `## Heading` → category; `- [Label](path.md)` → doc item (path → doc id); nested `  - [...]` → nested category or item; links outside docs → link item. It writes `sidebars.ts` (Next) as `export default { docs: [...] }` and the versioned JSON equivalent. Do not hand-edit those files; change `docs/TOC.md` in HarborRAG instead.

## 5. Landing page and the three.js hero

The prototype (`HarborRAG.html`, Claude Design export) defines: dark theme (`#0A0C0E` background, `#F2F6FA` headings, `#E8EDF2` body), "General Sans" 500/600, a hero with a three.js node/edge graph on a `<canvas data-hero-canvas>` with a CSS "poster" shown until WebGL boots and as the no-WebGL fallback, then sections "Install it, point it at a source", "Six stages, one route", "Eight packages, one basin", "Four tools your agents can call", "Run it yourself, or have it run for you", and a day/night toggle.

Implementation rules:

| Rule | How |
|---|---|
| Hero is optional, never blocking | `src/components/HeroGraph/index.tsx` wraps the canvas in `<BrowserOnly>` and `React.lazy(() => import('./Scene'))`; `Scene.tsx` imports `three` so it is code-split into its own chunk and never in the docs bundle. Poster (`Poster.tsx`, pure CSS/SVG) renders first; the scene fades in on first frame. |
| Respect users | `prefers-reduced-motion: reduce` → poster only, no RAF loop. Pause RAF when the canvas is off-screen (`IntersectionObserver`) or the tab is hidden. Cap device pixel ratio at 2. |
| Budget | `three` ≈ 150 kB gzipped; only import what the scene uses (`three/src/...` or `three` tree-shaken via ESM). Lighthouse performance ≥ 90 on the landing; the docs pages must not load `three` at all (assert in `pr-check` by grepping the docs chunk manifest). |
| Fonts | "General Sans" is a commercial family (Indian Type Foundry / Fontshare). Fontshare's licence permits web use for free in many cases but must be confirmed before self-hosting; until then use the fallback stack `system-ui, -apple-system, 'Segoe UI', Inter, sans-serif`. Put the decision in the repo README. |
| Copy | Landing copy stays in the site repo (`src/pages/index.tsx`, `src/data/landing.ts`). Capability statements must stay evidence-backed by `README.md` / `docs/getting-started/what-is-harborrag.md` in HarborRAG (same rule as today's `website/README.md`): no adoption numbers, logos or performance claims without a repo-owned source. |
| Theme | Port the prototype's tokens into `custom.css` as `--ifm-*` overrides for both `[data-theme='dark']` and light; Docusaurus's own toggle replaces the prototype's day/night button. |

Porting order: (1) static landing with poster only, (2) sections, (3) three.js scene, (4) theme polish. Ship (1)+(2) with 2.0.0 if (3) slips — the site is complete without the animation.

## 6. Workflows

### 6.1 HarborRAG side — `.github/workflows/docs-dispatch.yml` (new)

```yaml
name: Documentation dispatch
on:
  release:
    types: [published]
  push:
    branches: [main]
    paths: ["docs/**", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
            "pyproject.toml", "packages/*/README.md", "packages/*/pyproject.toml"]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  dispatch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>   # pin by SHA like the other workflows
        with: { persist-credentials: false }
      - id: meta
        run: |
          VERSION=$(python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
          # PEP 440 pre-release/dev markers (a, b, rc, alpha, beta, pre, dev) — no third-party module needed on the runner
          PRE=$(python3 -c "import re,sys;print(str(bool(re.search(r'(a|b|c|rc|alpha|beta|pre|preview|dev)\d*$', sys.argv[1]))).lower())" "$VERSION")
          if [ "$GITHUB_EVENT_NAME" = "release" ]; then
            TAG="${{ github.event.release.tag_name }}"; PKG="${TAG%-v*}"
            CHANNEL=$([ "$PRE" = "true" ] && echo prerelease || echo stable); REASON=release
          else
            TAG=""; PKG=""; CHANNEL=main; REASON=$GITHUB_EVENT_NAME
          fi
          printf 'version=%s\ntag=%s\npackage=%s\nchannel=%s\nreason=%s\n' "$VERSION" "$TAG" "$PKG" "$CHANNEL" "$REASON" >> "$GITHUB_OUTPUT"
      - name: Dispatch to harborrag-doc-website
        env: { TOKEN: ${{ secrets.DOCS_DISPATCH_TOKEN }} }
        run: |
          jq -n --arg ref "$GITHUB_REF" --arg sha "$GITHUB_SHA" \
            --arg tag "${{ steps.meta.outputs.tag }}" --arg pkg "${{ steps.meta.outputs.package }}" \
            --arg ver "${{ steps.meta.outputs.version }}" --arg ch "${{ steps.meta.outputs.channel }}" \
            --arg reason "${{ steps.meta.outputs.reason }}" \
            --arg run "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" \
            '{event_type:"harborrag-docs-sync", client_payload:{source_repo:"cbtw-apac/HarborRAG",
              ref:$ref, sha:$sha, tag:($tag|select(.!="")), package:($pkg|select(.!="")),
              product_version:$ver, channel:$ch, reason:$reason, run_url:$run}}' \
          | curl -fsS -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
              https://api.github.com/repos/cbtw-apac/harborrag-doc-website/dispatches -d @-
      - name: Notify Teams on failure
        if: failure()
        # reuse the Adaptive Card step from publish.yml with TEAMS_WEBHOOK_URL
```

`docs-auto.yml` keeps its build-only job as a smoke check for docs authors until phase 3, but its `stage-pages`/`deploy` jobs are removed at cut-over so two sites never deploy from one release.

### 6.2 Site side — `.github/workflows/sync.yml`

```yaml
name: Sync docs from HarborRAG
on:
  repository_dispatch:
    types: [harborrag-docs-sync]
  schedule:
    - cron: "17 18 * * *"        # 01:17 Asia/Saigon nightly fallback
  workflow_dispatch:
    inputs:
      ref:     { description: "HarborRAG ref (tag or main)", default: "main" }
      channel: { type: choice, options: [main, prerelease, stable], default: main }
      force:   { type: boolean, default: false }
concurrency:
  group: sync-${{ github.event.client_payload.channel || inputs.channel || 'cron' }}-${{ github.event.client_payload.product_version || inputs.ref || 'all' }}
  cancel-in-progress: false
permissions:
  contents: write
  pull-requests: write
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>                        # this repo
        with: { path: site, persist-credentials: false }
      - name: Resolve source ref            # validates payload: repo, ref exists, sha matches
        id: src
        run: |
          REF="${{ github.event.client_payload.ref || inputs.ref || 'main' }}"
          [ "${{ github.event.client_payload.source_repo || 'cbtw-apac/HarborRAG' }}" = "cbtw-apac/HarborRAG" ] || { echo "unexpected source repo"; exit 1; }
          SHA=$(git ls-remote https://github.com/cbtw-apac/HarborRAG.git "$REF" | cut -f1); [ -n "$SHA" ] || { echo "ref not found"; exit 1; }
          if [ -n "${{ github.event.client_payload.sha }}" ] && [ "$SHA" != "${{ github.event.client_payload.sha }}" ]; then echo "sha mismatch"; exit 1; fi
          echo "sha=$SHA" >> "$GITHUB_OUTPUT"
      - uses: actions/checkout@<sha>                        # HarborRAG, sparse
        with:
          repository: cbtw-apac/HarborRAG
          ref: ${{ steps.src.outputs.sha }}
          path: source
          sparse-checkout: |
            docs
            packages/*/README.md
            packages/*/pyproject.toml
            README.md
            CHANGELOG.md
            CONTRIBUTING.md
            SECURITY.md
            LICENSE
            pyproject.toml
          persist-credentials: false
      - uses: astral-sh/setup-uv@<sha>
        with: { python-version: "3.12" }
      - name: Ingest
        id: ingest
        working-directory: site/scripts/ingest
        run: |
          uv run ingest.py --source ../../../source --site ../../website \
            --channel "${{ github.event.client_payload.channel || inputs.channel }}" \
            --product-version "${{ github.event.client_payload.product_version || 'auto' }}" \
            --source-ref "${{ github.event.client_payload.ref || inputs.ref }}" \
            --source-sha "${{ steps.src.outputs.sha }}" ${{ inputs.force && '--force' || '' }}
          echo "changed=$(git -C ../../ status --porcelain | grep -q . && echo true || echo false)" >> "$GITHUB_OUTPUT"
      - name: Open / update sync PR
        if: steps.ingest.outputs.changed == 'true'
        id: pr
        uses: peter-evans/create-pull-request@<sha>
        with:
          token: ${{ secrets.DOCS_SYNC_TOKEN }}             # bot identity so pr-check runs
          path: site
          branch: sync/${{ github.event.client_payload.channel || inputs.channel }}-${{ github.event.client_payload.product_version || 'main' }}
          delete-branch: true
          commit-message: "sync: HarborRAG ${{ github.event.client_payload.ref || inputs.ref }} @ ${{ steps.src.outputs.sha }}"
          title: "[sync] ${{ github.event.client_payload.channel || inputs.channel }} ← ${{ github.event.client_payload.ref || inputs.ref }}"
          body: "Automated. Source: ${{ github.event.client_payload.run_url || 'manual/cron' }}. Content PRs belong in cbtw-apac/HarborRAG."
          labels: automation
      - if: steps.pr.outputs.pull-request-operation == 'created'
        uses: peter-evans/enable-pull-request-automerge@<sha>
        with: { token: ${{ secrets.DOCS_SYNC_TOKEN }}, pull-request-number: ${{ steps.pr.outputs.pull-request-number }}, merge-method: squash }
      - name: Approve pull request
        # Branch protection needs one approval and GitHub forbids self-approval, so this must be a
        # DIFFERENT account from the DOCS_SYNC_TOKEN owner. A second PAT avoids widening GITHUB_TOKEN
        # (which would need the org-level "Allow GitHub Actions to create and approve pull requests").
        # 'updated' is included so a refreshed PR is re-approved if stale reviews are dismissed.
        if: |
          steps.pr.outputs.pull-request-operation == 'created' ||
          steps.pr.outputs.pull-request-operation == 'updated'
        env:
          GH_TOKEN: ${{ secrets.APPROVER_PAT }}
          PR_NUMBER: ${{ steps.pr.outputs.pull-request-number }}
        run: |
          gh api --method POST "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER/reviews" -f event=APPROVE
      - name: Notify Teams on failure
        if: failure()
        # Adaptive Card with channel, ref, run URL (copy the step from HarborRAG publish.yml)
```

Why two tokens and not `GITHUB_TOKEN` (DevOps review, 15 Sep 2026): the built-in `GITHUB_TOKEN` cannot approve PRs unless "Allow GitHub Actions to create and approve pull requests" is enabled, and in an organisation that setting is gated by the org-level Actions policy. Enabling it widens what every workflow's token in that scope can do, so we keep the default and use two narrowly scoped tokens instead:

| Token | Owner | Scope | Used for |
|---|---|---|---|
| `DOCS_SYNC_TOKEN` | account A (service/bot account preferred) | fine-grained PAT, this repo only: Contents read & write, Pull requests read & write, Workflows read & write | create/refresh the sync PR (so `pr-check` runs), enable auto-merge |
| `APPROVER_PAT` | account B (a different admin or a second service account) | fine-grained PAT, this repo only: Pull requests read & write | post the `APPROVE` review |

Both accounts need write access to the repo. Fine-grained PATs expire (max 1 year) — put the expiry dates in the runbook and in the Teams reminder. If either owner leaves CBTW the sync stops until the secret is rotated; that is the reason architecture §11 keeps "service account vs. GitHub App" open. Follow-up once a dedicated bot account exists: a repository *ruleset* on `main` with the bot as a bypass actor for "require pull request review" removes the approval step and `APPROVER_PAT` entirely, while human PRs still require review.

Cron mode: when neither payload nor inputs are present, a small `versions.py discover` step lists HarborRAG tags, computes the expected `{current: main, "2.0": <newest 2.0.x tag>}` set, compares with `sync-state.json`, and loops the ingest over stale entries only.

### 6.3 Site side — `pr-check.yml` and `deploy.yml`

`pr-check.yml` (on `pull_request`): checkout → `pnpm/action-setup` (reads `packageManager`) + `setup-node` 20 with pnpm cache → `pnpm install --frozen-lockfile` → `pnpm typecheck` → `pnpm build` (strict broken-link settings make this the link check) → assert `three` is absent from docs chunks → `actions/upload-artifact` of `website/build` for preview. Required status check on `main`.

`deploy.yml` (on `push: main`, and `workflow_dispatch`): same build → `actions/configure-pages` → `upload-pages-artifact` (`website/build`) → `deploy-pages`. `concurrency: { group: pages, cancel-in-progress: false }`, `permissions: { pages: write, id-token: write }`, environment `github-pages`. Pin every action by SHA, as HarborRAG does.

## 7. Repository settings checklist

| Where | Setting |
|---|---|
| Site → Settings → Pages | Source: **GitHub Actions** |
| Site → Settings → General | Allow auto-merge ✔; Automatically delete head branches ✔ |
| Site → Branches → `main` | Require PR with 1 approval; require status `pr-check`; restrict pushes to admins + bot |
| Site → Secrets | `DOCS_SYNC_TOKEN` (account A — fine-grained PAT, this repo only: Contents, Pull requests, Workflows read & write), `APPROVER_PAT` (account B ≠ A — fine-grained PAT, this repo only: Pull requests read & write), `TEAMS_WEBHOOK_URL` |
| Site → Actions → General | Leave "Allow GitHub Actions to create and approve pull requests" **off** (default) — not needed with the two-PAT approach, and enabling it requires an org-level policy change |
| Site → Collaborators | Accounts A and B have **Write** access |
| HarborRAG → Secrets (admin) | `DOCS_DISPATCH_TOKEN` (Contents: read & write on `harborrag-doc-website` only) |
| HarborRAG → Variables | `DOCS_SITE_URL` = `https://cbtw-apac.github.io/harborrag-doc-website` at cut-over |
| Site repo files | `README.md` states the contribution rule; `CODEOWNERS` assigns generated paths to the bot and `website/src/**` to the FE owner; `dependabot.yml` for npm + github-actions weekly |

## 8. Local development loop

```makefile
# Makefile (repo root)
# $(abspath …) matters: the recipes cd into scripts/ingest first, so a relative
# HARBORRAG would otherwise resolve to scripts/HarborRAG. --site ../../website
# is correctly relative to scripts/ingest and stays as-is.
#
# On Windows, GNU Make falls back to cmd.exe when sh.exe is not on PATH, and
# every recipe here is POSIX. Install make (winget install ezwinports.make),
# put "C:\Program Files\Git\bin" on PATH, and pin the shell:
#   ifeq ($(OS),Windows_NT)
#     SHELL := sh.exe
#     .SHELLFLAGS := -c
#   endif
HARBORRAG ?= ../HarborRAG
sync-local:        ## ingest from a local HarborRAG checkout into website/docs (Next)
	cd scripts/ingest && uv run ingest.py --source $(abspath $(HARBORRAG)) --site ../../website --channel main \
	  --source-ref local --source-sha $$(git -C $(abspath $(HARBORRAG)) rev-parse HEAD)
sync-stable:       ## e.g. make sync-stable TAG=harborrag-v2.0.0
	cd scripts/ingest && uv run ingest.py --source $(abspath $(HARBORRAG)) --site ../../website --channel stable \
	  --source-ref refs/tags/$(TAG) --source-sha $$(git -C $(abspath $(HARBORRAG)) rev-parse $(TAG))
dev:               ; cd website && pnpm start
build:             ; cd website && pnpm build
check:             ; cd scripts/ingest && uv run pytest && uv run ruff check . && cd ../../website && pnpm typecheck && pnpm build
```

Typical loop for a docs author who wants to preview a HarborRAG docs change: edit in `HarborRAG/docs`, `make sync-local`, `make dev`. Nothing needs to be committed in the site repo for a preview.

## 9. Quality gates (map to Lam's §5.2)

| Gate | Where | Fails when |
|---|---|---|
| Publication guard | ingest step 1 | any deny-listed name/content in the published set |
| Unresolved relative link | ingest step 6 | a `.md` link has no target in the published set |
| Branding | ingest step 7 | ported `check_branding.py` rules |
| MDX compatibility | ingest step 8 | HTML comment or unescaped `{`/`<` survives into a synced page (MDX 1 compat is off under `future.v4`) |
| Strict build | `pr-check` | broken link/anchor, MDX compile error |
| Bundle boundary | `pr-check` | `three` appears in a non-landing chunk |
| Idempotency | `scripts/ingest/tests` | re-running ingest on the same sha yields a diff |
| Visual | manual before 2.0.0 | landing/docs at 360 px, 768 px, 1280 px; light and dark; reduced-motion |
| Lighthouse (optional) | `pr-check` via `treosh/lighthouse-ci-action` | performance < 90 or a11y < 95 on `/` and one doc page |

## 10. Cut-over checklist (with 2.0.0 stable)

1. Phase 0 done: site deploys from `main`; first manual `stable` sync from `harborrag-v2.0.0a1` visible as `2.0` (label "2.0.0a1"); `Next` from `main`.
2. `DOCS_DISPATCH_TOKEN` set in HarborRAG by an admin; `docs-dispatch.yml` merged; a docs push to `main` reaches `Next` within 15 min (record the time for Lam's test).
3. Release 2.0.0 via `release.py`; confirm one sync PR per channel, auto-merged; `2.0` snapshot relabelled "2.0.0"; `/docs/` routes to it.
4. Flip `DOCS_SITE_URL`; update `README.md`, root `pyproject.toml` `[project.urls]`, `SECURITY.md` links in HarborRAG (that push itself re-syncs `Next`).
5. Remove `stage-pages`/`deploy` jobs from `docs-auto.yml` and `docs-manual.yml`; publish a redirect `index.html` to the old Pages site once, then leave it.
6. Release notes for 2.0.0 link the new site; Teams announcement.
7. Post-2.0.0: delete `website/` and `tests/test_website_*.py` from HarborRAG; move any still-useful checks into `scripts/ingest`.

## 11. Definition of done for the 2.0.0 docs website

- Every page of HarborRAG `docs/`, the four root files and the eight package READMEs is reachable on the site under both `Next` and `2.0`, with zero broken links (strict build green).
- A stable release, a sub-package hotfix release and a docs-only push to `main` each update the site with no manual step, and the elapsed time is recorded.
- The nightly cron and manual dispatch each complete a no-op run cleanly ("no changes").
- Landing page renders with poster fallback when WebGL is disabled and under `prefers-reduced-motion`; docs pages do not download `three`.
- README of the site repo states the contribution rule; CODEOWNERS and branch protection are in place; all actions pinned by SHA.
- Runbook (architecture §9) linked from the site repo README.
