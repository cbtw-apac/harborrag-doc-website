import {
  useDocsPreferredVersion,
  useLatestVersion,
} from "@docusaurus/plugin-content-docs/client";
import type { GlobalVersion } from "@docusaurus/plugin-content-docs/client";

// The version the reader last picked in the dropdown, else the latest one.
// During the build there is no preference, so links are checked against latest.
function useReaderVersion(): GlobalVersion {
  const latest = useLatestVersion(undefined);
  const { preferredVersion } = useDocsPreferredVersion(undefined);
  return preferredVersion ?? latest;
}

/**
 * Route of `docId` in the reader's version, or undefined when that version
 * does not have the page. A doc id missing from the latest version is a typo
 * or a removed page, so it fails the build like any other broken link.
 */
export function useDocPath(docId: string): string | undefined {
  const latest = useLatestVersion(undefined);
  const version = useReaderVersion();
  const path = version.docs.find((doc) => doc.id === docId)?.path;
  if (path === undefined && version.name === latest.name) {
    throw new Error(`No doc "${docId}" in docs version "${latest.name}"`);
  }
  return path;
}
