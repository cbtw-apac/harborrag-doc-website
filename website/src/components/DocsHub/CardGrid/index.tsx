import Link from "@docusaurus/Link";
import clsx from "clsx";
import type { ReactNode } from "react";

import { hubCards, type HubCard, type HubItem } from "@site/src/data/docsHub";
import { useDocPath } from "@site/src/lib/docPath";

import styles from "./styles.module.css";

function Item({ label, docId, tag, tone, Icon }: HubItem): ReactNode {
  const to = useDocPath(docId);
  if (to === undefined) return null; // not in the reader's version
  return (
    <li>
      <Link to={to}>
        <span className={styles.itemLeft}>
          <Icon aria-hidden="true" />
          {label}
        </span>
        <span className={clsx(styles.tag, styles[`tag-${tone}`])}>{tag}</span>
      </Link>
    </li>
  );
}

function Card({ title, Icon, items }: HubCard): ReactNode {
  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardIcon}>
          <Icon aria-hidden="true" />
        </div>
        <h2>{title}</h2>
      </div>
      <ul className={styles.itemList}>
        {items.map((item) => (
          <Item key={item.docId} {...item} />
        ))}
      </ul>
    </article>
  );
}

export default function CardGrid(): ReactNode {
  return (
    <section className={styles.section}>
      <div className={styles.grid}>
        {hubCards.map((card) => (
          <Card key={card.title} {...card} />
        ))}
      </div>
    </section>
  );
}
