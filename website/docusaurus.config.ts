import type { VersionOptions } from "@docusaurus/plugin-content-docs";
import type * as Preset from "@docusaurus/preset-classic";
import type { Config } from "@docusaurus/types";

import { PYPI, SOURCE_REPO } from "./src/lib/site";
import { versions, syncState } from "./src/lib/syncState";
import prismTheme from "./src/lib/prismTheme";
import rehypeTableScroll from "./src/lib/rehypeTableScroll";

const latest = versions[0]; // string | undefined until the first stable sync

// Explicit tuple return type: without it TS infers (string | {...})[] and Object.fromEntries rejects it.
const versionOptions: Record<string, VersionOptions> = Object.fromEntries(
  versions.map((v, i): [string, VersionOptions] => [
    v,
    {
      label: syncState.versions[v]?.label ?? v,
      path: i === 0 ? "" : v, // newest stable owns /docs/, older ones /docs/2.0/
      banner: i === 0 ? "none" : "unmaintained",
    },
  ]),
);

// ---------------------------------------------------------------------------
// Site config
// ---------------------------------------------------------------------------

const config: Config = {
  title: "HarborRAG",
  tagline: "Open-source RAG framework",
  favicon: "img/favicon.ico",
  headTags: [
    {
      tagName: "link",
      attributes: { rel: "preconnect", href: "https://fonts.googleapis.com" },
    },
    {
      tagName: "link",
      attributes: {
        rel: "preconnect",
        href: "https://fonts.gstatic.com",
        crossorigin: "anonymous",
      },
    },
  ],
  stylesheets: [
    "https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Noto+Sans:wght@400;600;700&family=Source+Code+Pro&display=swap",
  ],

  url: "https://cbtw-apac.github.io",
  baseUrl: "/harborrag-doc-website/", // change once we map "harborrag.net"
  organizationName: "cbtw-apac",
  projectName: "harborrag-doc-website",
  trailingSlash: false,
  future: { v4: true, faster: true },

  onBrokenLinks: "throw",
  onBrokenAnchors: "throw",
  markdown: {
    mermaid: true,
    hooks: { onBrokenMarkdownLinks: "throw" }, // top-level option is deprecated in 3.10
  },
  themes: ["@docusaurus/theme-mermaid"],

  i18n: { defaultLocale: "en", locales: ["en"] },

  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "docs",
          sidebarPath: "./sidebars.ts",
          // Edit links go to the source of truth (HarborRAG docs folder), never to this repo.
          editUrl: ({ docPath }: { docPath: string }) =>
            `${SOURCE_REPO}/edit/main/docs/${docPath}`,
          lastVersion: latest ?? "current",
          versions: {
            current: {
              label: syncState.current.label,
              path: "next",
              banner:
                syncState.current.channel === "prerelease"
                  ? "unreleased"
                  : "none",
            },
            ...versionOptions,
          },
          sidebarCollapsible: false, // HarborRAG's rail is a flat, always-open list
          breadcrumbs: false, // HarborRAG doc pages have none
          rehypePlugins: [rehypeTableScroll],
        },
        blog: false,
        theme: { customCss: "./src/css/custom.css" },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: "img/social-card.png",
    colorMode: {
      defaultMode: "light",
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      logo: { alt: "HarborRAG", src: "img/logo.svg", height: 60 },
      items: [
        // TODO: switch to { to: "/#overview" } once the landing registers the anchor.
        {
          type: "doc",
          docId: "project/overview",
          label: "Overview",
          position: "right",
        },
        {
          type: "docSidebar",
          sidebarId: "docs",
          label: "Documentation",
          position: "right",
        },
        { type: "docsVersionDropdown", position: "right" },
        {
          href: SOURCE_REPO,
          label: "GitHub",
          position: "right",
          className: "header-github-link",
        },
        {
          type: "dropdown",
          label: "PyPI",
          position: "right",
          className: "header-pypi-link",
          items: [
            { label: "HarborRAG", href: PYPI.harborrag },
            { label: "MCP Server", href: PYPI.mcpServer },
            { label: "Core Library", href: PYPI.core },
          ],
        },
      ],
    },
    footer: {
      style: "dark",
      copyright: `© ${new Date().getFullYear()} CBTW.`,
    },
    prism: {
      theme: prismTheme,
      additionalLanguages: ["bash", "json", "toml", "yaml", "python"],
    },
  } satisfies Preset.ThemeConfig,
  clientModules: ["./src/clientModules/numberedSteps.ts"],
};

export default config;
