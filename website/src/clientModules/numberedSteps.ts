// Number every ordered list in a doc, and let a list that follows a code block, table,
// quote or another list continue the previous count instead of restarting.
const CONTINUES_AFTER = "ol, ul, pre, blockquote, table, .theme-code-block";

function previousContentSibling(el: Element): Element | null {
  let node = el.previousElementSibling;
  while (node?.matches("script, style")) {
    node = node.previousElementSibling;
  }
  return node;
}

function numberSteps(): void {
  let lastStep = 0;
  document
    .querySelectorAll<HTMLOListElement>(".theme-doc-markdown ol")
    .forEach((list) => {
      const items = list.querySelectorAll<HTMLLIElement>(":scope > li");
      if (items.length === 0) {
        return;
      }
      let first = 1;
      if (list.hasAttribute("start") && list.start > 0) {
        first = list.start;
      } else if (
        lastStep > 0 &&
        previousContentSibling(list)?.matches(CONTINUES_AFTER)
      ) {
        first = lastStep + 1;
      }
      items.forEach((item, index) => {
        const explicit = Number.parseInt(item.getAttribute("value") ?? "", 10);
        const step = explicit > 0 ? explicit : first + index;
        item.dataset.step = String(step);
        lastStep = step;
      });
    });
}

export function onRouteDidUpdate(): void {
  numberSteps();
}
