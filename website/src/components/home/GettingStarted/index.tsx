import Link from "@docusaurus/Link";
import useBrokenLinks from "@docusaurus/useBrokenLinks";
import type { ReactNode } from "react";

import ChevronIcon from "@site/src/assets/icons/chevron-right.svg";
import NarrowIcon from "@site/src/assets/icons/narrow-white-icon.svg";
import illustration from "@site/src/assets/images/R-HarborRAG.png";
import DocLink from "@site/src/components/DocLink";
import { gettingStartedCards } from "@site/src/data/home";
import { useMainDocPath } from "@site/src/lib/docPath";

import styles from "./styles.module.css";

export default function GettingStarted(): ReactNode {
  // The navbar links /#overview; the anchor checker only knows headings and
  // anchors registered like this one.
  useBrokenLinks().collectAnchor("overview");
  // TODO: point at the /documentation hub once it exists.
  const docsHome = useMainDocPath();
  return (
    <section className={styles.section}>
      <div className={styles.top}>
        <div className={styles.intro}>
          <h2 className={styles.title}>Getting started</h2>
          <p className={styles.description}>
            Comprehensive documentation for HarborRAG <br /> and MCP Server.
          </p>
          <Link to={docsHome} className={styles.cta}>
            Explore Now
            <NarrowIcon aria-hidden="true" />
          </Link>
        </div>
        <img
          className={styles.illustration}
          src={illustration}
          alt="Getting started illustration"
        />
      </div>

      <div id="overview" className={styles.grid}>
        {gettingStartedCards.map(({ title, description, docId, Icon }) => (
          <DocLink key={docId} docId={docId} className={styles.card}>
            <Icon className={styles.cardIcon} aria-hidden="true" />
            <div>
              <h3 className={styles.cardTitle}>{title}</h3>
              <p className={styles.cardDescription}>{description}</p>
              <p className={styles.viewDocs}>
                <ChevronIcon aria-hidden="true" />
                <span>View Documentation</span>
              </p>
            </div>
          </DocLink>
        ))}
      </div>
    </section>
  );
}
