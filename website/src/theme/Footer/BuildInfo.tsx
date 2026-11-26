import Link from "@docusaurus/Link";
import {
  useActivePluginAndVersion,
  useLatestVersion,
} from "@docusaurus/plugin-content-docs/client";
import type { ReactNode } from "react";

import { SOURCE_REPO } from "@site/src/lib/site";
import { syncState, type SyncEntry } from "@site/src/lib/syncState";

import styles from "./styles.module.css";

/** Sync entry of the docs version on screen; the latest one outside the docs. */
export function useSyncEntry(): SyncEntry {
  const active = useActivePluginAndVersion();
  const latest = useLatestVersion(undefined);
  const name = active?.activeVersion?.name ?? latest.name;
  return name === "current"
    ? syncState.current
    : (syncState.versions[name] ?? syncState.current);
}

const TAG_PREFIX = "refs/tags/";

function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split("-");
  return `${day}-${month}-${year}`; // same dd-mm-yyyy as HarborRAG
}

export default function BuildInfo(): ReactNode {
  const { label, source_ref, source_sha, synced_at } = useSyncEntry();
  const tag = source_ref?.startsWith(TAG_PREFIX)
    ? source_ref.slice(TAG_PREFIX.length)
    : null;
  return (
    <p className={styles.buildInfo}>
      {tag ? (
        <Link href={`${SOURCE_REPO}/releases/tag/${tag}`}>Version {label}</Link>
      ) : (
        `Version ${label}`
      )}
      {synced_at && ` • Synced ${formatDate(synced_at)}`}
      {source_sha && (
        <>
          {" • Commit "}
          <Link href={`${SOURCE_REPO}/commit/${source_sha}`}>
            {source_sha.slice(0, 7)}
          </Link>
        </>
      )}
    </p>
  );
}
