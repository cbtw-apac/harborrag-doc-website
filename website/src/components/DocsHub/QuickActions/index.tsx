import type { ReactNode } from "react";
import styles from "./styles.module.css";

import background from "@site/src/assets/images/doc-background.webp";
import { QuickAction, quickActions } from "@site/src/data/docsHub";
import Link from "@docusaurus/Link";
import clsx from "clsx";

function QA({ label, href, primary, Icon }: QuickAction): ReactNode {
  return (
    <Link
      href={href}
      className={clsx(
        styles.btn,
        primary ? styles.btnPrimary : styles.btnSecondary,
      )}
    >
      <Icon aria-hidden="true" />
      {label}
    </Link>
  );
}

export default function QuickActions(): ReactNode {
  return (
    <section className={styles.section}>
      <img className={styles.bg} src={background} alt="" />
      <div className={styles.inner}>
        <h3>Quick Actions</h3>
        <div className={styles.btns}>
          {quickActions.map((action) => (
            <QA key={action.label} {...action} />
          ))}
        </div>
      </div>
    </section>
  );
}
