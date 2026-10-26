import Link from "@docusaurus/Link";
import { useLatestVersion } from "@docusaurus/plugin-content-docs/client";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import type { ReactNode } from "react";

export default function Home(): ReactNode {
  const { siteConfig } = useDocusaurusContext();
  const docs = useLatestVersion(undefined); // pluginId is a required positional
  // docs.path has no page of its own once the ingest owns website/docs/; link the
  // version's main doc (first doc of the sidebar) instead.
  const mainDoc = docs.docs.find((d) => d.id === docs.mainDocId)!;
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <main style={{ padding: "6rem 1rem", textAlign: "center" }}>
        <h1>{siteConfig.title}</h1>
        <p>{siteConfig.tagline}</p>
        <Link className="button button--primary button--lg" to={mainDoc.path}>
          Read the docs
        </Link>
      </main>
    </Layout>
  );
}
