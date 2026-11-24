import type { ReactNode } from "react";
import styles from "./styles.module.css";

export default function Hero(): ReactNode {
  return (
    <div className={styles.content}>
      <h1 className={styles.title}>Documentation</h1>
      <p className={styles.description}>
        Comprehensive documentation for HarborRAG and MCP Server
      </p>
    </div>
  );
}
