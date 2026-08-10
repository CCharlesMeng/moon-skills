/**
 * Mutation tests for collect_restore_facts.js.
 *
 * Runs the collector's original source inside a minimal DOM stub (no npm / jsdom).
 * Each GREEN/RED pair must fail the "false-negative self-check": restoring the
 * mutated value must flip the assertion, proving the test actually observes the defect.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const EVAL_DIR = path.dirname(fileURLToPath(import.meta.url));
const COLLECTOR_PATH = path.join(EVAL_DIR, "..", "scripts", "collect_restore_facts.js");
const COLLECTOR_SOURCE = fs.readFileSync(COLLECTOR_PATH, "utf8");

const Node = { ELEMENT_NODE: 1, TEXT_NODE: 3 };
const NodeFilter = { SHOW_ELEMENT: 1 };

function cssEscape(value) {
  return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

class ClassList {
  constructor(classes = []) {
    this._classes = [...classes];
  }

  [Symbol.iterator]() {
    return this._classes[Symbol.iterator]();
  }
}

class TextNode {
  constructor(text) {
    this.nodeType = Node.TEXT_NODE;
    this.textContent = text;
    this.parentElement = null;
  }
}

class Element {
  constructor(tagName, options = {}) {
    this.nodeType = Node.ELEMENT_NODE;
    this.tagName = String(tagName).toUpperCase();
    this.attributes = { ...(options.attributes || {}) };
    this.classList = new ClassList(options.classes || []);
    this.children = [];
    this.childNodes = [];
    this.parentElement = null;
    this.value = options.value;
    this._textContent = options.textContent ?? "";
    this.scrollWidth = options.scrollWidth ?? options.width ?? 100;
    this.scrollHeight = options.scrollHeight ?? options.height ?? 40;
    this.clientWidth = options.clientWidth ?? options.width ?? 100;
    this.clientHeight = options.clientHeight ?? options.height ?? 40;
    this._rect = {
      x: options.x ?? 0,
      y: options.y ?? 0,
      left: options.x ?? 0,
      top: options.y ?? 0,
      width: options.width ?? 100,
      height: options.height ?? 40,
      right: (options.x ?? 0) + (options.width ?? 100),
      bottom: (options.y ?? 0) + (options.height ?? 40),
    };
    this._styles = { ...(options.styles || {}) };
    if (options.textContent != null && options.textContent !== "") {
      this.childNodes.push(new TextNode(options.textContent));
    }
  }

  get textContent() {
    if (this.childNodes.length === 0) return this._textContent || "";
    return this.childNodes
      .map((node) => {
        if (node.nodeType === Node.TEXT_NODE) return node.textContent;
        return node.textContent;
      })
      .join("");
  }

  set textContent(value) {
    this._textContent = value;
    this.childNodes = value ? [new TextNode(value)] : [];
    for (const child of this.children) {
      child.parentElement = null;
    }
    this.children = [];
  }

  getAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this.attributes, name)
      ? this.attributes[name]
      : null;
  }

  hasAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this.attributes, name);
  }

  getBoundingClientRect() {
    return { ...this._rect };
  }

  appendChild(child) {
    if (child.nodeType === Node.TEXT_NODE) {
      child.parentElement = this;
      this.childNodes.push(child);
      return child;
    }
    child.parentElement = this;
    this.children.push(child);
    this.childNodes.push(child);
    return child;
  }
}

function matchesSimpleSelector(element, selector) {
  const trimmed = selector.trim();
  const testid = trimmed.match(/^\[data-testid="([^"]+)"\]$/);
  if (testid) return element.getAttribute("data-testid") === testid[1];
  if (trimmed.startsWith(".")) {
    const className = trimmed.slice(1);
    return [...element.classList].includes(className);
  }
  if (/^[a-zA-Z][\w-]*$/.test(trimmed)) {
    return element.tagName.toLowerCase() === trimmed.toLowerCase();
  }
  if (trimmed === "*") return true;
  return false;
}

function collectDescendants(root) {
  const nodes = [];
  const walk = (element) => {
    nodes.push(element);
    for (const child of element.children) walk(child);
  };
  walk(root);
  return nodes;
}

function createDocument(bodyChildren) {
  const html = new Element("html");
  const body = new Element("body");
  html.appendChild(body);
  for (const child of bodyChildren) body.appendChild(child);

  const all = () => collectDescendants(html);

  return {
    body,
    documentElement: html,
    getElementById(id) {
      return all().find((element) => element.getAttribute("id") === id) || null;
    },
    querySelectorAll(selector) {
      return all().filter((element) => matchesSimpleSelector(element, selector));
    },
    createTreeWalker(root, whatToShow) {
      assert.equal(whatToShow, NodeFilter.SHOW_ELEMENT);
      const nodes = collectDescendants(root).filter(
        (element) => element.nodeType === Node.ELEMENT_NODE
      );
      // TreeWalker starts at root; collector reads currentNode then advances with nextNode.
      let index = -1;
      return {
        get currentNode() {
          return index < 0 ? root : nodes[index] || null;
        },
        nextNode() {
          index += 1;
          return nodes[index] || null;
        },
      };
    },
  };
}

function runCollector(input, { elements, viewport = { width: 1280, height: 720 } }) {
  const document = createDocument(elements);
  const sandbox = {
    window: {
      __SDD_RESTORE_INPUT__: input,
      innerWidth: viewport.width,
      innerHeight: viewport.height,
      devicePixelRatio: 1,
      getComputedStyle(element) {
        const styles = element._styles || {};
        return {
          getPropertyValue(name) {
            return styles[name] || "";
          },
          overflowX: styles.overflowX || styles.overflow || "visible",
          overflowY: styles.overflowY || styles.overflow || "visible",
        };
      },
    },
    document,
    Node,
    NodeFilter,
    CSS: { escape: cssEscape },
    navigator: { userAgent: "node-test-stub" },
    Array,
    Object,
    Math,
    Error,
    String,
    Boolean,
    Number,
    JSON,
  };
  sandbox.window.document = document;
  sandbox.globalThis = sandbox;
  const context = vm.createContext(sandbox);
  return vm.runInContext(COLLECTOR_SOURCE, context);
}

function textInput(ruleId, expectedText) {
  return {
    contract: {
      contract_sha256: "test-sha",
      rules: [
        {
          id: ruleId,
          required_layers: ["render"],
          state_scenario: { name: "default" },
          expected: expectedText,
          check_mode: "exact",
        },
      ],
    },
    adapter: {
      schema_version: 1,
      rules: {
        [ruleId]: {
          locators: [{ strategy: "testid", testid: "title" }],
          source_files: ["src/view.tsx"],
          collect: { kind: "text", single: true },
        },
      },
    },
    fixture_status: {},
  };
}

function clipInput(ruleId) {
  return {
    contract: {
      contract_sha256: "test-sha",
      rules: [
        {
          id: ruleId,
          required_layers: ["render"],
          state_scenario: { name: "default" },
          expected: 0,
          check_mode: "clip",
        },
      ],
    },
    adapter: {
      schema_version: 1,
      rules: {
        [ruleId]: {
          locators: [{ strategy: "testid", testid: "panel" }],
          source_files: ["src/view.tsx"],
          collect: { kind: "clip" },
        },
      },
    },
    fixture_status: {},
  };
}

test("text collect: GREEN matching copy, RED after text mutation", () => {
  const ruleId = "R1-text";
  const expected = "筛选条件";
  const input = textInput(ruleId, expected);

  const greenNode = new Element("h2", {
    attributes: { "data-testid": "title" },
    textContent: expected,
  });
  const green = runCollector(input, { elements: [greenNode] });
  assert.equal(green.rules[ruleId].status, "ok");
  assert.equal(green.rules[ruleId].actual, expected);

  const redNode = new Element("h2", {
    attributes: { "data-testid": "title" },
    textContent: "已改坏的文案",
  });
  const red = runCollector(input, { elements: [redNode] });
  assert.equal(red.rules[ruleId].status, "ok");
  assert.equal(red.rules[ruleId].actual, "已改坏的文案");
  assert.notEqual(red.rules[ruleId].actual, expected);

  // False-negative self-check: restoring the correct text must make the RED assertion fail.
  const restoredNode = new Element("h2", {
    attributes: { "data-testid": "title" },
    textContent: expected,
  });
  const restored = runCollector(input, { elements: [restoredNode] });
  assert.throws(() => {
    assert.notEqual(restored.rules[ruleId].actual, expected);
  }, /strictly unequal/i);
});

test("clip collect: GREEN zero clip, RED after ~20px overflow mutation", () => {
  const ruleId = "R5-clip";
  const input = clipInput(ruleId);

  const greenNode = new Element("div", {
    attributes: { "data-testid": "panel" },
    x: 10,
    y: 10,
    width: 200,
    height: 80,
    scrollWidth: 200,
    clientWidth: 200,
    scrollHeight: 80,
    clientHeight: 80,
  });
  const green = runCollector(input, { elements: [greenNode] });
  assert.equal(green.rules[ruleId].status, "ok");
  assert.equal(green.rules[ruleId].actual, 0);

  const redNode = new Element("div", {
    attributes: { "data-testid": "panel" },
    x: 10,
    y: 10,
    width: 200,
    height: 80,
    // Only this geometric defect differs from GREEN: 20px horizontal overflow.
    scrollWidth: 220,
    clientWidth: 200,
    scrollHeight: 80,
    clientHeight: 80,
  });
  const red = runCollector(input, { elements: [redNode] });
  assert.equal(red.rules[ruleId].status, "ok");
  assert.equal(red.rules[ruleId].actual, 20);
  assert.ok(red.rules[ruleId].actual > 0);

  // False-negative self-check: clearing the overflow must make the RED assertion fail.
  const restoredNode = new Element("div", {
    attributes: { "data-testid": "panel" },
    x: 10,
    y: 10,
    width: 200,
    height: 80,
    scrollWidth: 200,
    clientWidth: 200,
    scrollHeight: 80,
    clientHeight: 80,
  });
  const restored = runCollector(input, { elements: [restoredNode] });
  assert.throws(() => {
    assert.ok(restored.rules[ruleId].actual > 0);
  }, /falsy|truthy|ok/i);
});
