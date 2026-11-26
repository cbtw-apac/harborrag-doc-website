// Wrap every Markdown table in <div class="table-scroll">, as HarborRAG's builder does.
// The wrapper scrolls, so the table itself keeps table layout and can fill the width.
interface HastNode {
  type: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

function wrapTables(node: HastNode): void {
  if (!node.children) {
    return;
  }
  node.children = node.children.map((child) => {
    wrapTables(child);
    return child.type === "element" && child.tagName === "table"
      ? {
          type: "element",
          tagName: "div",
          properties: { className: ["table-scroll"] },
          children: [child],
        }
      : child;
  });
}

export default function rehypeTableScroll() {
  return (tree: HastNode): void => wrapTables(tree);
}
