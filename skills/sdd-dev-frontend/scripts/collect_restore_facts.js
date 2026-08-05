(() => {
  "use strict";

  /*
   * Read-only browser collector for restore-contract rules.
   *
   * Before injection, set:
   *   window.__SDD_RESTORE_INPUT__ = {
   *     contract: <restore-contract.json>,
   *     adapter: <restore-adapter.json>,
   *     fixture_status: { "<rule-id>": "ready" }
   *   }
   *
   * The returned object is the render-results input consumed by
   * scripts/verify_restore_contract.py. This script never takes screenshots and
   * never mutates application state; state scenarios must be triggered by the
   * browser driver before injection.
   */

  const input = window.__SDD_RESTORE_INPUT__;
  if (!input || !input.contract || !input.adapter) {
    return {
      schema_version: 1,
      page_available: true,
      capture_error: "window.__SDD_RESTORE_INPUT__ is missing contract or adapter"
    };
  }

  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();

  const implicitRole = (element) => {
    const tag = element.tagName.toLowerCase();
    if (tag === "button") return "button";
    if (tag === "a" && element.hasAttribute("href")) return "link";
    if (tag === "input") {
      const type = (element.getAttribute("type") || "text").toLowerCase();
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      if (type === "button" || type === "submit" || type === "reset") return "button";
      return "textbox";
    }
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (/^h[1-6]$/.test(tag)) return "heading";
    if (tag === "img") return "img";
    return null;
  };

  const accessibleName = (element) => {
    const labelledBy = element.getAttribute("aria-labelledby");
    if (labelledBy) {
      const value = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => normalizeText(node.textContent))
        .join(" ");
      if (value) return value;
    }
    return normalizeText(
      element.getAttribute("aria-label") ||
      element.getAttribute("alt") ||
      element.getAttribute("title") ||
      element.value ||
      element.textContent
    );
  };

  const byRole = (locator) => Array.from(document.querySelectorAll("*")).filter((element) => {
    const role = element.getAttribute("role") || implicitRole(element);
    return role === locator.role && accessibleName(element) === locator.name;
  });

  const byExactText = (text) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    const nodes = [];
    let current = walker.currentNode;
    while (current) {
      if (normalizeText(current.textContent) === text) {
        const childHasSameText = Array.from(current.children)
          .some((child) => normalizeText(child.textContent) === text);
        if (!childHasSameText) nodes.push(current);
      }
      current = walker.nextNode();
    }
    return nodes;
  };

  const locate = (locators) => {
    for (const locator of locators || []) {
      let nodes = [];
      if (locator.strategy === "role") nodes = byRole(locator);
      if (locator.strategy === "text") nodes = byExactText(locator.text);
      if (locator.strategy === "testid") {
        nodes = Array.from(document.querySelectorAll(`[data-testid="${CSS.escape(locator.testid)}"]`));
      }
      if (locator.strategy === "css") nodes = Array.from(document.querySelectorAll(locator.selector));
      if (nodes.length) return { nodes, locator };
    }
    return { nodes: [], locator: (locators || [])[0] || null };
  };

  const rect = (element) => {
    const value = element.getBoundingClientRect();
    return {
      x: value.x,
      y: value.y,
      top: value.top,
      right: value.right,
      bottom: value.bottom,
      left: value.left,
      width: value.width,
      height: value.height
    };
  };

  const directTexts = (element) => Array.from(element.childNodes)
    .filter((node) => node.nodeType === Node.TEXT_NODE)
    .map((node) => normalizeText(node.textContent))
    .filter(Boolean);

  // Keep this shape identical to design-facts.json blocks[].structure.
  const structure = (element) => ({
    tag: element.tagName.toLowerCase(),
    classes: Array.from(element.classList).sort(),
    texts: directTexts(element),
    children: Array.from(element.children).map(structure)
  });

  const styleFacts = (element, properties) => {
    const computed = window.getComputedStyle(element);
    const output = {};
    for (const property of properties || []) {
      output[property] = computed.getPropertyValue(property).trim();
    }
    return output;
  };

  const horizontalOverflow = (element) => {
    const value = rect(element);
    return Math.max(
      0,
      element.scrollWidth - element.clientWidth,
      value.right - window.innerWidth,
      -value.left
    );
  };

  const overlapAmount = (first, second) => {
    const a = rect(first);
    const b = rect(second);
    const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    return Math.min(width, height);
  };

  const clippingAmount = (element) => {
    const value = rect(element);
    let maximum = Math.max(
      0,
      element.scrollWidth - element.clientWidth,
      element.scrollHeight - element.clientHeight,
      value.right - window.innerWidth,
      value.bottom - window.innerHeight,
      -value.left,
      -value.top
    );
    const parent = element.parentElement;
    if (parent) {
      const parentRect = rect(parent);
      const parentStyle = window.getComputedStyle(parent);
      if (["hidden", "clip"].includes(parentStyle.overflowX)) {
        maximum = Math.max(
          maximum,
          parentRect.left - value.left,
          value.right - parentRect.right
        );
      }
      if (["hidden", "clip"].includes(parentStyle.overflowY)) {
        maximum = Math.max(
          maximum,
          parentRect.top - value.top,
          value.bottom - parentRect.bottom
        );
      }
    }
    return Math.max(0, maximum);
  };

  const collect = (nodes, spec) => {
    const kind = (spec && spec.kind) || "count";
    if (kind === "count") return nodes.length;
    if (kind === "text") {
      const values = nodes.map((node) => normalizeText(node.textContent));
      return spec && spec.single ? (values[0] || "") : values;
    }
    if (kind === "order") return nodes.map((node) => accessibleName(node));
    if (kind === "structure") {
      const values = nodes.map(structure);
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "style") {
      const values = nodes.map((node) => styleFacts(node, spec.properties));
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "rect") {
      const values = nodes.map(rect);
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "state") {
      const values = nodes.map((node) => ({
        styles: styleFacts(node, spec.properties),
        attributes: Object.fromEntries(
          (spec.attributes || []).map((name) => [name, node.getAttribute(name)])
        )
      }));
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "overflow") {
      return Math.max(0, ...nodes.map(horizontalOverflow));
    }
    if (kind === "clip") {
      return Math.max(0, ...nodes.map(clippingAmount));
    }
    if (kind === "overlap") {
      const others = spec && spec.with_selector
        ? Array.from(document.querySelectorAll(spec.with_selector))
        : nodes;
      let maximum = 0;
      for (let first = 0; first < nodes.length; first += 1) {
        for (let second = 0; second < others.length; second += 1) {
          if (nodes[first] === others[second]) continue;
          maximum = Math.max(maximum, overlapAmount(nodes[first], others[second]));
        }
      }
      return maximum;
    }
    throw new Error(`unsupported collect kind: ${kind}`);
  };

  const results = {};
  const fixtureStatus = input.fixture_status || {};

  for (const rule of input.contract.rules || []) {
    if (!(rule.required_layers || []).includes("render") || rule.frozen_exemption) continue;
    const scenario = rule.state_scenario || {};
    if (scenario.fixture_required && fixtureStatus[rule.id] !== "ready") {
      results[rule.id] = {
        status: "missing_fixture",
        reason: `fixture not ready: ${scenario.fixture || scenario.name || rule.id}`
      };
      continue;
    }
    const entry = (input.adapter.rules || {})[rule.id];
    if (!entry) {
      results[rule.id] = { status: "error", reason: "adapter entry missing" };
      continue;
    }
    try {
      const located = locate(entry.locators);
      if (!located.nodes.length) {
        results[rule.id] = {
          status: "error",
          reason: "no implementation locator matched",
          locator_used: located.locator,
          matched: 0
        };
        continue;
      }
      const actual = collect(located.nodes, entry.collect || {});
      results[rule.id] = {
        status: "ok",
        actual,
        locator_used: located.locator,
        matched: located.nodes.length
      };
    } catch (error) {
      results[rule.id] = {
        status: "capture_error",
        reason: error instanceof Error ? error.message : String(error)
      };
    }
  }

  return {
    schema_version: 1,
    contract_sha256: input.contract.contract_sha256,
    page_available: true,
    environment: {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      dpr: window.devicePixelRatio,
      user_agent: navigator.userAgent,
      scroll: {
        width: document.documentElement.scrollWidth,
        height: document.documentElement.scrollHeight
      }
    },
    rules: results
  };
})()
