// ---------------------------------------------------------------------------
// Sync state — written by scripts/ingest, read here.
// Both JSON files are parsed once at this boundary; nothing below touches the
// raw imports.
// ---------------------------------------------------------------------------

import syncStateJson from "../../sync-state.json";
import versionsJson from "../../versions.json";

export type Channel = "main" | "prerelease" | "stable";
export interface SyncEntry {
  label: string;
  channel: Channel;
  source_ref: string | null;
  source_sha: string | null;
  synced_at: string | null;
}
export interface SyncState {
  current: SyncEntry; // Docusaurus "current" = HarborRAG main / latest pre-release
  versions: Record<string, SyncEntry>; // keyed exactly like versions.json ("2.0.0", "2.0.1", …)
}

const CHANNELS: readonly Channel[] = ["main", "prerelease", "stable"];

const isRecord = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);
const isNullableString = (x: unknown): x is string | null =>
  x === null || typeof x === "string";
const isChannel = (x: unknown): x is Channel =>
  typeof x === "string" && (CHANNELS as readonly string[]).includes(x);
const isSyncEntry = (x: unknown): x is SyncEntry =>
  isRecord(x) &&
  typeof x.label === "string" &&
  isChannel(x.channel) &&
  isNullableString(x.source_ref) &&
  isNullableString(x.source_sha) &&
  isNullableString(x.synced_at);

function parseSyncState(x: unknown): SyncState {
  if (!isRecord(x)) {
    throw new Error("website/sync-state.json must be an object");
  }
  const { current, versions } = x;
  if (!isSyncEntry(current)) {
    throw new Error(
      'website/sync-state.json: "current" is not a valid sync entry'
    );
  }
  if (!isRecord(versions)) {
    throw new Error(
      'website/sync-state.json: "versions" must be an object keyed by "X.Y"'
    );
  }
  const parsed: Record<string, SyncEntry> = {};
  for (const [key, entry] of Object.entries(versions)) {
    if (!isSyncEntry(entry)) {
      throw new Error(
        `website/sync-state.json: versions["${key}"] is not a valid sync entry`
      );
    }
    parsed[key] = entry;
  }
  return { current, versions: parsed };
}

function parseVersions(x: unknown): string[] {
  const isMinorLine = (v: unknown): v is string =>
    typeof v === "string" && /^\d+\.\d+$/.test(v);
  if (!Array.isArray(x) || !x.every(isMinorLine)) {
    throw new Error('website/versions.json must be ["X.Y", ...] newest-first');
  }
  return x;
}

export const versions = parseVersions(versionsJson);
export const syncState = parseSyncState(syncStateJson);