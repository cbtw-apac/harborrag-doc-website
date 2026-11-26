import type { ReactNode } from "react";

import Artwork from "@site/src/assets/icons/key-feature-background-HarborRAG.svg";
import { keyFeatures } from "@site/src/data/home";

import styles from "./styles.module.css";

export default function KeyFeatures(): ReactNode {
  return (
    <>
      <div className={styles.divider} aria-hidden="true" />
      <section className={styles.section}>
        <div className={styles.container}>
          <div className={styles.intro}>
            <h2 className={styles.title}>Key Features</h2>
            <p className={styles.description}>
              Connect engineering systems, process complex documents, and serve
              governed vector and graph retrieval through independently
              replaceable components.
            </p>
          </div>
          <div className={styles.artwork}>
            <Artwork role="img" aria-label="Feature showcase artwork" />
          </div>

          <div className={styles.grid}>
            {keyFeatures.map(({ title, description, Icon }) => (
              <div key={title} className={styles.item}>
                <Icon className={styles.icon} aria-hidden="true" />
                <h3 className={styles.itemTitle}>{title}</h3>
                <p className={styles.itemText}>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
