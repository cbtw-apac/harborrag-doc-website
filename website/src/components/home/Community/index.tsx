import Link from "@docusaurus/Link";
import type { ReactNode } from "react";

import StartIcon from "@site/src/assets/icons/check-square-icon.svg";
import HeartIcon from "@site/src/assets/icons/heart-icon.svg";
import NarrowIcon from "@site/src/assets/icons/narrow-white-icon.svg";
import WaveIcon from "@site/src/assets/icons/wave-icon.svg";
import background from "@site/src/assets/images/community-background.webp";
import { communityLinks } from "@site/src/data/home";
import { SOURCE_REPO } from "@site/src/lib/site";

import styles from "./styles.module.css";

export default function Community(): ReactNode {
  return (
    <section className={styles.section}>
      <img className={styles.background} src={background} alt="" />
      <div className={styles.overlay} />

      <div className={styles.container}>
        <h2 className={styles.title}>Join The Community</h2>
        <p className={styles.subtitle}>
          Help us build open RAG infrastructure for engineering knowledge
        </p>
        <p className={styles.description}>
          Join our community of developers! Whether you're fixing bugs, adding
          features, or improving documentation, every contribution makes a
          difference.
        </p>

        <div className={styles.grid}>
          <div className={styles.cardLight}>
            <div className={styles.cardLightContent}>
              <HeartIcon className={styles.heartIcon} aria-hidden="true" />
              <h3 className={styles.cardLightTitle}>Contribute to HarborRAG</h3>
              <p className={styles.cardCopy}>
                Join our community of developers! Whether you're fixing bugs,
                adding features, or improving documentation, every contribution
                makes a difference.
              </p>
              <p className={styles.cardTags}>
                Code, Documentation, Bug Reports, Ideas
              </p>
            </div>
            <Link href={SOURCE_REPO} className={styles.startButton}>
              <StartIcon aria-hidden="true" />
              Start Contributing
            </Link>
          </div>

          <div className={styles.cardDark}>
            <div className={styles.connectHeader}>
              <WaveIcon className={styles.connectIcon} aria-hidden="true" />
              <div>
                <h3 className={styles.connectTitle}>Connect with Us</h3>
                <p className={styles.connectText}>
                  Connect with us to make things better
                </p>
              </div>
            </div>
            <div className={styles.links}>
              {communityLinks.map(({ title, description, href, Icon }) => (
                <Link key={href} href={href} className={styles.linkItem}>
                  <span className={styles.linkLeft}>
                    <Icon className={styles.linkIcon} aria-hidden="true" />
                    <span>
                      <span className={styles.linkTitle}>{title}</span>
                      <span className={styles.linkDescription}>
                        {description}
                      </span>
                    </span>
                  </span>
                  <NarrowIcon
                    className={styles.linkArrow}
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
