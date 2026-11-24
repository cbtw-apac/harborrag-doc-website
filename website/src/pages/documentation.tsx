import Layout from "@theme/Layout";
import type { ReactNode } from "react";

import CardGrid from "@site/src/components/DocsHub/CardGrid";
import Hero from "@site/src/components/DocsHub/Hero";
import QuickActions from "@site/src/components/DocsHub/QuickActions";

export default function Documentation(): ReactNode {
  return (
    <Layout title="Documentation" description="Comprehensive documentation for HarborRAG and MCP Server">
      <main>
        <Hero />
        <CardGrid />
        <QuickActions />
      </main>
    </Layout>
  );
}