import Layout from "@theme/Layout";
import type { ReactNode } from "react";

import Community from "@site/src/components/home/Community";
import GettingStarted from "@site/src/components/home/GettingStarted";
import Hero from "@site/src/components/home/Hero";
import Install from "@site/src/components/home/Install";
import KeyFeatures from "@site/src/components/home/KeyFeatures";
import RunIt from "@site/src/components/home/RunIt";

export default function Home(): ReactNode {
  return (
    <Layout description="A modular, provider-agnostic RAG framework for engineering knowledge">
      <main>
        <Hero />
        <RunIt />
        <GettingStarted />
        <KeyFeatures />
        <Install />
        <Community />
      </main>
    </Layout>
  );
}
