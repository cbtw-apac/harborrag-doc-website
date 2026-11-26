import Link from "@docusaurus/Link";
import type { ReactNode } from "react";

import DocumentationIcon from "@site/src/assets/icons/documentation-icon.svg";
import ModuleIcon from "@site/src/assets/icons/module-icon.svg";
import background from "@site/src/assets/images/install-background-HarborRAG.webp";
import Terminal from "@site/src/components/Terminal";
import { installCards } from "@site/src/data/home";

import styles from "./styles.module.css";

export default function Install(): ReactNode {
  return (
    <section className={styles.section}>
      <img className={styles.background} src={background} alt="" />
      <div className={styles.overlay} />

      <div className={styles.container}>
        <div className={styles.intro}>
          <h2 className={styles.title}>Quick Installation</h2>
          <p className={styles.lead}>Install the packages you need with pip</p>
        </div>

        <div className={styles.grid}>
          {installCards.map(
            ({ title, description, Icon, terminal, copyLabel, pypiUrl }) => (
              <div key={title} className={styles.card}>
                <Icon className={styles.cardIcon} aria-hidden="true" />
                <h3 className={styles.cardTitle}>{title}</h3>
                <p className={styles.cardText}>{description}</p>
                <Terminal
                  title="bash"
                  lines={terminal}
                  copyLabel={copyLabel}
                  className={styles.terminal}
                />
                <Link href={pypiUrl} className={styles.pypiButton}>
                  <ModuleIcon aria-hidden="true" />
                  View on PyPI
                </Link>
              </div>
            ),
          )}
        </div>

        <Link to="/documentation" className={styles.cta}>
          <DocumentationIcon aria-hidden="true" />
          View Full Documentation
        </Link>
      </div>
    </section>
  );
}
