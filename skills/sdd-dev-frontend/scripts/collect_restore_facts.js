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

  // 选择器不跨 shadow 边界，所以必须逐个 root 查再合并。不这么做的话，
  // web-component 形态的组件库（Lit / Stencil 构建的那类）会让每条规则都返回
  // 「定位不到」，而报告把它算成 RED——那与真实现偏差在输出上无法区分，
  // 最后会走成「修 3 次 → 打断用户 → 补豁免」，把工具缺口写进冻结基线。
  const collectRoots = () => {
    const roots = [document];
    const queue = [document];
    while (queue.length) {
      const root = queue.shift();
      for (const element of root.querySelectorAll("*")) {
        // 只有 open 模式的 shadowRoot 从外部可见；closed 的拿不到，见 suspectClosedShadow。
        if (element.shadowRoot) {
          roots.push(element.shadowRoot);
          queue.push(element.shadowRoot);
        }
      }
    }
    return roots;
  };

  const deepQueryAll = (selector) => {
    const nodes = [];
    for (const root of collectRoots()) {
      nodes.push(...root.querySelectorAll(selector));
    }
    return nodes;
  };

  /* closed shadow root 从外部无法枚举，也无法读取。所以「定位不到」有两种成因，
   * 必须分开报：选择器写错了（该修 adapter），还是这一层根本不可见（工具边界）。
   * 判据是自定义元素（标签名含 `-`）既没有 shadowRoot 也没有子节点——它渲染出的
   * 内容一定在某处，而我们看不见。 */
  const suspectClosedShadow = () =>
    deepQueryAll("*")
      .filter((element) =>
        element.tagName.includes("-") && !element.shadowRoot && !element.children.length
      )
      .map((element) => element.tagName.toLowerCase());

  const byRole = (locator) => deepQueryAll("*").filter((element) => {
    const role = element.getAttribute("role") || implicitRole(element);
    return role === locator.role && accessibleName(element) === locator.name;
  });

  const byExactText = (text) => {
    const nodes = [];
    for (const root of collectRoots()) {
      const scope = root === document ? document.body : root;
      if (!scope) continue;
      const walker = document.createTreeWalker(scope, NodeFilter.SHOW_ELEMENT);
      let current = walker.currentNode;
      while (current) {
        if (normalizeText(current.textContent) === text) {
          const childHasSameText = Array.from(current.children)
            .some((child) => normalizeText(child.textContent) === text);
          if (!childHasSameText) nodes.push(current);
        }
        current = walker.nextNode();
      }
    }
    return nodes;
  };

  const locate = (locators) => {
    for (const locator of locators || []) {
      let nodes = [];
      if (locator.strategy === "role") nodes = byRole(locator);
      if (locator.strategy === "text") nodes = byExactText(locator.text);
      if (locator.strategy === "testid") {
        nodes = deepQueryAll(`[data-testid="${CSS.escape(locator.testid)}"]`);
      }
      if (locator.strategy === "css") nodes = deepQueryAll(locator.selector);
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

  // 简写属性 → 计算样式 longhand。getComputedStyle 对简写返回整段序列化
  // （background 会带 none repeat scroll…），与期望值必然不等；输出键保留
  // 请求名，与契约 expected 的键对齐。verify_restore_contract.py 有同一份映射。
  const PROPERTY_ALIASES = { background: "background-color", flex: "flex-grow" };

  /* `pseudo` 让规则读 ::before / ::after 的计算样式。不给这个入口的话，图标字体和
   * 设计系统放在伪元素里的装饰内容对采集器完全不可见——不是判错，是静默看不见，
   * 而静默不可见比报错危险。`content` 是伪元素最常判的属性，照常走 properties 请求。 */
  const styleFacts = (element, properties, pseudo) => {
    const computed = window.getComputedStyle(element, pseudo || null);
    const output = {};
    for (const property of properties || []) {
      const resolved = PROPERTY_ALIASES[property] || property;
      output[property] = computed.getPropertyValue(resolved).trim();
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

  const describeElement = (element) => {
    if (!element) return null;
    const testid = element.getAttribute ? element.getAttribute("data-testid") : null;
    const classes = Array.from(element.classList || []).join(".");
    return (
      element.tagName.toLowerCase() +
      (testid ? `[data-testid="${testid}"]` : "") +
      (classes ? `.${classes}` : "")
    );
  };

  // 与 closest() 同一条边界：不跨 shadow 边界。
  const containsNode = (ancestor, node) => {
    let current = node;
    while (current) {
      if (current === ancestor) return true;
      current = current.parentElement;
    }
    return false;
  };

  const cssValue = (style, name) => (style.getPropertyValue(name) || "").trim();

  // 逐条都必须是**计算样式默认值落在下面中性表里**的属性，否则会在每个元素上误命中，
  // 把真正的成因挤掉。`mask` 就是这样被换成 `mask-image` 的：Chrome 给 mask 的默认
  // 计算值是一整段 `none 0% 0% / auto repeat border-box border-box add match-source`。
  const STACKING_CONTEXT_PROPERTIES = [
    "transform",
    "translate",
    "rotate",
    "scale",
    "filter",
    "backdrop-filter",
    "perspective",
    "clip-path",
    "mask-image",
    "mix-blend-mode",
    "isolation",
    "contain",
    "will-change"
  ];
  const STACKING_NEUTRAL_VALUES = ["", "none", "normal", "auto", "0"];
  // with_selector 命中面过宽时，逐对打点会把整页拖垮。超预算不是「量到没问题」，
  // 见 stackingFacts 末尾：截断时不给 true。
  const MAX_STACKING_PROBES = 32;

  const stackingContextReason = (element) => {
    const style = window.getComputedStyle(element);
    const position = cssValue(style, "position");
    if (position === "fixed" || position === "sticky") return `position: ${position}`;
    const zIndex = cssValue(style, "z-index");
    if (zIndex && zIndex !== "auto" && position && position !== "static") {
      return `position: ${position} + z-index: ${zIndex}`;
    }
    const opacity = cssValue(style, "opacity");
    if (opacity && Number(opacity) < 1) return `opacity: ${opacity}`;
    for (const property of STACKING_CONTEXT_PROPERTIES) {
      const value = cssValue(style, property);
      if (value && !STACKING_NEUTRAL_VALUES.includes(value)) return `${property}: ${value}`;
    }
    return null;
  };

  /* 「为什么输了」——这是提示，不是判据。判据永远是下面的命中顺序。
   * 建立层叠上下文的条件是一份还在变的长枚举，这里只覆盖实测最常撞上的两条，
   * 因为它们的共同点是「z-index 的计算值完全正常，却不起作用」——只看样式值
   * 排查不出来，而这正是人要花掉一轮的地方。指不出成因时返回空数组，不编。 */
  const stackingHints = (subject) => {
    const hints = [];
    const style = window.getComputedStyle(subject);
    const zIndex = cssValue(style, "z-index");
    const position = cssValue(style, "position");
    if (zIndex && zIndex !== "auto" && (position === "" || position === "static")) {
      const parent = subject.parentElement;
      const display = parent ? cssValue(window.getComputedStyle(parent), "display") : "";
      if (!/flex|grid/.test(display)) {
        hints.push(`本元素 position: static，z-index: ${zIndex} 不生效`);
      }
    }
    let ancestor = subject.parentElement;
    while (ancestor) {
      const reason = stackingContextReason(ancestor);
      if (reason) {
        hints.push(`祖先 ${describeElement(ancestor)} 建立了新层叠上下文：${reason}`);
        break;
      }
      ancestor = ancestor.parentElement;
    }
    return hints;
  };

  const elementStackAt = (x, y) => {
    if (typeof document.elementsFromPoint === "function") {
      return { nodes: document.elementsFromPoint(x, y), method: "elementsFromPoint" };
    }
    // 退化形态只知道最顶上那个，判不出「第三个元素盖住了两边」之外的排序，
    // 所以 probe_method 要回传，报告里能看出这条结论是哪种精度得来的。
    if (typeof document.elementFromPoint === "function") {
      const node = document.elementFromPoint(x, y);
      return { nodes: node ? [node] : [], method: "elementFromPoint" };
    }
    throw new Error("stacking 需要 document.elementsFromPoint 或 elementFromPoint，当前驱动都没有");
  };

  /* 层叠顺序。`overlap` 只量矩形相交多少，答不出「谁压在谁上面」——蒙层、下拉、
   * 吸顶这些元素本来就该重叠，相交量不为 0 是正常表现，而 z-index 事故恰好全发生
   * 在这类元素之间。读 z-index 计算值同样不行：最常见的事故是祖先的 transform /
   * opacity / filter 建了新层叠上下文把子树整块关进去，此时 z-index 写多大都没用，
   * 而它的计算值完全正常。所以判据取浏览器合成后的真实命中顺序：在两者相交区域
   * 中心打点，看谁先被返回。 */
  const stackingFacts = (nodes, spec) => {
    if (!spec || !spec.with_selector) {
      throw new Error("stacking 必须给 with_selector：层叠规则要说清和谁比");
    }
    const others = deepQueryAll(spec.with_selector);
    const pairs = [];
    for (const subject of nodes) {
      for (const other of others) {
        if (subject !== other) pairs.push([subject, other]);
      }
    }

    const probes = [];
    let probed = 0;
    let truncated = false;
    let method = null;
    let violatingSubject = null;

    for (const [subject, other] of pairs) {
      if (probed >= MAX_STACKING_PROBES) {
        truncated = true;
        break;
      }
      const base = { subject: describeElement(subject), with: describeElement(other) };
      if (containsNode(subject, other) || containsNode(other, subject)) {
        // 祖先与后代之间的命中顺序由文档树决定，不携带层叠信息；判它等于判一句废话。
        probes.push({ ...base, winner: "not-comparable", reason: "ancestor-descendant" });
        continue;
      }
      const a = rect(subject);
      const b = rect(other);
      const left = Math.max(a.left, b.left);
      const right = Math.min(a.right, b.right);
      const top = Math.max(a.top, b.top);
      const bottom = Math.min(a.bottom, b.bottom);
      if (right <= left || bottom <= top) {
        probes.push({ ...base, winner: "not-comparable", reason: "no-overlap" });
        continue;
      }

      const point = { x: (left + right) / 2, y: (top + bottom) / 2 };
      const stack = elementStackAt(point.x, point.y);
      method = stack.method;
      probed += 1;
      const subjectIndex = stack.nodes.findIndex((node) => containsNode(subject, node));
      const otherIndex = stack.nodes.findIndex((node) => containsNode(other, node));
      let winner;
      if (subjectIndex < 0 && otherIndex < 0) winner = "neither";
      else if (otherIndex < 0) winner = "subject";
      else if (subjectIndex < 0) winner = "other";
      else winner = subjectIndex < otherIndex ? "subject" : "other";
      if (winner !== "subject" && !violatingSubject) violatingSubject = subject;
      probes.push({
        ...base,
        winner,
        point,
        top_of_stack: describeElement(stack.nodes[0])
      });
    }

    const decisive = probes.filter((probe) => probe.winner !== "not-comparable");
    let subjectOnTop;
    if (violatingSubject) {
      // 已经量到反例，截断与否都不改变结论。
      subjectOnTop = false;
    } else if (truncated || decisive.length === 0) {
      // 没量全、或压根没有可比对：不给结论。给 true 就是把「没测到」说成「没问题」。
      subjectOnTop = null;
    } else {
      subjectOnTop = true;
    }

    const facts = { subject_on_top: subjectOnTop, probes, candidates: others.length };
    if (method) facts.probe_method = method;
    if (truncated) facts.truncated = true;
    if (violatingSubject) facts.stacking_hints = stackingHints(violatingSubject);
    return facts;
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
    if (kind === "count") {
      /* 虚拟列表里 DOM 只有窗口内的行，`nodes.length` 量到的是窗口而不是数据集——
       * 那会给出一个「看起来对」的错数，比报错危险。ARIA 正是为这件事存在的：
       * 容器声明了 aria-rowcount / aria-setsize 且与渲染数不符时，两个数都给出去，
       * 由契约那侧决定判哪一个，采集器不替它选。 */
      const declared = nodes
        .map((node) => {
          const owner = node.closest("[aria-rowcount], [aria-setsize]");
          if (!owner) return null;
          const value = owner.getAttribute("aria-rowcount") || owner.getAttribute("aria-setsize");
          const parsed = Number.parseInt(value, 10);
          return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
        })
        .find((value) => value !== null);
      if (declared !== undefined && declared !== null && declared !== nodes.length) {
        return { rendered: nodes.length, declared, windowed: true };
      }
      return nodes.length;
    }
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
      const values = nodes.map((node) => styleFacts(node, spec.properties, spec.pseudo));
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "rect") {
      const values = nodes.map(rect);
      return spec && spec.single ? (values[0] || null) : values;
    }
    if (kind === "state") {
      const values = nodes.map((node) => ({
        styles: styleFacts(node, spec.properties, spec.pseudo),
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
      // with_selector 走 deepQueryAll，与主定位同一条 shadow 规则；用
      // document.querySelectorAll 的话，组件库形态下这一侧会恒空而判绿。
      const others = spec && spec.with_selector ? deepQueryAll(spec.with_selector) : nodes;
      let maximum = 0;
      for (let first = 0; first < nodes.length; first += 1) {
        for (let second = 0; second < others.length; second += 1) {
          if (nodes[first] === others[second]) continue;
          maximum = Math.max(maximum, overlapAmount(nodes[first], others[second]));
        }
      }
      return maximum;
    }
    if (kind === "stacking") {
      return stackingFacts(nodes, spec);
    }
    throw new Error(`unsupported collect kind: ${kind}`);
  };

  const results = {};
  const fixtureStatus = input.fixture_status || {};
  // 整页算一次就够，别在每条定位失败时重扫一遍整棵树。
  const closedShadow = suspectClosedShadow();

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
          reason: closedShadow.length
            ? `possible closed shadow root: ${[...new Set(closedShadow)].join(", ")}`
            : "no implementation locator matched",
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
