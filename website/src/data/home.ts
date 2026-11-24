// Landing page content, copied verbatim from HarborRAG templates/index.html.
// Content rules follow HarborRAG/website/README.md: no metrics, customer logos
// or performance claims without a source.
import type { ComponentType, SVGProps } from "react";

import BugIcon from "@site/src/assets/icons/bug-orange-icon.svg";
import CardExtendingIcon from "@site/src/assets/icons/file-conversion-icon.svg";
import CircuitBoardIcon from "@site/src/assets/icons/circuit-board-orange-icon.svg";
import DiscussionIcon from "@site/src/assets/icons/discussion-icon.svg";
import ProviderAgnosticIcon from "@site/src/assets/icons/server-icon.svg";
import SemanticSearchIcon from "@site/src/assets/icons/search-orange-icon.svg";
import FileConversionIcon from "@site/src/assets/icons/file-conversion-icon.svg";
import FilePdfIcon from "@site/src/assets/icons/file-pdf-icon.svg";
import GitHubIcon from "@site/src/assets/icons/github-orange-icon.svg";
import GridIcon from "@site/src/assets/icons/grid-icon.svg";
import InstallHarborRagIcon from "@site/src/assets/icons/module-icon.svg";
import InstallMcpServerIcon from "@site/src/assets/icons/circuit-board-icon.svg";
import LayersIcon from "@site/src/assets/icons/layers-icon.svg";
import LinkedIcon from "@site/src/assets/icons/linked-orange-icon.svg";
import ModuleIcon from "@site/src/assets/icons/module-orange-icon.svg";
import PaperPlaneIcon from "@site/src/assets/icons/paper-plane-icon.svg";
import PlugIcon from "@site/src/assets/icons/plug-orange-icon.svg";
import SearchIcon from "@site/src/assets/icons/search-orange-icon.svg";
import ServerIcon from "@site/src/assets/icons/server-icon.svg";
import type { TerminalLine } from "@site/src/components/Terminal";
import { PYPI, SOURCE_REPO } from "@site/src/lib/site";

export type Icon = ComponentType<SVGProps<SVGSVGElement>>;

export interface IconLabel {
  label: string;
  Icon: Icon;
}

export const heroFeatures: readonly IconLabel[] = [
  { label: "Multi-Project Support", Icon: GridIcon },
  { label: "Semantic Search", Icon: SearchIcon },
  { label: "File Conversion", Icon: FileConversionIcon },
  { label: "MCP Server", Icon: CircuitBoardIcon },
  { label: "Provider Agnostic", Icon: ServerIcon },
];

export const runItTerminal: readonly TerminalLine[] = [
  { kind: "comment", text: "# 1. get the repository" },
  { kind: "command", text: `git clone ${SOURCE_REPO}.git` },
  { kind: "command", text: "cd HarborRAG" },
  { kind: "blank" },
  { kind: "comment", text: "# 2. sync the workspace (Python 3.12+ and uv)" },
  { kind: "command", text: "uv sync --all-packages --extra dev" },
  { kind: "blank" },
  { kind: "comment", text: "# 3. the operator CLI is live" },
  { kind: "command", text: "uv run --package harborrag-app harborrag --help" },
  { kind: "output", text: "Usage: harborrag [OPTIONS] COMMAND [ARGS]..." },
  { kind: "output", text: "  doctor    Check Temporal runtime readiness." },
  {
    kind: "output",
    text: "  chat      Generate a response with the configured chat model.",
  },
  {
    kind: "output",
    text: "  retrieve  Search active vectors with graph context expansion.",
  },
  { kind: "output", text: "  ingest    Submit, observe, and control ingestion runs." },
];

export interface GettingStartedCard {
  title: string;
  description: string;
  docId: string;
  Icon: Icon;
}

// The template's "Test Coverage" card is dropped: Coverage is out of scope.
export const gettingStartedCards: readonly GettingStartedCard[] = [
  {
    title: "HarborRAG Core",
    description:
      "Comprehensive data ingestion toolkit supporting Git, Confluence, JIRA, and local files with intelligent file conversion.",
    docId: "packages/harborrag-core",
    Icon: ModuleIcon,
  },
  {
    title: "MCP Server",
    description:
      "Model Context Protocol server providing RAG capabilities for Cursor IDE and other Al development tools.",
    docId: "packages/harborrag-mcp-server",
    Icon: CircuitBoardIcon,
  },
  {
    title: "Multi-Project Support",
    description:
      "Manage multiple projects with a single configuration, one Qdrant server, and unified search capabilities.",
    docId: "users/configuration/config-file-reference",
    Icon: LayersIcon,
  },
  {
    title: "Extending HarborRAG",
    description:
      "Implement a real connector, parser, model, or repository using the base + mock pattern.",
    docId: "developers/extending/README",
    Icon: CardExtendingIcon,
  },
  {
    title: "Quick Start",
    description:
      "Get started with HarborRAG in minutes with our comprehensive installation and setup guide.",
    docId: "getting-started/quick-start",
    Icon: PaperPlaneIcon,
  },
];

export interface KeyFeature {
  title: string;
  description: string;
  Icon: Icon;
}

export const keyFeatures: readonly KeyFeature[] = [
  {
    title: "Multiple Data Sources",
    description: "GitHub, Confluence, Jira, SharePoint, local files",
    Icon: LinkedIcon,
  },
  {
    title: "File Conversion",
    description: "PDF, Office, Images, Audio, Archives",
    Icon: FilePdfIcon,
  },
  {
    title: "Multi-Project",
    description: "Tenant-aware workspaces and access boundaries",
    Icon: LayersIcon,
  },
  {
    title: "Semantic Search",
    description: "AI-powered document retrieval",
    Icon: SemanticSearchIcon,
  },
  {
    title: "MCP Integration",
    description: "Cursor IDE and AI tools",
    Icon: PlugIcon,
  },
  {
    title: "Provider Agnostic",
    description: "Replaceable models, stores, parsers, and transports",
    Icon: ProviderAgnosticIcon,
  },
];

export interface InstallCard {
  title: string;
  description: string;
  Icon: Icon;
  terminal: readonly TerminalLine[];
  copyLabel: string;
  pypiUrl: string;
}

export const installCards: readonly InstallCard[] = [
  {
    title: "HarborRAG",
    description:
      "Install the public meta-package and choose optional capabilities.",
    Icon: InstallHarborRagIcon,
    terminal: [{ kind: "command", text: "pip install harborrag" }],
    copyLabel: "Copy the harborrag install command",
    pypiUrl: PYPI.harborrag,
  },
  {
    title: "MCP Server",
    description:
      "Expose governed retrieval tools through the Model Context Protocol.",
    Icon: InstallMcpServerIcon,
    terminal: [{ kind: "command", text: "pip install harborrag-mcp-server" }],
    copyLabel: "Copy the harborrag-mcp-server install command",
    pypiUrl: PYPI.mcpServer,
  },
];

export interface CommunityLink {
  title: string;
  description: string;
  href: string;
  Icon: Icon;
}

export const communityLinks: readonly CommunityLink[] = [
  {
    title: "GitHub Repository",
    description: "Source code, issues, and discussions",
    href: SOURCE_REPO,
    Icon: GitHubIcon,
  },
  {
    title: "Report Issues",
    description: "Bug reports and feature requests",
    href: `${SOURCE_REPO}/issues`,
    Icon: BugIcon,
  },
  {
    title: "Discussions",
    description: "Community Q&A and ideas",
    href: `${SOURCE_REPO}/discussions`,
    Icon: DiscussionIcon,
  },
];
