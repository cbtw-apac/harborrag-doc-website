import clsx from "clsx";
import { Fragment, useEffect, useState } from "react";
import type { ReactNode } from "react";

import CopyIcon from "@site/src/assets/icons/copy-icon.svg";

import styles from "./styles.module.css";

export type TerminalLine =
  | { kind: "comment"; text: string }
  | { kind: "command"; text: string }
  | { kind: "output"; text: string }
  | { kind: "blank" };

interface Props {
  title: string;
  lines: readonly TerminalLine[];
  copyLabel: string; // aria-label of the copy button
  className?: string;
}

type CopyState = "idle" | "copied" | "failed";
const COPY_TEXT: Record<CopyState, string> = {
  idle: "Copy",
  copied: "Copied",
  failed: "Press Ctrl+C",
};

function renderLine(line: TerminalLine): ReactNode {
  switch (line.kind) {
    case "comment":
      return <span className={styles.comment}>{line.text}</span>;
    case "command":
      return (
        <>
          <span className={styles.prompt}>$ </span>
          {line.text}
        </>
      );
    case "output":
      return <span className={styles.output}>{line.text}</span>;
    case "blank":
      return null;
  }
}

/** Terminal window with a copy button; shared by the run-it band and the install cards. */
export default function Terminal({
  title,
  lines,
  copyLabel,
  className,
}: Props): ReactNode {
  const [copyState, setCopyState] = useState<CopyState>("idle");

  useEffect(() => {
    if (copyState === "idle") return;
    const timer = window.setTimeout(() => setCopyState("idle"), 1600);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  // Only the commands are copied, never the prompt, comments or sample output.
  const commands = lines
    .flatMap((l) => (l.kind === "command" ? [l.text] : []))
    .join("\n");

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(commands);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <div className={clsx(styles.terminal, className)}>
      <div className={styles.bar}>
        <span className={styles.dots} aria-hidden="true">
          <i className={styles.dotRed} />
          <i className={styles.dotYellow} />
          <i className={styles.dotGreen} />
        </span>
        <span className={styles.title}>{title}</span>
        <button
          type="button"
          className={styles.copy}
          aria-label={copyLabel}
          onClick={copy}
        >
          <CopyIcon aria-hidden="true" />
          <span>{COPY_TEXT[copyState]}</span>
        </button>
      </div>
      {/* Newlines go between lines, not after the last, so no empty row trails the body. */}
      <pre className={styles.body}>
        {lines.map((line, i) => (
          <Fragment key={i}>
            {i > 0 && "\n"}
            {renderLine(line)}
          </Fragment>
        ))}
      </pre>
    </div>
  );
}
