import type { ComponentType, SVGProps } from "react";

import CoreIcon from "@site/src/assets/icons/db-icon.svg";
import DocumentationIcon from "@site/src/assets/icons/documentation-icon.svg";
import GitHubIcon from "@site/src/assets/icons/github-icon.svg";
import McpServerIcon from "@site/src/assets/icons/circuit-board-icon.svg";
import ModuleIcon from "@site/src/assets/icons/module-icon.svg";

import { PYPI, SOURCE_REPO } from "@site/src/lib/site";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

export interface FooterLink {
  label: string;
  href: string;
  Icon: Icon;
}

// The "Give feedback" link is built per page in the Footer component, so it is
// not listed here; it renders right after these.
export const quickLinks: readonly FooterLink[] = [
  { label: "Documentation", href: "/documentation", Icon: DocumentationIcon },
];

export const packageLinks: readonly FooterLink[] = [
  { label: "GitHub Repository", href: SOURCE_REPO, Icon: GitHubIcon },
  { label: "HarborRAG PyPI", href: PYPI.harborrag, Icon: ModuleIcon },
  { label: "MCP Server PyPI", href: PYPI.mcpServer, Icon: McpServerIcon },
  { label: "Core Library PyPI", href: PYPI.core, Icon: CoreIcon },
];
