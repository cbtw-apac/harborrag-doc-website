import Link from "@docusaurus/Link";
import type { ReactNode } from "react";

import Terminal from "@site/src/components/Terminal";
import { runItTerminal } from "@site/src/data/home";
import { useDocPath } from "@site/src/lib/docPath";

import styles from "./styles.module.css";

const UV_DOCS = "https://docs.astral.sh/uv/";

/**
 * " <link>." at the end of a note. Unlike <DocLink>, it also drops the full
 * stop when the reader's version lacks the page, so no stray "." is left behind.
 */
function TrailingDocLink({
  docId,
  children,
}: {
  docId: string;
  children: ReactNode;
}): ReactNode {
  const to = useDocPath(docId);
  return to === undefined ? null : (
    <>
      {" "}
      <Link to={to}>{children}</Link>.
    </>
  );
}

export default function RunIt(): ReactNode {
  return (
    <section className={styles.section} id="run-it">
      <div className={styles.head}>
        <h2 className={styles.title}>Run it without any services</h2>
        <p className={styles.lead}>
          No credentials, no Docker, and no databases. Clone the repository,
          sync the workspace, and the operator CLI answers in three commands.
        </p>
      </div>

      <div className={styles.grid}>
        <Terminal
          title="bash — harborrag"
          lines={runItTerminal}
          copyLabel="Copy these commands"
        />

        <aside className={styles.notes}>
          <div>
            <p className={styles.noteTitle}>What you need</p>
            <p className={styles.noteText}>
              Python 3.12 or newer and <Link href={UV_DOCS}>uv</Link>. The sync
              resolves the full development dependency set and needs roughly
              520&nbsp;MB of disk.
            </p>
          </div>
          <div>
            <p className={styles.noteTitle}>Parse a document next</p>
            <p className={styles.noteText}>
              A short Python snippet runs the real parser registry against a
              local file, still with nothing else running.
              {/* HarborRAG links #run-it-without-any-services; the synced docs have no such anchor. */}
              <TrailingDocLink docId="project/overview">See the snippet</TrailingDocLink>
            </p>
          </div>
          <div>
            <p className={styles.noteTitle}>Then the full stack</p>
            <p className={styles.noteText}>
              Retrieval, chat, and durable ingestion need PostgreSQL, object
              storage, Qdrant, FalkorDB, Redis, and Temporal.
              <TrailingDocLink docId="developers/deployment/README">
                Read the deployment guide
              </TrailingDocLink>
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}
