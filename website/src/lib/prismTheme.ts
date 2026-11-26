import type { PrismTheme } from "prism-react-renderer";

// Palette of the syntax colouring in HarborRAG's base.html.
const prismTheme: PrismTheme = {
  plain: { color: "#d4d4d4", backgroundColor: "#141414" },
  styles: [
    {
      types: ["comment", "prolog", "doctype", "cdata"],
      style: { color: "#7c7c7c" },
    },
    {
      types: ["string", "char", "attr-value", "inserted"],
      style: { color: "#98d982" },
    },
    {
      types: ["keyword", "builtin", "boolean", "important"],
      style: { color: "#79b6f2" },
    },
    {
      types: ["class-name", "function"],
      style: { color: "#6fc2ef" },
    },
    {
      types: ["variable", "constant"],
      style: { color: "#f7ca88" },
    },
    { types: ["number"], style: { color: "#f99157" } },
    {
      types: ["tag", "property", "attr-name", "key", "selector"],
      style: { color: "#6fc2ef" },
    },
    { types: ["operator", "punctuation"], style: { color: "#d4d4d4" } },
  ],
};

export default prismTheme;
