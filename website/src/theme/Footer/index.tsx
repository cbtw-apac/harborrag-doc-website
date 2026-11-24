import Link from "@docusaurus/Link";
import { useLocation } from "@docusaurus/router";
import useBaseUrl from "@docusaurus/useBaseUrl";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import type { ReactNode } from "react";

import FeedbackIcon from "@site/src/assets/icons/feedback-icon.svg";
import GitHubIcon from "@site/src/assets/icons/github-icon.svg";
import LinkedInIcon from "@site/src/assets/icons/linkedIn-icon.svg";
import { packageLinks, quickLinks, type FooterLink } from "@site/src/data/footer";
import { CBTW_URL, LINKEDIN_URL, SOURCE_REPO } from "@site/src/lib/site";

import BuildInfo, { useSyncEntry } from "./BuildInfo";
import styles from "./styles.module.css";


function useFeedbackUrl(): string {
  const { siteConfig } = useDocusaurusContext();
  const { pathname } = useLocation();
  const { label, source_sha } = useSyncEntry();
  const params = new URLSearchParams({
    labels: "docs-feedback",
    title: `[Docs Feedback] ${pathname}`,
    body: `Page: ${siteConfig.url}${pathname}\nDocs version: ${label}\nDocs commit: ${source_sha?.slice(0, 7) ?? "unknown"}\n\nFeedback:\n`,
  });
  return `${SOURCE_REPO}/issues/new?${params}`;
}

function LinkItem({ label, href, Icon }: FooterLink): ReactNode {
  return (
    <li>
      <Link href={href} className={styles.link}>
        <Icon className={styles.linkIcon} aria-hidden="true" />
        <span>{label}</span>
      </Link>
    </li>
  );
}

function LinkColumn({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}): ReactNode {
  return (
    <div>
      <p className={styles.columnTitle}>{title}</p>
      <ul className={styles.linkList}>{children}</ul>
    </div>
  );
}

// Evaluated at build time, like the rest of the static HTML.
const YEAR = new Date().getFullYear();

export default function Footer(): ReactNode {
  const logo = useBaseUrl("/img/logo.svg");
  const feedbackUrl = useFeedbackUrl();

  return (
    <footer className={styles.footer}>
      <div className={styles.top}>
        <div>
          <Link to="/" className={styles.logo}>
            <img src={logo} alt="HarborRAG" height={60} />
          </Link>
          <p className={styles.description}>
            A modular, provider-agnostic RAG framework for engineering
            knowledge.
          </p>
        </div>

        <div className={styles.columns}>
          <LinkColumn title="Quick Links">
            {quickLinks.map((link) => (
              <LinkItem key={link.label} {...link} />
            ))}
            <LinkItem
              label="Was this helpful? Give feedback"
              href={feedbackUrl}
              Icon={FeedbackIcon}
            />
          </LinkColumn>
          <LinkColumn title="Packages & Code">
            {packageLinks.map((link) => (
              <LinkItem key={link.label} {...link} />
            ))}
          </LinkColumn>
        </div>
      </div>

      <div className={styles.supporter}>
        <p className={styles.supportText}>
          This project is proudly supported and powered by <b>CBTW</b>
        </p>
        <p className={styles.supportTitle}>Collaboration betters the world</p>
        <Link href={CBTW_URL} className={styles.supportLink}>
          <span className={styles.indicator} aria-hidden="true" />
          <span>www.cbtw.tech</span>
        </Link>
      </div>

      <hr className={styles.divider} />

      <div className={styles.bottom}>
        <p className={styles.copy}>
          © {YEAR} HarborRAG. Built with ❤️ for the AI development community.
        </p>
        <div className={styles.meta}>
          <BuildInfo />
          <div className={styles.social}>
            <Link
              href={SOURCE_REPO}
              className={styles.socialLink}
              title="View HarborRAG on GitHub"
              aria-label="View HarborRAG on GitHub"
            >
              <GitHubIcon width={24} height={24} aria-hidden="true" />
            </Link>
            <Link
              href={LINKEDIN_URL}
              className={styles.socialLink}
              title="CBTW APAC on LinkedIn"
              aria-label="CBTW APAC on LinkedIn"
            >
              <LinkedInIcon width={24} height={24} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
