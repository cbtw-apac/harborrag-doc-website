import Link from "@docusaurus/Link";
import clsx from "clsx";
import type { ReactNode } from "react";

import BookIcon from "@site/src/assets/icons/book-open-icon.svg";
import GitHubIcon from "@site/src/assets/icons/github-icon.svg";
import background from "@site/src/assets/images/home-background.webp";
import { heroFeatures } from "@site/src/data/home";
import { SOURCE_REPO } from "@site/src/lib/site";

import styles from "./styles.module.css";

export default function Hero(): ReactNode {
  return (
    <section className={styles.section}>
      <img className={styles.background} src={background} alt="" />
      <div className={styles.content}>
        <h1 className={styles.title}>
          Harbor<span className={styles.accent}>RAG</span>
        </h1>
        <p className={styles.description}>
          A modular, provider-agnostic RAG framework for engineering knowledge
        </p>
        <p className={styles.claim}>
          Every answer is resolved against the authoritative document version,
          so a superseded version can never be cited &mdash; even mid-reindex.
        </p>

        <div className={styles.features}>
          {heroFeatures.map(({ label, Icon }) => (
            <p key={label} className={styles.feature}>
              <Icon className={styles.featureIcon} aria-hidden="true" />
              {label}
            </p>
          ))}
        </div>

        <div className={styles.cta}>
          <Link to="/documentation" className={clsx(styles.button, styles.buttonLight)}>
            <BookIcon className={styles.buttonIcon} aria-hidden="true" />
            Get Started
          </Link>
          <Link
            href={SOURCE_REPO}
            className={clsx(styles.button, styles.buttonOutline)}
          >
            <GitHubIcon className={styles.buttonIcon} aria-hidden="true" />
            View on GitHub
          </Link>
        </div>
      </div>
    </section>
  );
}
