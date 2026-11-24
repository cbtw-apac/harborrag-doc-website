import Link from "@docusaurus/Link";
import type { ReactNode } from "react";

import { useDocPath } from "@site/src/lib/docPath";

interface Props {
  docId: string;
  className?: string;
  children: ReactNode;
}

/** Link to a doc in the reader's docs version; renders nothing when that version lacks it. */
export default function DocLink({
  docId,
  className,
  children,
}: Props): ReactNode {
  const to = useDocPath(docId);
  return to === undefined ? null : (
    <Link to={to} className={className}>
      {children}
    </Link>
  );
}
