import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import type { VersionOptions } from '@docusaurus/plugin-content-docs';
import { themes as prismThemes } from 'prism-react-renderer';

import versionsJson from './versions.json';
import syncStateJson from './sync-state.json';

// ---------------------------------------------------------------------------
// Sync state — written by scripts/ingest, read here.
// Both JSON files are parsed once at this boundary; nothing below touches the
// raw imports.
// ---------------------------------------------------------------------------

type Channel = 'main' | 'prerelease' | 'stable';

interface SyncEntry {
  label: string;
  channel: Channel;
  source_ref: string | null;
  source_sha: string | null;
  synced_at: string | null;      
}

interface SyncState {
  current: SyncEntry;                    // Docusaurus "current" = HarborRAG main / latest pre-release
  versions: Record<string, SyncEntry>;   // keyed exactly like versions.json ("2.0.0", "2.0.1", …)
}

const CHANNELS: readonly Channel[] = ['main', 'prerelease', 'stable'];

const isRecord = (x: unknown): x is Record<string, unknown> =>
  typeof x === 'object' && x !== null && !Array.isArray(x);
const isNullableString = (x: unknown): x is string | null =>
  x === null || typeof x === 'string';
const isChannel = (x: unknown): x is Channel =>
  typeof x === 'string' && (CHANNELS as readonly string[]).includes(x);
const isSyncEntry = (x: unknown): x is SyncEntry =>
  isRecord(x) &&
  typeof x.label === 'string' &&
  isChannel(x.channel) &&
  isNullableString(x.source_ref) &&
  isNullableString(x.source_sha) &&
  isNullableString(x.synced_at);

function parseSyncState(x: unknown): SyncState {
  if (!isRecord(x)) {
    throw new Error('website/sync-state.json must be an object');
  }
  const { current, versions } = x;
  if (!isSyncEntry(current)) {
    throw new Error('website/sync-state.json: "current" is not a valid sync entry');
  }
  if (!isRecord(versions)) {
    throw new Error('website/sync-state.json: "versions" must be an object keyed by "X.Y"');
  }
  const parsed: Record<string, SyncEntry> = {};
  for (const [key, entry] of Object.entries(versions)) {
    if (!isSyncEntry(entry)) {
      throw new Error(`website/sync-state.json: versions["${key}"] is not a valid sync entry`);
    }
    parsed[key] = entry;
  }
  return { current, versions: parsed };
}

function parseVersions(x: unknown): string[] {
  const isMinorLine = (v: unknown): v is string => typeof v === 'string' && /^\d+\.\d+$/.test(v);
  if (!Array.isArray(x) || !x.every(isMinorLine)) {
    throw new Error('website/versions.json must be ["X.Y", ...] newest-first');
  }
  return x;
}

const versions = parseVersions(versionsJson);
const syncState = parseSyncState(syncStateJson);
const latest = versions[0]; // string | undefined until the first stable sync

// Explicit tuple return type: without it TS infers (string | {...})[] and Object.fromEntries rejects it.
const versionOptions: Record<string, VersionOptions> = Object.fromEntries(
  versions.map((v, i): [string, VersionOptions] => [
    v,
    {
      label: syncState.versions[v]?.label ?? v,
      path: i === 0 ? '' : v,                    // newest stable owns /docs/, older ones /docs/2.0/
      banner: i === 0 ? 'none' : 'unmaintained',
    },
  ]),
);

// ---------------------------------------------------------------------------
// Site config
// ---------------------------------------------------------------------------

const SOURCE_REPO = 'https://github.com/cbtw-apac/HarborRAG';

const config: Config = {
  title: 'HarborRAG',
  tagline: 'Open-source RAG framework',
  favicon: 'img/favicon.ico',

  url: 'https://cbtw-apac.github.io',
  baseUrl: '/harborrag-doc-website/', // change once we map "harborrag.net"
  organizationName: 'cbtw-apac',
  projectName: 'harborrag-doc-website',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: {
    mermaid: true,
    hooks: { onBrokenMarkdownLinks: 'throw' }, // top-level option is deprecated in 3.10
  },
  themes: ['@docusaurus/theme-mermaid'],

  i18n: { defaultLocale: 'en', locales: ['en'] },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          // Edit links go to the source of truth (HarborRAG docs folder), never to this repo.
          editUrl: ({ docPath }: { docPath: string }) => `${SOURCE_REPO}/edit/main/docs/${docPath}`,
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
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/harborrag-social-card.png',
    colorMode: { defaultMode: 'dark', respectPrefersColorScheme: true },
    navbar: {
      title: 'HarborRAG',
      logo: { alt: 'HarborRAG', src: 'img/logo.svg' },
      items: [
        { type: 'docSidebar', sidebarId: 'docs', label: 'Docs', position: 'left' },
        { to: '/docs/developers/architecture', label: 'Architecture', position: 'left' },
        { to: '/docs/users/detailed-guides/mcp-server', label: 'MCP', position: 'left' },
        { to: '/docs/project/changelog', label: 'Changelog', position: 'left' },
        { type: 'docsVersionDropdown', position: 'right' },
        { href: SOURCE_REPO, label: 'GitHub', position: 'right' },
        { href: 'https://pypi.org/p/harborrag', label: 'PyPI', position: 'right' },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `© ${new Date().getFullYear()} CBTW.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'toml', 'yaml', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;