import type { ComponentType, SVGProps } from "react";

import ChangelogIcon from "@site/src/assets/icons/changelog-icon.svg";
import ModuleIcon from "@site/src/assets/icons/module-icon.svg";
import DocumentationIcon from "@site/src/assets/icons/documentation-icon.svg";
import CpuIcon from "@site/src/assets/icons/cpu-icon.svg";
import McpServerIcon from "@site/src/assets/icons/circuit-board-icon.svg";
import HarborragIcon from "@site/src/assets/icons/arrow-reload-icon.svg";
import HierarchyIcon from "@site/src/assets/icons/hierarchy-icon.svg";
import FolderIcon from "@site/src/assets/icons/folder-icon.svg";
import MagicWandIcon from "@site/src/assets/icons/magic-wand-icon.svg";
import FileIcon from "@site/src/assets/icons/file-icon.svg";
import CliIcon from "@site/src/assets/icons/cli-icon.svg";
import SearchIcon from "@site/src/assets/icons/search-icon.svg";
import UsersIcon from "@site/src/assets/icons/users-icon.svg";
import CheckIcon from "@site/src/assets/icons/check-icon.svg";
import CloudDeploymentIcon from "@site/src/assets/icons/cloud-deployment-icon.svg";
import GitHubIcon from "@site/src/assets/icons/github-icon.svg";

import { PYPI, SOURCE_REPO } from "@site/src/lib/site";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;
export type TagTone = "blue" | "cyan" | "green" | "gray" | "black";

export interface HubItem {
  label: string;
  docId: string;
  tag: string;
  tone: TagTone;
  Icon: Icon;
}
export interface HubCard {
  title: string;
  Icon: Icon;
  items: readonly HubItem[];
}

export const hubCards: readonly HubCard[] = [
  {
    title: "Getting Started",
    Icon: ModuleIcon,
    items: [
      {
        label: "Main README",
        docId: "project/overview",
        tag: "Essential",
        tone: "blue",
        Icon: DocumentationIcon,
      },
      {
        label: "Core Library",
        docId: "packages/harborrag-core",
        tag: "Core",
        tone: "cyan",
        Icon: CpuIcon,
      },
      {
        label: "MCP Server",
        docId: "packages/harborrag-mcp-server",
        tag: "Integration",
        tone: "cyan",
        Icon: McpServerIcon,
      },
      {
        label: "HarborRAG",
        docId: "packages/harborrag",
        tag: "CLI",
        tone: "cyan",
        Icon: HarborragIcon,
      },
      {
        label: "Changelog",
        docId: "project/changelog",
        tag: "Updates",
        tone: "gray",
        Icon: ChangelogIcon,
      },
    ],
  },
  {
    title: "Workspace Mode",
    Icon: HierarchyIcon,
    items: [
      {
        label: "Workspace Mode",
        docId: "users/configuration/workspace-mode",
        tag: "Configuration",
        tone: "green",
        Icon: FolderIcon,
      },
    ],
  },
  {
    title: "Features & Guides",
    Icon: HierarchyIcon,
    items: [
      {
        label: "Features Overview",
        docId: "getting-started/what-is-harborrag",
        tag: "Overview",
        tone: "cyan",
        Icon: MagicWandIcon,
      },
      {
        label: "Extending Guide",
        docId: "developers/extending/README",
        tag: "Guide",
        tone: "cyan",
        Icon: FileIcon,
      },
      {
        label: "Python SDK",
        docId: "users/python-sdk/README",
        tag: "SDK",
        tone: "cyan",
        Icon: CliIcon,
      },
      {
        label: "CLI Reference",
        docId: "users/cli-reference/README",
        tag: "CLI",
        tone: "cyan",
        Icon: CliIcon,
      },
      {
        label: "Troubleshooting",
        docId: "users/troubleshooting/README",
        tag: "Guides",
        tone: "cyan",
        Icon: HierarchyIcon,
      },
    ],
  },
  {
    title: "MCP Tools",
    Icon: McpServerIcon,
    items: [
      {
        label: "MCP Mock Tools",
        docId: "users/detailed-guides/mcp-server/README",
        tag: "Reference",
        tone: "gray",
        Icon: SearchIcon,
      },
      {
        label: "Setup & Integration",
        docId: "users/detailed-guides/mcp-server/setup-and-integration",
        tag: "Guide",
        tone: "gray",
        Icon: HierarchyIcon,
      },
    ],
  },
  {
    title: "Development",
    Icon: CliIcon,
    items: [
      {
        label: "Contributing",
        docId: "project/contributing",
        tag: "Community",
        tone: "black",
        Icon: UsersIcon,
      },
      {
        label: "Testing Guide",
        docId: "developers/testing/README",
        tag: "QA",
        tone: "black",
        Icon: CheckIcon,
      },
      {
        label: "Architecture Overview",
        docId: "developers/architecture/README",
        tag: "Design",
        tone: "black",
        Icon: HierarchyIcon,
      },
      {
        label: "Deployment Guide",
        docId: "developers/deployment/README",
        tag: "Guide",
        tone: "black",
        Icon: CloudDeploymentIcon,
      },
    ],
  },
];

export interface QuickAction {
  label: string;
  href: string;
  primary?: boolean;
  Icon: Icon;
}

export const quickActions: readonly QuickAction[] = [
  {
    label: "GitHub Repository",
    href: SOURCE_REPO,
    primary: true,
    Icon: GitHubIcon,
  },
  { label: "HarborRAG PyPI", href: PYPI.harborrag, Icon: ModuleIcon },
  { label: "MCP Server PyPI", href: PYPI.mcpServer, Icon: CliIcon },
];
