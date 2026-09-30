import type { Nodes } from "mdast";
import { fromMarkdown } from "mdast-util-from-markdown";

// Nodes whose children are blocks, so their text needs a space between them.
const BLOCK_CONTAINERS = new Set<Nodes["type"]>([
  "root",
  "blockquote",
  "list",
  "listItem",
]);

function plainText(node: Nodes): string {
  if (node.type === "html") return "";
  if ("value" in node) return node.value;
  if (!("children" in node)) return "";

  const separator = BLOCK_CONTAINERS.has(node.type) ? " " : "";
  return node.children.map((child) => plainText(child)).join(separator);
}

/**
 * The text of the first top-level paragraph, or of the whole document when it
 * has none, with Markdown syntax and raw HTML removed. Cut at a word boundary
 * when longer than `maxLength`. Blank for blank input.
 */
export function markdownExcerpt(markdown: string, maxLength = Infinity) {
  const root = fromMarkdown(markdown);
  const source =
    root.children.find((node) => node.type === "paragraph") ?? root;
  const text = plainText(source).replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;

  const cut = text.slice(0, maxLength - 1);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > 0 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}
