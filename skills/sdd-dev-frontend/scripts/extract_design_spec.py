#!/usr/bin/env python3
"""Extract deterministic design-spec artifacts from a prototype HTML file.

产出三份 Markdown、稳定的 design-facts.json、按锚点切片的单区块规格素材，
并管理按需生成的不可变原型视觉缓存。零 LLM 参与，只用标准库。
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


EXIT_OK = 0
EXIT_ERROR = 1
# 抽取器读不到的样式来源存在，且调用方未登记。产物照常落盘，退出码阻断流程。
EXIT_COVERAGE_GAPS = 4

# 不影响还原取值的 at 规则，不计入覆盖缺口。
IGNORABLE_AT_RULES = frozenset({"charset", "font-face", "keyframes", "page"})

# 承载状态样式的伪类。`:root` 只放 token 声明，不算状态。
PSEUDO_STATE_RE = re.compile(
    r":(?:hover|focus(?:-visible|-within)?|active|disabled|checked|"
    r"invalid|required|placeholder|first-child|last-child|nth-child|"
    r"not|empty|target|visited)\b"
)

# html.parser 不维护 void 元素的栈平衡，需自行跳过。这些元素不参与结构签名与节点计数。
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr",
}

# 生成器的共享类命名约定：`<属性>_common<N>`。命中它才走「共享类」抽取路径。
SHARED_CLASS_RE = re.compile(r"_common\d+$")
# 具名类的实例后缀：`.text-2`、`.section-87`。仅用于变体族归并提示，不用于主签名。
NAME_INDEX_RE = re.compile(r"-\d+$")

# 字面量频次退化模式只统计这些属性——它们才是跨元素共享的候选值。
LITERAL_TOKEN_PROPS = (
    "color", "background-color", "font-size", "font-weight",
    "line-height", "letter-spacing", "border-radius", "box-shadow",
)

# 产物里 token 表的分组顺序，同时决定字面量去重表的维度。
PROPERTY_GROUPS = (
    ("排版", ("font-size", "font-weight", "line-height", "letter-spacing", "text-align", "font-family", "white-space", "text-overflow")),
    ("颜色", ("color", "background-color", "border-color", "border", "box-shadow", "opacity")),
    ("间距", ("margin", "padding", "gap", "row-gap", "column-gap")),
    ("尺寸", ("width", "height", "min-width", "min-height", "max-width", "max-height")),
    ("布局", ("display", "align-items", "justify-content", "flex", "flex-direction", "flex-wrap", "position", "z-index", "overflow", "box-sizing")),
)

COLOR_RE = re.compile(r"(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))")
URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# 占位符判据（产物里会原样列出，下游 agent 据此判定「不得作为 R2 期望值」）
PLACEHOLDER_MASK_RE = re.compile(r"X{2,}")
PLACEHOLDER_NUMERIC_RE = re.compile(
    r"^[+-]?\d[\d,]*(?:\.\d+)?\s*(?:[%‰$]|[\u4e00-\u9fa5]{1,2}|[A-Za-z]{1,3})?(?:[.…]{1,3})?$"
)
PLACEHOLDER_DATE_RE = re.compile(
    r"\d{4}\s*[/\-年]\s*\d{1,2}\s*(?:[/\-月]\s*\d{1,2}\s*日?)?"
)
PLACEHOLDER_ELLIPSIS_RE = re.compile(r"^[.…]+$")

# 「文件是否格式化」的判据：平均行长。标准版 42、导出件 134599。
FORMATTED_MAX_AVG_LINE = 200
# 摘要类字段的截断长度，防止产物被单条长文案顶爆。
SUMMARY_TEXT_LIMIT = 24


class Element:
    """DOM 元素节点。只保留区块切分与签名需要的字段。"""

    __slots__ = (
        "tag", "classes", "parent", "children", "texts",
        "line", "end_line", "order", "size", "signature", "family",
    )

    def __init__(self, tag: str, classes: list[str], parent: "Element | None", line: int, order: int) -> None:
        self.tag = tag
        self.classes = classes
        self.parent = parent
        self.children: list[Element] = []
        self.texts: list[str] = []
        self.line = line
        self.end_line = line
        self.order = order
        self.size = 1
        self.signature = ""
        self.family = ""


class PrototypeParser(html.parser.HTMLParser):
    """只解析 <body> 子树，忽略 style/script 文本。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: Element | None = None
        self.elements: list[Element] = []
        self.void_counts: dict[str, int] = {}
        self._stack: list[Element] = []
        self._in_body = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "script"):
            self._skip_depth += 1
            return
        if tag == "body":
            self._in_body = True
            return
        if not self._in_body:
            return
        if tag in VOID_TAGS:
            self.void_counts[tag] = self.void_counts.get(tag, 0) + 1
            return
        class_attr = ""
        for name, value in attrs:
            if name == "class" and value:
                class_attr = value
        classes = [item for item in class_attr.split() if item]
        parent = self._stack[-1] if self._stack else None
        node = Element(tag, classes, parent, self.getpos()[0], len(self.elements))
        if parent is not None:
            parent.children.append(node)
        elif self.root is None:
            self.root = node
        else:
            # body 下有多个顶层元素时挂到合成根上（见 parse_document）。
            self.root.children.append(node)
            node.parent = self.root
        self.elements.append(node)
        self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_TAGS:
            if self._in_body:
                self.void_counts[tag] = self.void_counts.get(tag, 0) + 1
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "body":
            self._in_body = False
            return
        if not self._in_body or tag in VOID_TAGS:
            return
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index].tag == tag:
                self._stack[index].end_line = self.getpos()[0]
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self._in_body or self._skip_depth or not self._stack:
            return
        text = " ".join(data.split())
        if text:
            self._stack[-1].texts.append(text)


def normalize_css_source(source: str) -> str:
    """Normalize insignificant CSS whitespace while preserving strings and all rules."""
    output: list[str] = []
    pending_space = False
    quote: str | None = None
    escaped = False
    index = 0
    punctuation = set("{}:;,>+~()")
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character == "/" and following == "*":
            end = source.find("*/", index + 2)
            index = len(source) if end < 0 else end + 2
            pending_space = True
            continue
        if character in {"'", '"'}:
            if pending_space and output and output[-1] not in punctuation:
                output.append(" ")
            output.append(character)
            quote = character
            pending_space = False
            index += 1
            continue
        if character.isspace():
            pending_space = True
            index += 1
            continue
        if character in punctuation:
            if output and output[-1] == " ":
                output.pop()
            output.append(character)
            pending_space = False
            index += 1
            continue
        if pending_space and output and output[-1] not in punctuation:
            output.append(" ")
        output.append(character)
        pending_space = False
        index += 1
    return "".join(output).strip()


def normalize_fingerprint_attribute(name: str, value: str | None) -> tuple[str, str]:
    normalized_name = name.lower()
    normalized_value = "" if value is None else value
    if normalized_name == "class":
        normalized_value = " ".join(sorted(set(normalized_value.split())))
    elif normalized_name == "style":
        normalized_value = normalize_css_source(normalized_value)
    else:
        normalized_value = " ".join(normalized_value.split())
    return normalized_name, normalized_value


class FullFingerprintParser(html.parser.HTMLParser):
    """Capture complete DOM attributes, void elements, inline styles and full CSS."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[str] = []
        self.style_chunks: list[str] = []
        self._style_depth = 0
        self._script_depth = 0

    def append_start(self, tag: str, attrs: list[tuple[str, str | None]], closed: bool) -> None:
        normalized = sorted(normalize_fingerprint_attribute(name, value) for name, value in attrs)
        attributes = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
        self.events.append(f"S|{tag.lower()}|{attributes}|{int(closed)}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        self.append_start(lowered, attrs, lowered in VOID_TAGS)
        if lowered == "style":
            self._style_depth += 1
        elif lowered == "script":
            self._script_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.append_start(tag, attrs, True)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "style":
            self._style_depth = max(0, self._style_depth - 1)
        elif lowered == "script":
            self._script_depth = max(0, self._script_depth - 1)
        if lowered not in VOID_TAGS:
            self.events.append(f"E|{lowered}")

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.style_chunks.append(data)
            return
        if self._script_depth:
            return
        text = " ".join(data.split())
        if text:
            self.events.append(f"T|{text}")


def full_dom_css_sha256(source: str) -> str:
    parser = FullFingerprintParser()
    parser.feed(source)
    parser.close()
    payload = {
        "dom": parser.events,
        "css": normalize_css_source("\n".join(parser.style_chunks)),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class CoverageParser(html.parser.HTMLParser):
    """只收「抽取器看不见的样式来源」，供覆盖缺口判定。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stylesheet_hrefs: list[str] = []
        self.script_srcs: list[str] = []
        self.inline_style_elements = 0
        self.style_blocks = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        values = {name.lower(): (value or "") for name, value in attrs}
        if lowered == "style":
            self.style_blocks += 1
        elif lowered == "link":
            rel = values.get("rel", "").lower()
            href = values.get("href", "").strip()
            if href and ("stylesheet" in rel or href.split("?")[0].lower().endswith(".css")):
                self.stylesheet_hrefs.append(href)
        elif lowered == "script":
            src = values.get("src", "").strip()
            if src:
                self.script_srcs.append(src)
        if values.get("style", "").strip():
            self.inline_style_elements += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def detect_coverage_gaps(source: str, other_rules: list["Rule"]) -> list[dict]:
    """列出本抽取器读不到、但会影响还原期望值的样式来源。

    抽取器的能力边界是「内联 <style> 里的单类选择器」。边界之外的样式来源一律
    在这里显式登记：不登记就会变成区块规格里的 `未见`，进而让冻结基线静默漏项。
    """
    parser = CoverageParser()
    parser.feed(source)
    parser.close()

    style_bodies = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", source, re.S | re.I))
    style_bodies = re.sub(r"/\*.*?\*/", "", style_bodies, flags=re.S)
    at_rules: dict[str, int] = {}
    for name in re.findall(r"@([a-zA-Z-]+)", style_bodies):
        lowered = name.lower()
        if lowered in IGNORABLE_AT_RULES:
            continue
        at_rules[lowered] = at_rules.get(lowered, 0) + 1

    gaps: list[dict] = []
    if parser.stylesheet_hrefs:
        gaps.append({
            "kind": "外链样式表",
            "count": len(parser.stylesheet_hrefs),
            "detail": sorted(set(parser.stylesheet_hrefs)),
            "impact": "其中的声明不进 design_tokens / layout_declarations，R3 / R4 会退化为 `未见`",
        })
    if at_rules:
        gaps.append({
            "kind": "at 规则",
            "count": sum(at_rules.values()),
            "detail": [f"@{name} ×{count}" for name, count in sorted(at_rules.items())],
            "impact": "整块跳过；@media 内的响应式取值与 @layer / @container 内的声明全部不可见",
        })
    if parser.inline_style_elements:
        gaps.append({
            "kind": "行内 style 属性",
            "count": parser.inline_style_elements,
            "detail": [f"{parser.inline_style_elements} 个元素带非空 style 属性"],
            "impact": "行内声明不参与类 → 声明映射，这些元素的尺寸与间距不可见",
        })
    # 纯元素与通配选择器（`*`、`body`、`:root`）只承载 reset，不持有区块级期望值，
    # 计入缺口只会制造噪声，让调用方习惯性忽略真缺口。
    scoped = sorted({
        rule.selector for rule in other_rules
        if "." in rule.selector or PSEUDO_STATE_RE.search(rule.selector)
    })
    if scoped:
        gaps.append({
            "kind": "非单类选择器",
            "count": len(scoped),
            "detail": scoped[:20] + ([f"…另 {len(scoped) - 20} 条"] if len(scoped) > 20 else []),
            "impact": "伪类、后代与组合选择器只登记不解析，R4 状态样式取不到期望值",
        })
    if parser.script_srcs:
        gaps.append({
            "kind": "外部脚本",
            "count": len(parser.script_srcs),
            "detail": sorted(set(parser.script_srcs)),
            "impact": "运行时生成的 CSS 或 DOM（CDN 版原子化 CSS、组件运行时）在静态抽取中不存在",
        })
    if not parser.style_blocks and not parser.stylesheet_hrefs:
        gaps.append({
            "kind": "无样式来源",
            "count": 0,
            "detail": ["原型里既没有 <style> 块也没有外链样式表"],
            "impact": "还原侧没有任何可抽取的视觉取值",
        })
    return gaps


class Rule:
    """一条 CSS 规则。只区分「单类选择器」与「其他」两种。"""

    __slots__ = ("selector", "class_name", "declarations")

    def __init__(self, selector: str, class_name: str | None, declarations: list[tuple[str, str]]) -> None:
        self.selector = selector
        self.class_name = class_name
        self.declarations = declarations


class Document:
    """一次解析的全部产物输入。"""

    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        self.line_count = source.count("\n") + 1
        self.char_count = len(source)
        self.avg_line_length = self.char_count / max(1, self.line_count)
        self.formatted = self.avg_line_length <= FORMATTED_MAX_AVG_LINE
        self.root: Element | None = None
        self.elements: list[Element] = []
        self.void_counts: dict[str, int] = {}
        self.rules: list[Rule] = []
        self.class_rules: dict[str, list[tuple[str, str]]] = {}
        self.other_rules: list[Rule] = []
        self.class_usage: dict[str, int] = {}
        self.doc_hash = ""
        self.dom_css_sha256 = ""
        self.legacy_dom_css_sha256 = ""


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #


def parse_style_rules(source: str) -> list[Rule]:
    """把全部 <style> 块拍平成规则列表。不做级联，只要「类 → 声明」映射。"""
    rules: list[Rule] = []
    for style_body in re.findall(r"<style[^>]*>(.*?)</style>", source, re.S | re.I):
        cleaned = re.sub(r"/\*.*?\*/", "", style_body, flags=re.S)
        # 设计稿导出件不含 @media / 嵌套规则；遇到时整块跳过而非解析失败。
        cleaned = re.sub(r"@[a-zA-Z-]+[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", cleaned, flags=re.S)
        for raw_selector, raw_body in re.findall(r"([^{}]+)\{([^{}]*)\}", cleaned):
            selector = " ".join(raw_selector.split())
            if not selector:
                continue
            declarations: list[tuple[str, str]] = []
            for chunk in split_declarations(raw_body):
                if ":" not in chunk:
                    continue
                prop, value = chunk.split(":", 1)
                prop = prop.strip().lower()
                value = " ".join(value.split())
                if prop and value:
                    declarations.append((prop, value))
            match = re.fullmatch(r"\.([A-Za-z_][\w-]*)", selector)
            rules.append(Rule(selector, match.group(1) if match else None, declarations))
    return rules


def split_declarations(body: str) -> list[str]:
    """按 `;` 切声明，但不切 url(...) / rgba(...) 括号内的分号。"""
    chunks: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == ";" and depth == 0:
            chunks.append("".join(current))
            current = []
            continue
        current.append(char)
    chunks.append("".join(current))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def parse_document(path: Path) -> Document:
    source = path.read_text(encoding="utf-8", errors="replace")
    document = Document(path, source)

    parser = PrototypeParser()
    parser.feed(source)
    parser.close()
    if parser.root is None:
        raise ValueError(f"没有在 <body> 内找到任何元素节点：{path}")
    document.root = parser.root
    document.elements = parser.elements
    document.void_counts = parser.void_counts

    for rule in parse_style_rules(source):
        document.rules.append(rule)
        if rule.class_name is None:
            document.other_rules.append(rule)
        else:
            document.class_rules.setdefault(rule.class_name, []).extend(rule.declarations)

    for element in document.elements:
        for class_name in element.classes:
            document.class_usage[class_name] = document.class_usage.get(class_name, 0) + 1

    compute_signatures(document.root)
    document.legacy_dom_css_sha256 = normalized_document_sha256(document)
    document.doc_hash = document.legacy_dom_css_sha256[:8]
    document.dom_css_sha256 = full_dom_css_sha256(source)
    return document


def compute_signatures(node: Element) -> int:
    """自底向上算子树大小、结构签名与变体族键。签名忽略文案，只看 tag+class。"""
    size = 1
    child_signatures: list[str] = []
    child_families: list[str] = []
    for child in node.children:
        size += compute_signatures(child)
        child_signatures.append(child.signature)
        child_families.append(child.family)
    node.size = size
    exact = ".".join(sorted(set(node.classes)))
    node.signature = f"{node.tag}[{exact}]({','.join(child_signatures)})"
    family = ".".join(sorted({NAME_INDEX_RE.sub("", name) for name in node.classes}))
    node.family = f"{node.tag}[{family}]({','.join(child_families)})"
    return size


def iter_subtree(node: Element):
    yield node
    for child in node.children:
        yield from iter_subtree(child)


def serialize_subtree(node: Element) -> str:
    """内容哈希的输入：tag + class + 文案，逐层拼接。与空白格式无关。"""
    parts = [node.tag, "|", ".".join(sorted(set(node.classes))), "|", "\x1f".join(node.texts)]
    for child in node.children:
        parts.append("<")
        parts.append(serialize_subtree(child))
        parts.append(">")
    return "".join(parts)


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def normalized_document_source(document: Document) -> str:
    """归一化后的 DOM + CSS；与 HTML 空白格式无关。"""
    css_part = "\n".join(
        f"{name}{{{';'.join(f'{prop}:{value}' for prop, value in declarations)}}}"
        for name, declarations in sorted(document.class_rules.items())
    )
    other_part = "\n".join(
        f"{rule.selector}{{{';'.join(f'{prop}:{value}' for prop, value in rule.declarations)}}}"
        for rule in document.other_rules
    )
    return serialize_subtree(document.root) + "\n" + css_part + "\n" + other_part


def normalized_document_sha256(document: Document) -> str:
    """归一化 DOM/CSS 的完整 SHA-256。"""
    return hashlib.sha256(
        normalized_document_source(document).encode("utf-8")
    ).hexdigest()


def normalized_hash(document: Document) -> str:
    """兼容旧调用的 8 位文档哈希。"""
    return normalized_document_sha256(document)[:8]


# --------------------------------------------------------------------------- #
# 共享类 / 具名类二分
# --------------------------------------------------------------------------- #


class TokenSet:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.tokens: list[dict] = []
        self.token_classes: set[str] = set()
        self.layout_classes: list[str] = []
        self.rejected: list[tuple[str, str]] = []


def classify_classes(document: Document, mode: str) -> TokenSet:
    """共享类 → design tokens；具名类 → 逐元素布局值。

    `auto`：命中 `_commonN` 约定（≥3 个类）时走 shared，否则退化为字面量频次统计。
    """
    shared_candidates = [name for name in document.class_rules if SHARED_CLASS_RE.search(name)]
    effective = mode
    if mode == "auto":
        effective = "shared" if len(shared_candidates) >= 3 else "literal"

    if effective == "shared":
        result = TokenSet("shared-class")
        for name in sorted(shared_candidates, key=lambda item: sort_key_class(document, item)):
            declarations = document.class_rules[name]
            usage = document.class_usage.get(name, 0)
            if len(declarations) != 1:
                result.rejected.append((name, f"{len(declarations)} 条属性，非单属性"))
                continue
            if usage < 2:
                result.rejected.append((name, f"仅 {usage} 个元素引用"))
                continue
            prop, value = declarations[0]
            result.tokens.append({
                "name": name,
                "property": prop,
                "value": value,
                "usage": usage,
                "source": f".{name}",
            })
            result.token_classes.add(name)
        for name in document.class_rules:
            if name not in result.token_classes:
                result.layout_classes.append(name)
        return result

    result = TokenSet("literal-frequency")
    buckets: dict[tuple[str, str], list[str]] = {}
    for name, declarations in document.class_rules.items():
        for prop, value in declarations:
            if prop in LITERAL_TOKEN_PROPS:
                buckets.setdefault((prop, value), []).append(name)
    counter = 0
    for (prop, value), owners in sorted(
        buckets.items(), key=lambda item: (-len(item[1]), item[0][0], item[0][1])
    ):
        if len(owners) < 2:
            result.rejected.append((f"{prop}:{value}", f"仅 1 个类使用（{owners[0]}）"))
            continue
        counter += 1
        result.tokens.append({
            "name": f"{prop}-literal{counter}",
            "property": prop,
            "value": value,
            "usage": sum(document.class_usage.get(owner, 0) for owner in owners),
            "source": "、".join(f".{owner}" for owner in sorted(owners)[:4])
            + ("…" if len(owners) > 4 else ""),
        })
    result.layout_classes = list(document.class_rules)
    return result


def sort_key_class(document: Document, name: str) -> tuple:
    return (-document.class_usage.get(name, 0), name)


# --------------------------------------------------------------------------- #
# 字面量 / 资源
# --------------------------------------------------------------------------- #


def collect_literals(document: Document) -> dict[str, list[tuple[str, int]]]:
    """按维度收集去重字面量。计数单位是「声明中出现的次数」。"""
    buckets: dict[str, dict[str, int]] = {
        "颜色": {}, "字号": {}, "行高": {}, "字重": {},
        "圆角": {}, "阴影": {}, "间距": {}, "尺寸": {},
    }

    def bump(dimension: str, value: str) -> None:
        buckets[dimension][value] = buckets[dimension].get(value, 0) + 1

    for rule in document.rules:
        for prop, value in rule.declarations:
            for match in COLOR_RE.finditer(value):
                bump("颜色", normalize_color(match.group(1)))
            if prop == "font-size":
                bump("字号", value)
            elif prop == "line-height":
                bump("行高", value)
            elif prop == "font-weight":
                bump("字重", value)
            elif prop == "border-radius":
                bump("圆角", value)
            elif prop == "box-shadow":
                bump("阴影", value)
            elif prop in ("margin", "padding", "gap"):
                bump("间距", value)
            elif prop in ("width", "height"):
                bump("尺寸", value)
    return {
        dimension: sorted(values.items(), key=lambda item: (-item[1], item[0]))
        for dimension, values in buckets.items()
    }


def normalize_color(value: str) -> str:
    """`rgba(25, 25, 25, 1)` 与 `rgba(25,25,25,1)` 视为同一个颜色。"""
    if value.startswith("#"):
        return value.lower()
    head, _, rest = value.partition("(")
    return f"{head.lower()}({','.join(part.strip() for part in rest.rstrip(')').split(','))})"


class AssetReferenceParser(html.parser.HTMLParser):
    """Collect resource-bearing HTML attributes without treating navigation as assets."""

    ASSET_ATTRIBUTES = {
        "img": ("src", "srcset"),
        "source": ("src", "srcset"),
        "video": ("src", "poster"),
        "audio": ("src",),
        "script": ("src",),
        "link": ("href",),
        "input": ("src",),
        "object": ("data",),
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        wanted = self.ASSET_ATTRIBUTES.get(tag.lower())
        if not wanted:
            return
        values = {name.lower(): value for name, value in attrs if value}
        for attribute in wanted:
            value = values.get(attribute)
            if not value:
                continue
            if attribute == "srcset":
                for candidate in value.split(","):
                    url = candidate.strip().split()[0] if candidate.strip() else ""
                    if url:
                        self.urls.append(url)
            else:
                self.urls.append(value.strip())


def collect_html_asset_urls(source: str) -> list[str]:
    parser = AssetReferenceParser()
    parser.feed(source)
    parser.close()
    return parser.urls


def resource_fingerprint(base: Path, url: str) -> dict:
    """Return a stable resource state and content digest.

    Remote resources cannot be fetched in a deterministic offline extractor, so the
    URL itself is hashed and the state is explicit. Local missing resources use a
    stable ``missing:<url>`` marker; appearance/disappearance therefore invalidates
    the prototype fingerprint.
    """
    remote = bool(re.match(r"^(?:[a-z]+:)?//", url, re.I))
    embedded = url.lower().startswith("data:")
    if remote:
        return {
            "status": "remote-unresolved",
            "missing": False,
            "remote": True,
            "content_sha256": hashlib.sha256(
                f"remote-unresolved:{url}".encode("utf-8")
            ).hexdigest(),
        }
    if embedded:
        return {
            "status": "embedded",
            "missing": False,
            "remote": False,
            "content_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        }

    split = urlsplit(url)
    relative = unquote(split.path)
    resource_path = (base / relative).resolve()
    if not resource_path.is_file():
        return {
            "status": "missing",
            "missing": True,
            "remote": False,
            "content_sha256": hashlib.sha256(
                f"missing:{url}".encode("utf-8")
            ).hexdigest(),
        }
    return {
        "status": "present",
        "missing": False,
        "remote": False,
        "content_sha256": hashlib.sha256(resource_path.read_bytes()).hexdigest(),
    }


def collect_assets(document: Document) -> list[dict]:
    """资源引用清单，含稳定的存在状态与内容 SHA-256。"""
    usage: dict[str, dict] = {}
    for name, declarations in document.class_rules.items():
        for _, value in declarations:
            for match in URL_RE.finditer(value):
                url = match.group(2).strip()
                entry = usage.setdefault(url, {"url": url, "classes": [], "elements": 0})
                if name not in entry["classes"]:
                    entry["classes"].append(name)
                entry["elements"] += document.class_usage.get(name, 0)
    for rule in document.other_rules:
        for _, value in rule.declarations:
            for match in URL_RE.finditer(value):
                url = match.group(2).strip()
                entry = usage.setdefault(url, {"url": url, "classes": [], "elements": 0})
                if rule.selector not in entry["classes"]:
                    entry["classes"].append(rule.selector)

    for url in collect_html_asset_urls(document.source):
        usage.setdefault(url, {"url": url, "classes": ["<html-attribute>"], "elements": 1})

    base = document.path.parent
    assets: list[dict] = []
    for url in sorted(usage):
        entry = usage[url]
        entry.update(resource_fingerprint(base, url))
        assets.append(entry)
    return assets


def prototype_fingerprint(document: Document, assets: list[dict]) -> str:
    payload = {
        "dom_css_sha256": document.dom_css_sha256,
        "resources": [
            {
                "url": item["url"],
                "status": item["status"],
                "content_sha256": item["content_sha256"],
            }
            for item in assets
        ],
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------- #
# 文案
# --------------------------------------------------------------------------- #


def classify_text(text: str) -> tuple[str, str]:
    """返回 (类别, 判据编号)。类别为 `动态数据位` 或 `静态标签`。"""
    if PLACEHOLDER_MASK_RE.search(text):
        return "动态数据位", "P1"
    if PLACEHOLDER_DATE_RE.search(text):
        return "动态数据位", "P3"
    if PLACEHOLDER_ELLIPSIS_RE.fullmatch(text):
        return "动态数据位", "P4"
    for piece in text.split():
        if PLACEHOLDER_NUMERIC_RE.fullmatch(piece):
            return "动态数据位", "P2"
    return "静态标签", "-"


def format_template(text: str) -> str:
    """数字换成 9，X 掩码原样保留——给下游一个格式模板而不是字面期望值。"""
    return re.sub(r"\d", "9", text)


def collect_texts(document: Document, block_of: dict[int, str]) -> dict:
    entries: dict[str, dict] = {}
    total = 0
    for element in document.elements:
        for text in element.texts:
            total += 1
            entry = entries.get(text)
            if entry is None:
                category, rule_id = classify_text(text)
                entry = entries[text] = {
                    "text": text,
                    "count": 0,
                    "category": category,
                    "rule": rule_id,
                    "blocks": [],
                    "tags": [],
                }
            entry["count"] += 1
            anchor = block_of.get(id(element), "-")
            if anchor not in entry["blocks"]:
                entry["blocks"].append(anchor)
            if element.tag not in entry["tags"]:
                entry["tags"].append(element.tag)
    ordered = sorted(entries.values(), key=lambda item: (-item["count"], item["text"]))
    return {
        "total_nodes": total,
        "unique": ordered,
        "static": [item for item in ordered if item["category"] == "静态标签"],
        "dynamic": [item for item in ordered if item["category"] == "动态数据位"],
    }


# --------------------------------------------------------------------------- #
# Interface Inventory
# --------------------------------------------------------------------------- #


def find_repeated_patterns(document: Document, min_nodes: int, min_instances: int) -> dict:
    """结构签名去重，取不互相嵌套的顶层重复模式。

    候选按子树规模降序挑选（「顶层」= 尽可能外层），与已选模式的节点有任何
    重叠即跳过，保证模式之间不互相嵌套。
    """
    groups: dict[str, list[Element]] = {}
    for element in document.elements:
        if element.size >= min_nodes:
            groups.setdefault(element.signature, []).append(element)

    candidates = [
        (signature, instances)
        for signature, instances in groups.items()
        if len(instances) >= min_instances
    ]
    candidates.sort(key=lambda item: (-item[1][0].size, -len(item[1]), item[0]))

    covered: set[int] = set()
    accepted: list[dict] = []
    for signature, instances in candidates:
        node_ids = {id(node) for instance in instances for node in iter_subtree(instance)}
        if node_ids & covered:
            continue
        covered |= node_ids
        accepted.append({
            "signature": signature,
            "instances": instances,
            "size": instances[0].size,
            "count": len(instances),
            "covered": len(node_ids),
        })

    accepted.sort(key=lambda item: (-item["covered"], -item["size"], item["signature"]))
    families: dict[str, list[int]] = {}
    family_index: dict[str, list[Element]] = {}
    for element in document.elements:
        if element.size >= min_nodes:
            family_index.setdefault(element.family, []).append(element)
    for index, pattern in enumerate(accepted):
        pattern["code"] = f"IC-{index + 1:02d}"
        families.setdefault(pattern["instances"][0].family, []).append(index)
    for indexes in families.values():
        if len(indexes) < 2:
            continue
        codes = [accepted[i]["code"] for i in indexes]
        for i in indexes:
            accepted[i]["merge_candidates"] = [code for code in codes if code != accepted[i]["code"]]

    # 变体候选：同一变体族（class 仅差实例序号）但结构签名不完全相同的元素。
    # 它们是「同一组件的变体」的最强候选，归并与否由 extract-prototype 判定。
    variant_nodes = 0
    for pattern in accepted:
        taken = {id(instance) for instance in pattern["instances"]}
        variants = [
            element
            for element in family_index.get(pattern["instances"][0].family, [])
            if id(element) not in taken and element.signature != pattern["signature"]
        ]
        pattern["variants"] = variants
        variant_nodes += sum(element.size for element in variants)

    return {
        "patterns": accepted,
        "total_nodes": len(document.elements),
        "covered_nodes": len(covered),
        "coverage": len(covered) / max(1, len(document.elements)),
        "variant_nodes": variant_nodes,
    }


# --------------------------------------------------------------------------- #
# 区块切分
# --------------------------------------------------------------------------- #


def anchor_class(document: Document, element: Element, token_classes: set[str]) -> str | None:
    """锚点主体取该元素最具区分度的具名 class；token 类不能充当锚点。"""
    named_classes = [name for name in element.classes if name not in token_classes]
    if not named_classes:
        return None
    return min(
        named_classes,
        key=lambda name: (
            document.class_usage.get(name, 0),
            element.classes.index(name),
        ),
    )


def build_anchors(document: Document, token_classes: set[str]) -> dict[int, str]:
    """给每个元素算锚点。

    class 在全稿出现多次时加 `[i]`——i 是该 class 在 DOM 序中的出现序号（第 i 个带这个
    class 的元素），因此拿 `rg` 数一遍就能复算，不依赖本脚本的内部顺序。
    """
    seen: dict[str, int] = {}
    occurrence: dict[int, dict[str, int]] = {}
    for element in document.elements:
        indexes: dict[str, int] = {}
        for name in element.classes:
            seen[name] = seen.get(name, 0) + 1
            indexes[name] = seen[name]
        occurrence[id(element)] = indexes

    def class_reference(element: Element, name: str) -> str:
        total = document.class_usage.get(name, 0)
        if total <= 1:
            return f".{name}"
        return f".{name}[{occurrence[id(element)][name]}]"

    def fallback_anchor(element: Element) -> str:
        """无具名 class 时走 class 结构路径，不退回语义标签。

        优先用最近具名后代反向定位当前祖先；没有具名后代时，用最近具名祖先
        加子节点序号路径。整个子树都没有具名 class 才退化为纯 DOM 序号路径。
        """
        queue = [(child, 1) for child in element.children]
        while queue:
            descendant, depth = queue.pop(0)
            name = anchor_class(document, descendant, token_classes)
            if name is not None:
                return f"@ancestor({depth},{class_reference(descendant, name)})"
            queue.extend((child, depth + 1) for child in descendant.children)

        path: list[int] = []
        current = element
        while current.parent is not None:
            path.append(current.parent.children.index(current) + 1)
            current = current.parent
            name = anchor_class(document, current, token_classes)
            if name is not None:
                indexes = ".".join(str(index) for index in reversed(path))
                return f"@path({class_reference(current, name)};{indexes})"

        root_path: list[int] = []
        current = element
        while current.parent is not None:
            root_path.append(current.parent.children.index(current) + 1)
            current = current.parent
        suffix = ".".join(str(index) for index in reversed(root_path)) or "root"
        return f"@dom({suffix})"

    anchors: dict[int, str] = {}
    for element in document.elements:
        name = anchor_class(document, element, token_classes)
        if name is None:
            anchors[id(element)] = fallback_anchor(element)
            continue
        anchors[id(element)] = class_reference(element, name)
    return anchors


def split_blocks(document: Document, max_nodes: int) -> list[Element]:
    """按 class 结构自顶向下切区块，一个区块恰好是一个元素子树。

    - 节点数不超上限 → 直接成块（尽可能取外层，保住上下文）
    - 超上限且只有一个子元素 → 穿透下钻，外层容器只作父链坐标
    - 超上限且有 ≥2 个实质子结构 → 按子元素切开
    - 超上限但子元素全是叶子（扁平容器，如一行 60 个单元格）→ 整块给出，不切碎

    切分只保证「可按需读取的确定性候选段」；把段归并成「一屏可截」的页面区块是
    `extract-prototype` 的职责，因此这里允许出现少数极小的候选段。
    """
    blocks: list[Element] = []

    def visit(node: Element) -> None:
        if node.size <= max_nodes or not node.children:
            blocks.append(node)
            return
        if len(node.children) == 1:
            visit(node.children[0])
            return
        if len([child for child in node.children if child.size >= 3]) < 2:
            blocks.append(node)
            return
        for child in node.children:
            visit(child)

    visit(document.root)
    return blocks


def block_records(
    document: Document, blocks: list[Element], anchors: dict[int, str], max_nodes: int
) -> list[dict]:
    records: list[dict] = []
    for element in blocks:
        texts: list[str] = []
        for node in iter_subtree(element):
            texts.extend(node.texts)
        records.append({
            "anchor": anchors[id(element)],
            "tag": element.tag,
            "classes": list(element.classes),
            "nodes": element.size,
            "oversize": element.size > max_nodes,
            "hash": short_hash(serialize_subtree(element)),
            "lines": line_range(document, element),
            "parents": parent_chain(element, anchors),
            "text_nodes": len(texts),
            "summary": summarize(texts),
            "element": element,
        })
    return records


def line_range(document: Document, element: Element) -> str:
    """行号只在文件格式化时可用；单行档给 `-`。"""
    if not document.formatted:
        return "-"
    return f"L{element.line}–L{element.end_line}"


def parent_chain(element: Element, anchors: dict[int, str], keep: int = 2) -> list[str]:
    """父链只保留最近 `keep` 层——再往上是页面根容器，对定位没有增量信息。"""
    chain: list[str] = []
    current = element.parent
    while current is not None:
        chain.append(anchors[id(current)])
        current = current.parent
    chain.reverse()
    if len(chain) > keep:
        return ["…"] + chain[-keep:]
    return chain


def summarize(texts: list[str], limit: int = 3) -> str:
    picked = [truncate(text) for text in texts[:limit]]
    if len(texts) > limit:
        picked.append("…")
    return " / ".join(picked) if picked else "（无文案）"


def truncate(text: str, limit: int = SUMMARY_TEXT_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_chain(items: list[str]) -> str:
    return " › ".join(item if item == "…" else f"`{item}`" for item in items) or "—"


def map_elements_to_blocks(blocks: list[Element], anchors: dict[int, str]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for block in blocks:
        anchor = anchors[id(block)]
        for node in iter_subtree(block):
            mapping[id(node)] = anchor
    return mapping


# --------------------------------------------------------------------------- #
# 抽取汇总
# --------------------------------------------------------------------------- #


def extract(path: Path, token_mode: str, max_nodes: int, min_pattern_nodes: int, min_instances: int) -> dict:
    document = parse_document(path)
    tokens = classify_classes(document, token_mode)
    anchors = build_anchors(document, tokens.token_classes)
    blocks = split_blocks(document, max_nodes)
    block_map = map_elements_to_blocks(blocks, anchors)
    assets = collect_assets(document)
    return {
        "document": document,
        "tokens": tokens,
        "anchors": anchors,
        "blocks": block_records(document, blocks, anchors, max_nodes),
        "max_nodes": max_nodes,
        "block_map": block_map,
        "literals": collect_literals(document),
        "assets": assets,
        "prototype_fingerprint": prototype_fingerprint(document, assets),
        "content": collect_texts(document, block_map),
        "inventory": find_repeated_patterns(document, min_pattern_nodes, min_instances),
        "coverage_gaps": detect_coverage_gaps(document.source, document.other_rules),
    }


def stats(result: dict) -> dict:
    document: Document = result["document"]
    tokens: TokenSet = result["tokens"]
    literals = result["literals"]
    assets = result["assets"]
    content = result["content"]
    inventory = result["inventory"]
    return {
        "file": document.path.name,
        "chars": document.char_count,
        "lines": document.line_count,
        "avg_line_length": round(document.avg_line_length, 1),
        "formatted": document.formatted,
        "doc_hash": document.doc_hash,
        "dom_css_sha256": document.dom_css_sha256,
        "prototype_fingerprint": result["prototype_fingerprint"],
        "css_rules": len(document.rules),
        "class_rules": len(document.class_rules),
        "token_mode": tokens.mode,
        "token_classes": len(tokens.tokens),
        "layout_classes": len(tokens.layout_classes),
        "colors": len(literals["颜色"]),
        "font_sizes": len(literals["字号"]),
        "line_heights": len(literals["行高"]),
        "assets": len(assets),
        "assets_missing": sum(1 for item in assets if item["missing"]),
        "element_nodes": len(document.elements),
        "void_nodes": sum(document.void_counts.values()),
        "text_nodes": content["total_nodes"],
        "text_unique": len(content["unique"]),
        "text_static": len(content["static"]),
        "text_dynamic": len(content["dynamic"]),
        "blocks": len(result["blocks"]),
        "block_max_nodes": max((item["nodes"] for item in result["blocks"]), default=0),
        "patterns": len(inventory["patterns"]),
        "pattern_covered_nodes": inventory["covered_nodes"],
        "pattern_coverage_pct": round(100 * inventory["coverage"], 1),
        "coverage_gaps": result["coverage_gaps"],
    }


# --------------------------------------------------------------------------- #
# 机器可读设计事实
# --------------------------------------------------------------------------- #


def element_fact(element: Element) -> dict:
    """Return the exact shape emitted by collect_restore_facts.js for R1."""
    return {
        "tag": element.tag,
        "classes": sorted(set(element.classes)),
        "texts": list(element.texts),
        "children": [element_fact(child) for child in element.children],
    }


def design_facts_payload(result: dict) -> dict:
    """Stable Requirement-level facts consumed by restore contracts."""
    document: Document = result["document"]
    tokens: TokenSet = result["tokens"]
    token_by_name = {item["name"]: item for item in tokens.tokens}
    blocks: list[dict] = []
    for record in result["blocks"]:
        element: Element = record["element"]
        nodes = list(iter_subtree(element))
        block_token_names = sorted(
            {
                class_name
                for node in nodes
                for class_name in node.classes
                if class_name in token_by_name
            }
        )
        block_layout_classes = sorted(
            {
                class_name
                for node in nodes
                for class_name in node.classes
                if class_name in document.class_rules
                and class_name not in tokens.token_classes
            }
        )
        static_texts = []
        for node in nodes:
            for text in node.texts:
                if classify_text(text)[0] == "静态标签" and text not in static_texts:
                    static_texts.append(text)
        blocks.append(
            {
                "anchor": record["anchor"],
                "content_hash": record["hash"],
                "content_sha256": hashlib.sha256(
                    serialize_subtree(element).encode("utf-8")
                ).hexdigest(),
                "lines": record["lines"],
                "nodes": record["nodes"],
                "structure": element_fact(element),
                "static_texts": static_texts,
                "design_tokens": [
                    {
                        "name": name,
                        "property": token_by_name[name]["property"],
                        "value": token_by_name[name]["value"],
                    }
                    for name in block_token_names
                ],
                "layout_declarations": {
                    name: [
                        {"property": prop, "value": value}
                        for prop, value in document.class_rules[name]
                    ]
                    for name in block_layout_classes
                },
            }
        )

    payload = {
        "schema_version": 2,
        "source_file": document.path.name,
        "prototype_fingerprint": result["prototype_fingerprint"],
        "dom_css": {
            "legacy_doc_hash": document.doc_hash,
            "legacy_sha256": document.legacy_dom_css_sha256,
            "sha256": document.dom_css_sha256,
        },
        "resources": [
            {
                "url": item["url"],
                "status": item["status"],
                "missing": item["missing"],
                "remote": item["remote"],
                "content_sha256": item["content_sha256"],
            }
            for item in result["assets"]
        ],
        "design_tokens": [
            {
                "name": item["name"],
                "property": item["property"],
                "value": item["value"],
                "usage": item["usage"],
                "source": item["source"],
            }
            for item in tokens.tokens
        ],
        "static_texts": [
            {
                "text": item["text"],
                "count": item["count"],
                "blocks": item["blocks"],
            }
            for item in result["content"]["static"]
        ],
        "layout_declarations": {
            name: [
                {"property": prop, "value": value}
                for prop, value in document.class_rules[name]
            ]
            for name in sorted(tokens.layout_classes)
        },
        "coverage_gaps": result["coverage_gaps"],
        "blocks": blocks,
    }
    payload["facts_sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return payload


def render_design_facts(result: dict) -> str:
    return json.dumps(
        design_facts_payload(result),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


# --------------------------------------------------------------------------- #
# 产物渲染
# --------------------------------------------------------------------------- #


GENERATED_NOTE = (
    "> 由 `scripts/extract_design_spec.py` 确定性生成；文档哈希一致时保持只读，"
    "哈希变化时由下一次抽取重写。"
)
DOCUMENT_HASH_RE = re.compile(r"^> 文档哈希：`([0-9a-f]{8})`", re.M)


def provenance_lines(document: Document) -> list[str]:
    shape = "已格式化（行号可用）" if document.formatted else "单行/压缩（行号失效，锚点不带行号）"
    return [
        GENERATED_NOTE,
        f"> 来源：`{document.path.name}` — {document.char_count} 字符 / {document.line_count} 行 / "
        f"平均 {document.avg_line_length:.0f} 字符每行 / {shape}",
        f"> 文档哈希：`{document.doc_hash}`（归一化 DOM+CSS，重新格式化文件不会改变它）",
    ]


def render_design_tokens(result: dict) -> str:
    document: Document = result["document"]
    tokens: TokenSet = result["tokens"]
    literals = result["literals"]
    assets = result["assets"]

    lines = ["# Design Tokens", ""]
    lines += provenance_lines(document)
    lines.append("")
    lines.append(
        f"抽取模式：`{tokens.mode}` — "
        + (
            "命中生成器的 `_commonN` 共享类约定，token 直接取自共享类。"
            if tokens.mode == "shared-class"
            else "未命中 `_commonN` 约定，退化为字面量频次统计（值被 ≥2 个类引用才算 token）。"
        )
    )
    lines.append("")
    lines.append("## 抽取覆盖")
    lines.append("")
    gaps = result["coverage_gaps"]
    if gaps:
        lines.append(
            "**本表不完整。** 下列样式来源在本抽取器的能力边界之外（边界是「内联 `<style>` 里的单类选择器」）。"
            "每条都必须登记进 `dev-baseline.md / 已知缺口` 并在 Phase A 确认门里说明，"
            "否则受影响的维度会以 `未见` 的形式从冻结基线里消失。"
        )
        lines.append("")
        lines.append("| 缺口 | 数量 | 影响 | 明细 |")
        lines.append("| --- | --- | --- | --- |")
        for gap in gaps:
            lines.append(
                f"| {gap['kind']} | {gap['count']} | {gap['impact']} | "
                + "；".join(f"`{item}`" for item in gap["detail"])
                + " |"
            )
    else:
        lines.append("无缺口：原型的全部样式来源都在抽取范围内，本表可作为 R3 期望值的完整出处。")
    lines.append("")
    lines.append("## 二分判据")
    lines.append("")
    lines.append("- **共享类 → design tokens**：单属性且被 ≥2 个元素引用。本表就是它们，可直接对照仓内 token。")
    lines.append("- **具名类 → 逐元素布局值**：属性以 margin/width/height/padding 为主，一次性尺寸与位置，**不进本表**，逐区块写在区块规格里。")
    lines.append("- 命名与仓内样式/token `PATTERN-*` 的映射**不在本层做**（本产物 requirement 级复用，不绑定某个仓的快照）。")
    lines.append("")
    lines.append(
        f"- 类规则合计 {len(document.class_rules)} 条 = **{len(tokens.tokens)} 个 token 类** "
        f"+ **{len(tokens.layout_classes)} 个布局类**；另有 {len(document.other_rules)} 条非类选择器规则"
        + (f"（{'、'.join('`' + rule.selector + '`' for rule in document.other_rules[:4])}）" if document.other_rules else "")
        + "。"
    )
    lines.append("")

    lines.append(f"## Token 表（{len(tokens.tokens)} 项）")
    lines.append("")
    grouped = group_tokens(tokens.tokens)
    for group_name, items in grouped:
        lines.append(f"### {group_name}（{len(items)} 项）")
        lines.append("")
        lines.append("| Token 类 | 属性 | 值 | 引用元素数 |")
        lines.append("| --- | --- | --- | --- |")
        for item in items:
            lines.append(
                f"| `{item['name']}` | `{item['property']}` | `{item['value']}` | {item['usage']} |"
            )
        lines.append("")

    if tokens.rejected:
        lines.append(f"### 落选的共享类候选（{len(tokens.rejected)} 项）")
        lines.append("")
        lines.append("| 候选 | 落选原因 |")
        lines.append("| --- | --- |")
        for name, reason in tokens.rejected[:20]:
            lines.append(f"| `{name}` | {reason} |")
        if len(tokens.rejected) > 20:
            lines.append(f"| … | 另有 {len(tokens.rejected) - 20} 项 |")
        lines.append("")

    lines.append("## 去重字面量（全稿，含具名类）")
    lines.append("")
    lines.append("统计口径是「声明中出现的次数」，用于交叉核对 token 表的完整性。")
    lines.append("")
    lines.append("| 维度 | 去重数量 | 取值（值 ×出现次数） |")
    lines.append("| --- | --- | --- |")
    for dimension in ("颜色", "字号", "行高", "字重", "圆角", "阴影"):
        values = literals[dimension]
        rendered = "、".join(f"`{value}` ×{count}" for value, count in values) or "—"
        lines.append(f"| {dimension} | {len(values)} | {rendered} |")
    for dimension in ("间距", "尺寸"):
        values = literals[dimension]
        top = "、".join(f"`{value}` ×{count}" for value, count in values[:6])
        suffix = f"；另有 {len(values) - 6} 个低频值（逐元素噪声，完整值见区块规格）" if len(values) > 6 else ""
        lines.append(f"| {dimension} | {len(values)} | {top or '—'}{suffix} |")
    lines.append("")

    missing = [item for item in assets if item["missing"]]
    lines.append(f"## 资源引用（{len(assets)} 项，缺失 {len(missing)} 项）")
    lines.append("")
    if missing:
        lines.append(
            f"**资源缺失降级项**：`{document.path.parent.name}/assets/` 下有 {len(missing)} 个引用取不到文件。"
            "原型侧截图会缺这些图标，Step ② 的截图对照须标注「原型侧图标缺失，R1 的图标类元素不作差异判定」。"
        )
        lines.append("")
    lines.append("| 资源 | 状态 | 引用类 | 引用元素数 |")
    lines.append("| --- | --- | --- | --- |")
    for item in assets:
        state = "**缺失**" if item["missing"] else ("远程" if item["remote"] else "存在")
        owners = "、".join(f"`.{name}`" for name in item["classes"][:3])
        if len(item["classes"]) > 3:
            owners += f" 等 {len(item['classes'])} 个"
        lines.append(f"| `{item['url']}` | {state} | {owners} | {item['elements']} |")
    lines.append("")
    return "\n".join(lines)


def group_tokens(tokens: list[dict]) -> list[tuple[str, list[dict]]]:
    remaining = list(tokens)
    grouped: list[tuple[str, list[dict]]] = []
    for group_name, props in PROPERTY_GROUPS:
        items = [item for item in remaining if item["property"] in props]
        if items:
            grouped.append((group_name, sorted(items, key=lambda item: (item["property"], -item["usage"]))))
        remaining = [item for item in remaining if item["property"] not in props]
    if remaining:
        grouped.append(("其他", sorted(remaining, key=lambda item: (item["property"], -item["usage"]))))
    return grouped


def render_interface_inventory(result: dict) -> str:
    document: Document = result["document"]
    inventory = result["inventory"]
    blocks = result["blocks"]
    anchors = result["anchors"]

    lines = ["# Interface Inventory", ""]
    lines += provenance_lines(document)
    lines.append("")
    lines.append(
        f"节点：{len(document.elements)} 个元素节点"
        + (f"（另有 {sum(document.void_counts.values())} 个空元素，不计入结构签名）" if document.void_counts else "")
        + f"；区块 {len(blocks)} 个；重复结构模式 {len(inventory['patterns'])} 种，"
        f"覆盖 {inventory['covered_nodes']} 节点 = {100 * inventory['coverage']:.0f}%。"
    )
    if inventory["variant_nodes"]:
        lines.append("")
        lines.append(
            f"另有 {inventory['variant_nodes']} 节点属于已收模式的**变体候选**（同变体族、结构不完全相同），"
            "逐条列在各模式下，未计入上面的覆盖率。"
        )
    lines.append("")
    lines.append("## 区块索引")
    lines.append("")
    lines.append(
        "锚点主体是 class 名：取该元素引用次数最少的**非 token** class；该 class 在全稿出现多次时加 "
        "`[i]`，i 是它在 DOM 序中的出现序号（第 i 个带这个 class 的元素），可用 `rg` 复算。"
        "根元素没有非 token class 时，以 `@ancestor(...)` / `@path(...)` 记录最近具名后代或祖先的结构路径，"
        "不退回语义标签。"
        + ("行号可用，附 `L起–L止`。" if document.formatted else "本文件为单行档，行号失效，一律记 `-`。")
    )
    lines.append("")
    lines.append("单区块切片按需取：`python3 scripts/extract_design_spec.py block <html> --anchor <锚点>`。")
    lines.append("")
    lines.append(
        f"以下是**确定性候选段**（节点上限 {result['max_nodes']}，`*` 表示超限的扁平容器，切碎无意义故整块给出）。"
        "把候选段归并成「一屏可截」的页面区块是 `extract-prototype` 的职责。"
    )
    lines.append("")
    lines.append("| 锚点 | 行号 | 节点数 | 文本节点 | 内容哈希 | 父链 | 文案摘要 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for record in blocks:
        nodes = f"{record['nodes']}*" if record["oversize"] else str(record["nodes"])
        lines.append(
            f"| `{record['anchor']}` | {record['lines']} | {nodes} | {record['text_nodes']} | "
            f"`{record['hash']}` | {render_chain(record['parents'])} | {record['summary']} |"
        )
    lines.append("")
    lines.append(
        "内容哈希是 requirement 级缓存的时效校验单位：只有哈希变了的区块需要重抽，其余直接复用。"
        "哈希输入是归一化的 `tag + class + 文案`，与空白格式无关。"
    )
    lines.append("")

    lines.append("## 重复结构模式")
    lines.append("")
    lines.append(
        "签名忽略文案，只看 `tag[class]` 骨架，逐层嵌套；只取**不互相嵌套的顶层模式**。"
        "编号 `IC-nn` 是抽取序号（按覆盖节点数降序），**不是组件名**——命名与变体归并由 `extract-prototype` 审定。"
    )
    lines.append("")
    for pattern in inventory["patterns"]:
        first: Element = pattern["instances"][0]
        instance_anchors = [anchors[id(instance)] for instance in pattern["instances"]]
        block_anchors: list[str] = []
        for instance in pattern["instances"]:
            anchor = result["block_map"].get(id(instance), "-")
            if anchor not in block_anchors:
                block_anchors.append(anchor)
        sample_texts: list[str] = []
        for instance in pattern["instances"][:3]:
            texts = [text for node in iter_subtree(instance) for text in node.texts]
            sample_texts.append(summarize(texts, limit=4))
        lines.append(f"### {pattern['code']}（{pattern['count']} 实例 × {pattern['size']} 节点 = {pattern['covered']} 节点）")
        lines.append("")
        lines.append("| 项 | 值 |")
        lines.append("| --- | --- |")
        lines.append(f"| 根元素 | `{first.tag}` `.{'.'.join(first.classes)}` |")
        lines.append(f"| 签名哈希 | `{short_hash(pattern['signature'])}` |")
        lines.append(f"| 实例锚点 | {'、'.join('`' + item + '`' for item in instance_anchors[:8])}"
                     + (f" 等 {pattern['count']} 个" if pattern["count"] > 8 else "") + " |")
        lines.append(f"| 所在区块 | {'、'.join('`' + item + '`' for item in block_anchors[:6])}"
                     + (f" 等 {len(block_anchors)} 处" if len(block_anchors) > 6 else "") + " |")
        if pattern.get("merge_candidates"):
            lines.append(
                f"| 候选归并 | 与 {'、'.join('`' + code + '`' for code in pattern['merge_candidates'])} "
                "同属一个变体族（class 仅差实例序号），待判定是否为同一组件的变体 |"
            )
        if pattern.get("variants"):
            variant_anchors = [anchors[id(element)] for element in pattern["variants"]]
            lines.append(
                f"| 变体候选实例 | {'、'.join('`' + item + '`' for item in variant_anchors[:6])}"
                + (f" 等 {len(variant_anchors)} 个" if len(variant_anchors) > 6 else "")
                + "（同变体族、结构不完全相同，未计入本模式覆盖） |"
            )
        lines.append("")
        lines.append("骨架（忽略文案，token 类折叠为计数）：")
        lines.append("")
        lines.append("```")
        lines.extend(render_skeleton(result, first))
        lines.append("```")
        lines.append("")
        lines.append("逐实例文案样例：")
        for index, sample in enumerate(sample_texts, start=1):
            lines.append(f"- 实例 {index}：{sample}")
        lines.append("")
    return "\n".join(lines)


def render_skeleton(result: dict, element: Element, max_lines: int = 20) -> list[str]:
    """结构骨架：只有 tag + 具名 class + token 计数，同签名的相邻兄弟折叠成 `×n`。"""
    token_names = result["tokens"].token_classes
    output: list[str] = []

    def label(node: Element) -> str:
        named = [name for name in node.classes if name not in token_names]
        text = f"{node.tag}." + ".".join(named) if named else node.tag
        extra = len(node.classes) - len(named)
        return text + (f" (+{extra} token)" if extra else "")

    def walk(node: Element, depth: int, repeat: int = 1) -> None:
        if len(output) >= max_lines:
            return
        output.append("  " * depth + label(node) + (f" ×{repeat}" if repeat > 1 else ""))
        index = 0
        while index < len(node.children):
            child = node.children[index]
            span = 1
            while (
                index + span < len(node.children)
                and node.children[index + span].signature == child.signature
            ):
                span += 1
            walk(child, depth + 1, span)
            index += span

    walk(element, 0)
    if len(output) >= max_lines:
        output.append(f"…（骨架在 {max_lines} 行处截断）")
    return output


def render_content_inventory(result: dict) -> str:
    document: Document = result["document"]
    content = result["content"]

    lines = ["# Content Inventory", ""]
    lines += provenance_lines(document)
    lines.append("")
    lines.append(
        f"{content['total_nodes']} 个文本节点去重后 **{len(content['unique'])} 条**："
        f"静态标签 {len(content['static'])} 条、动态数据位 {len(content['dynamic'])} 条。"
    )
    if document.void_counts.get("br"):
        lines.append("")
        lines.append(f"注：正文含 {document.void_counts['br']} 个 `<br>`，被它切开的文段计为独立文本节点。")
    lines.append("")
    lines.append("## 占位符判据")
    lines.append("")
    lines.append("命中任一条即判为**动态数据位**，否则为静态标签：")
    lines.append("")
    lines.append("| 编号 | 判据 | 命中样例 |")
    lines.append("| --- | --- | --- |")
    lines.append("| P1 | 含连续 2 个及以上大写 `X` 掩码 | `XX客户名称`、`X,XXX个`、`XX%`、`XXXX` |")
    lines.append("| P2 | 某个空白分隔片段整体是数值（可带千分位、小数、单位、尾部省略号） | `2,000`、`-888次`、`28%`、`智能光伏(业主) 38%` |")
    lines.append("| P3 | 含日期形态 | `2026/03/26`、`2026年2月28日` |")
    lines.append("| P4 | 整条只由省略号组成 | `…` |")
    lines.append("")
    lines.append("## 静态标签（可作 R2 文案期望值）")
    lines.append("")
    lines.append("| 文案 | 次数 | 所在区块 |")
    lines.append("| --- | --- | --- |")
    for item in content["static"]:
        blocks = "、".join(f"`{anchor}`" for anchor in item["blocks"][:3])
        if len(item["blocks"]) > 3:
            blocks += f" 等 {len(item['blocks'])} 处"
        lines.append(f"| {item['text']} | {item['count']} | {blocks} |")
    lines.append("")
    lines.append("## 动态数据位（**不得作为 R2 文案期望值**）")
    lines.append("")
    lines.append("下游只能拿「格式模板」列做格式断言（位数、单位、千分位），不得把「样例值」写成期望文案。")
    lines.append("")
    lines.append("| 样例值 | 次数 | 判据 | 格式模板 | 所在区块 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in content["dynamic"]:
        blocks = "、".join(f"`{anchor}`" for anchor in item["blocks"][:3])
        if len(item["blocks"]) > 3:
            blocks += f" 等 {len(item['blocks'])} 处"
        lines.append(
            f"| {item['text']} | {item['count']} | {item['rule']} | `{format_template(item['text'])}` | {blocks} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_block_slice(result: dict, anchor: str) -> str:
    document: Document = result["document"]
    tokens: TokenSet = result["tokens"]
    record = find_block(result, anchor)
    element: Element = record["element"]

    token_by_name = {item["name"]: item for item in tokens.tokens}
    used_tokens: dict[str, int] = {}
    used_layout: dict[str, int] = {}
    for node in iter_subtree(element):
        for name in node.classes:
            if name in token_by_name:
                used_tokens[name] = used_tokens.get(name, 0) + 1
            elif name in document.class_rules:
                used_layout[name] = used_layout.get(name, 0) + 1
            else:
                used_layout.setdefault(name, 0)
                used_layout[name] += 1

    assets_by_class: dict[str, list[dict]] = {}
    for item in result["assets"]:
        for name in item["classes"]:
            assets_by_class.setdefault(name, []).append(item)

    lines = [f"# 区块切片 `{record['anchor']}`", ""]
    lines += provenance_lines(document)
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("| --- | --- |")
    lines.append(f"| 锚点 | `{record['anchor']}`（`{element.tag}` `.{'.'.join(element.classes)}`） |")
    lines.append(f"| 行号 | {record['lines']}{'' if document.formatted else '（单行档，行号失效）'} |")
    lines.append(f"| 内容哈希 | `{record['hash']}` |")
    lines.append(f"| 节点数 | {record['nodes']}（文本节点 {record['text_nodes']}） |")
    lines.append(f"| 父链 | {render_chain(record['parents'])} |")
    lines.append("")

    lines.append("## 引用 token")
    lines.append("")
    if used_tokens:
        lines.append("| Token 类 | 属性 | 值 | 本区块引用数 |")
        lines.append("| --- | --- | --- | --- |")
        for name, count in sorted(used_tokens.items(), key=lambda item: (-item[1], item[0])):
            item = token_by_name[name]
            lines.append(f"| `{name}` | `{item['property']}` | `{item['value']}` | {count} |")
    else:
        lines.append("（本区块未引用任何 token 类）")
    lines.append("")

    lines.append("## 逐元素布局值")
    lines.append("")
    lines.append("| 具名类 | 本区块引用数 | 声明 |")
    lines.append("| --- | --- | --- |")
    for name, count in sorted(used_layout.items(), key=lambda item: (-item[1], item[0])):
        declarations = document.class_rules.get(name)
        if not declarations:
            lines.append(f"| `{name}` | {count} | **无 CSS 规则** |")
            continue
        rendered = "；".join(f"`{prop}: {value}`" for prop, value in declarations)
        lines.append(f"| `{name}` | {count} | {rendered} |")
    lines.append("")

    lines.append("## 结构与文案")
    lines.append("")
    lines.append("```")
    lines.extend(render_tree(document, element, result))
    lines.append("```")
    lines.append("")

    block_assets: list[dict] = []
    for name in list(used_tokens) + list(used_layout):
        for item in assets_by_class.get(name, []):
            if item not in block_assets:
                block_assets.append(item)
    lines.append("## 资源引用")
    lines.append("")
    if block_assets:
        for item in sorted(block_assets, key=lambda entry: entry["url"]):
            state = "**缺失**" if item["missing"] else ("远程" if item["remote"] else "存在")
            lines.append(f"- `{item['url']}` — {state}（`{'`、`'.join('.' + name for name in item['classes'][:3])}`）")
        if any(item["missing"] for item in block_assets):
            lines.append("")
            lines.append("资源缺失：原型侧截图会缺这些图标，R1 的图标类元素不作差异判定。")
    else:
        lines.append("（本区块无资源引用）")
    lines.append("")

    lines.append("## 文案分类")
    lines.append("")
    static_items: list[tuple[str, str]] = []
    dynamic_items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for node in iter_subtree(element):
        for text in node.texts:
            if text in seen:
                continue
            seen.add(text)
            category, rule_id = classify_text(text)
            (static_items if category == "静态标签" else dynamic_items).append((text, rule_id))
    lines.append("- 静态标签（可作 R2 期望值）：" + ("、".join(f"「{text}」" for text, _ in static_items) or "无"))
    lines.append(
        "- 动态数据位（**不得作为 R2 期望值**，只给格式模板）："
        + (
            "、".join(f"`{format_template(text)}`（{rule_id}，样例 {text}）" for text, rule_id in dynamic_items)
            or "无"
        )
    )
    lines.append("")
    lines.append("## 静态设计稿的固有缺口")
    lines.append("")
    lines.append("R4 状态样式（hover/focus/disabled/loading）与 R5 空态在静态设计稿里**不存在**，区块规格须写「未见」，不得推断。")
    lines.append("")
    return "\n".join(lines)


def render_tree(document: Document, element: Element, result: dict, max_lines: int = 400) -> list[str]:
    """区块结构树。折叠 token 类与相邻重复骨架，控制语义区块切片体积。"""
    token_names = result["tokens"].token_classes
    output: list[str] = []

    def walk(node: Element, depth: int, repeat: int = 1) -> None:
        if len(output) >= max_lines:
            return
        named = [name for name in node.classes if name not in token_names]
        token_count = len(node.classes) - len(named)
        label = f"{node.tag}." + ".".join(named) if named else node.tag
        if token_count:
            label += f" (+{token_count} token)"
        if repeat > 1:
            label += f" ×{repeat}"
        text = " ".join(node.texts)
        suffix = f"  “{truncate(text, 40)}”" if text else ""
        position = f"  {line_range(document, node)}" if document.formatted and node.size > 1 else ""
        output.append("  " * depth + label + suffix + position)
        index = 0
        while index < len(node.children):
            child = node.children[index]
            span = 1
            while (
                index + span < len(node.children)
                and node.children[index + span].signature == child.signature
            ):
                span += 1
            walk(child, depth + 1, span)
            index += span

    walk(element, 0)
    if len(output) >= max_lines:
        output.append(f"…（结构树在 {max_lines} 行处截断，区块过大，建议按子锚点再切）")
    return output


def find_block(result: dict, anchor: str) -> dict:
    wanted = anchor.strip()
    if not wanted.startswith((".", "@")):
        wanted = "." + wanted
    for record in result["blocks"]:
        if record["anchor"] == wanted:
            return record

    # `extract-prototype` 可以把相邻候选段归到共同父级；因此 block 接受任意元素锚点，
    # 不局限于 interface-inventory 里的确定性候选段。
    anchors = result["anchors"]
    document: Document = result["document"]
    for element in document.elements:
        if anchors[id(element)] == wanted:
            return block_records(document, [element], anchors, result["max_nodes"])[0]

    # 允许省略 `[i]`：唯一命中时照样接受，多处命中时报可选值。
    matched_elements = [
        element
        for element in document.elements
        if anchors[id(element)].startswith(wanted + "[")
    ]
    matches = [
        block_records(document, [element], anchors, result["max_nodes"])[0]
        for element in matched_elements
    ]
    if len(matches) == 1:
        return matches[0]
    available = "、".join(record["anchor"] for record in result["blocks"])
    if matches:
        raise SystemExit(
            f"锚点 `{anchor}` 命中多个区块：{'、'.join(record['anchor'] for record in matches)}；请补出现序号。"
        )
    raise SystemExit(f"锚点 `{anchor}` 不在区块索引里。可用锚点：{available}")


# --------------------------------------------------------------------------- #
# 懒视觉缓存
# --------------------------------------------------------------------------- #


def parse_viewport(value: str) -> dict[str, int]:
    match = re.fullmatch(r"(\d+)[xX×](\d+)", value.strip())
    if not match:
        raise ValueError("viewport 必须是 WIDTHxHEIGHT，如 1440x900")
    width, height = (int(item) for item in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError("viewport 宽高必须大于 0")
    return {"width": width, "height": height}


def visual_cache_identity(
    prototype_fingerprint_value: str,
    anchor: str,
    viewport: dict[str, int],
    dpr: float,
    browser_engine: str,
    browser_version: str,
    font_fingerprint: str,
) -> dict:
    return {
        "prototype_fingerprint": prototype_fingerprint_value,
        "block_anchor": anchor,
        "viewport": viewport,
        "dpr": float(dpr),
        "browser": {
            "engine": browser_engine,
            "version": browser_version,
        },
        "font_fingerprint": font_fingerprint,
    }


def visual_cache_fingerprint(identity: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def visual_yellow_count(report_path: Path, anchor: str) -> int:
    """Count only YELLOW rules that explicitly require visual evidence at anchor."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    entries = report.get("entries")
    if not isinstance(entries, list):
        raise ValueError("restore report 缺 entries 数组")
    count = 0
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "yellow":
            continue
        if "visual" not in entry.get("required_layers", []):
            continue
        source = entry.get("contract_source", {}).get("design_fact_source", {})
        if isinstance(source, dict) and source.get("anchor") == anchor:
            count += 1
    return count


def visual_cache_status(
    facts_path: Path,
    design_spec_dir: Path,
    anchor: str,
    viewport_value: str,
    dpr: float,
    browser_engine: str,
    browser_version: str,
    font_fingerprint: str,
    yellow_count: int,
    png_path: Path | None,
) -> dict:
    """Query or populate an immutable visual baseline cache.

    With zero YELLOW visual rules the function returns ``not-needed`` and never
    creates a directory. On a miss without ``png_path`` it returns
    ``needs-capture`` so the caller can take exactly one browser screenshot.
    """
    if yellow_count < 0:
        raise ValueError("yellow-count 不能为负数")
    if yellow_count == 0:
        return {
            "status": "not-needed",
            "reason": "没有 YELLOW 视觉项；机器可检项目不截图",
        }

    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    prototype = facts.get("prototype_fingerprint")
    if not isinstance(prototype, str) or not re.fullmatch(r"[0-9a-f]{64}", prototype):
        raise ValueError("design-facts.json 缺合法 prototype_fingerprint")
    if not any(block.get("anchor") == anchor for block in facts.get("blocks", [])):
        raise ValueError(f"区块锚点不在 design-facts.json：{anchor}")

    viewport = parse_viewport(viewport_value)
    identity = visual_cache_identity(
        prototype,
        anchor,
        viewport,
        dpr,
        browser_engine,
        browser_version,
        font_fingerprint,
    )
    fingerprint = visual_cache_fingerprint(identity)
    target = design_spec_dir / "visual-baseline" / fingerprint
    manifest_path = target / "manifest.json"
    cached_png = target / "prototype.png"

    expected_manifest = {
        "schema_version": 1,
        "cache_fingerprint": fingerprint,
        **identity,
        "png": "prototype.png",
    }
    if target.exists():
        if not manifest_path.is_file() or not cached_png.is_file():
            raise ValueError(f"视觉缓存目录不完整，拒绝覆盖：{target}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(manifest.get(key) != value for key, value in expected_manifest.items()):
            raise ValueError(f"视觉缓存 manifest 与缓存键不一致，拒绝覆盖：{target}")
        cached_body = cached_png.read_bytes()
        if not cached_body.startswith(PNG_SIGNATURE):
            raise ValueError(f"视觉缓存 PNG 无效：{cached_png}")
        if manifest.get("png_sha256") != hashlib.sha256(cached_body).hexdigest():
            raise ValueError(f"视觉缓存 PNG 与 manifest 哈希不一致：{cached_png}")
        return {
            "status": "hit",
            "cache_fingerprint": fingerprint,
            "path": str(target),
        }

    if png_path is None:
        return {
            "status": "needs-capture",
            "cache_fingerprint": fingerprint,
            "path": str(target),
            "reason": "存在 YELLOW 视觉项且缓存未命中；请截原型当前区块",
        }
    body = png_path.read_bytes()
    if not body.startswith(PNG_SIGNATURE):
        raise ValueError(f"--png 不是有效 PNG：{png_path}")

    target.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(png_path, cached_png)
    expected_manifest["png_sha256"] = hashlib.sha256(body).hexdigest()
    manifest_path.write_text(
        json.dumps(expected_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "created",
        "cache_fingerprint": fingerprint,
        "path": str(target),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


ARTIFACTS = (
    ("design-tokens.md", render_design_tokens),
    ("interface-inventory.md", render_interface_inventory),
    ("content-inventory.md", render_content_inventory),
)


def write_artifacts(result: dict, out_dir: Path) -> list[str]:
    """写三份 Markdown 与 design-facts.json。

    Markdown may contain human naming amendments and is preserved while the legacy
    document hash matches. JSON is fully deterministic and is rewritten only when
    its canonical content changes.
    """
    document: Document = result["document"]
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for filename, renderer in ARTIFACTS:
        target = out_dir / filename
        body = renderer(result) + "\n"
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing == body:
                written.append(f"{filename}（无差异，未重写）")
                continue
            match = DOCUMENT_HASH_RE.search(existing)
            if match is None:
                raise SystemExit(
                    f"{target} 已存在但没有可识别的文档哈希；为避免覆盖未知内容，未写入。"
                )
            if match.group(1) == document.doc_hash:
                written.append(f"{filename}（文档哈希一致，保留现有文件）")
                continue
        target.write_text(body, encoding="utf-8")
        written.append(f"{filename}（{len(body)} 字符）")

    facts_target = out_dir / "design-facts.json"
    facts_body = render_design_facts(result)
    if facts_target.exists() and facts_target.read_text(encoding="utf-8") == facts_body:
        written.append("design-facts.json（无差异，未重写）")
    else:
        facts_target.write_text(facts_body, encoding="utf-8")
        written.append(f"design-facts.json（{len(facts_body)} 字符）")
    return written


def command_extract(args: argparse.Namespace) -> int:
    result = extract(
        Path(args.html).expanduser(),
        args.token_mode,
        args.block_max_nodes,
        args.min_pattern_nodes,
        args.min_instances,
    )
    summary = stats(result)
    written: list[str] = []
    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser()
        written = write_artifacts(result, out_dir)
    summary["written"] = written
    summary["out_dir"] = str(Path(args.out_dir).expanduser()) if args.out_dir else None

    gaps = result["coverage_gaps"]
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_summary(summary, result)
    if gaps and not args.acknowledge_coverage_gaps:
        print(
            "\n抽取覆盖不完整：上列缺口中的样式来源本抽取器读不到，直接开工会让 R3 / R4 / R6 "
            "在区块规格里退化为 `未见`，冻结基线随之漏项。\n"
            "先把每条缺口登记进「已知缺口」并在确认门里说明，再带 --acknowledge-coverage-gaps 重跑。",
            file=sys.stderr,
        )
        return EXIT_COVERAGE_GAPS
    return EXIT_OK


def print_summary(summary: dict, result: dict) -> None:
    document: Document = result["document"]
    print(f"file: {summary['file']}")
    print(
        f"shape: {summary['chars']} 字符 / {summary['lines']} 行 / 平均 {summary['avg_line_length']} 字符每行 / "
        + ("已格式化，锚点附行号" if summary["formatted"] else "单行档，锚点不附行号")
    )
    print(f"doc hash: {summary['doc_hash']}")
    print(f"prototype fingerprint: {summary['prototype_fingerprint']}")
    print(
        f"css: {summary['class_rules']} 类规则 = {summary['token_classes']} token 类 "
        f"+ {summary['layout_classes']} 布局类（模式 {summary['token_mode']}）"
    )
    print(
        f"literals: {summary['colors']} 色 / {summary['font_sizes']} 字号 / "
        f"{summary['line_heights']} 行高 / {summary['assets']} 资源"
        + (f"（缺失 {summary['assets_missing']}）" if summary["assets_missing"] else "")
    )
    print(
        f"nodes: {summary['element_nodes']} 元素节点"
        + (f" + {summary['void_nodes']} 空元素" if summary["void_nodes"] else "")
        + f"；文本节点 {summary['text_nodes']} → 去重 {summary['text_unique']}"
        f"（静态 {summary['text_static']} / 动态 {summary['text_dynamic']}）"
    )
    print(
        f"inventory: {summary['patterns']} 种顶层重复模式，覆盖 "
        f"{summary['pattern_covered_nodes']}/{summary['element_nodes']} 节点 = {summary['pattern_coverage_pct']}%"
    )
    gaps = summary.get("coverage_gaps") or []
    if gaps:
        print(f"coverage: {len(gaps)} 类缺口，抽取值不完整")
        for gap in gaps:
            print(f"  ! {gap['kind']}（{gap['count']}）：{gap['impact']}")
            for item in gap["detail"]:
                print(f"      {item}")
    else:
        print("coverage: 无缺口，全部样式来源均在抽取范围内")
    print(f"blocks: {summary['blocks']} 个，最大 {summary['block_max_nodes']} 节点")
    for record in result["blocks"]:
        print(
            f"  {record['anchor']}  {record['lines']}  {record['nodes']} 节点  "
            f"{record['hash']}  {record['summary']}"
        )
    if summary["written"]:
        print(f"written -> {summary['out_dir']}")
        for item in summary["written"]:
            print(f"  {item}")
    elif document is not None:
        print("dry run：未给 --out-dir，未落盘")


def command_block(args: argparse.Namespace) -> int:
    result = extract(
        Path(args.html).expanduser(),
        args.token_mode,
        args.block_max_nodes,
        args.min_pattern_nodes,
        args.min_instances,
    )
    body = render_block_slice(result, args.anchor) + "\n"
    if args.out:
        target = Path(args.out).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(f"written -> {target}（{len(body)} 字符）")
        return EXIT_OK
    print(body, end="")
    return EXIT_OK


def command_blocks(args: argparse.Namespace) -> int:
    """只列锚点与内容哈希，供 requirement 级缓存做时效校验。"""
    result = extract(
        Path(args.html).expanduser(),
        args.token_mode,
        args.block_max_nodes,
        args.min_pattern_nodes,
        args.min_instances,
    )
    document: Document = result["document"]
    payload = {
        "file": document.path.name,
        "doc_hash": document.doc_hash,
        "formatted": document.formatted,
        "blocks": [
            {
                "anchor": record["anchor"],
                "hash": record["hash"],
                "lines": record["lines"],
                "nodes": record["nodes"],
                "text_nodes": record["text_nodes"],
            }
            for record in result["blocks"]
        ],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"doc hash: {payload['doc_hash']}")
    for item in payload["blocks"]:
        print(f"{item['anchor']}\t{item['hash']}\t{item['lines']}\t{item['nodes']} 节点")
    return EXIT_OK


def command_visual_cache(args: argparse.Namespace) -> int:
    yellow_count = (
        visual_yellow_count(Path(args.report).expanduser(), args.anchor)
        if args.report
        else args.yellow_count
    )
    payload = visual_cache_status(
        Path(args.facts).expanduser(),
        Path(args.design_spec_dir).expanduser(),
        args.anchor,
        args.viewport,
        args.dpr,
        args.browser_engine,
        args.browser_version,
        args.font_fingerprint,
        yellow_count,
        Path(args.png).expanduser() if args.png else None,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return EXIT_OK


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("html", help="设计稿 HTML 文件路径")
    parser.add_argument(
        "--token-mode",
        choices=["auto", "shared", "literal"],
        default="auto",
        help="token 抽取模式：auto 命中 _commonN 约定走 shared，否则退化为 literal 字面量频次",
    )
    parser.add_argument(
        "--block-max-nodes",
        type=int,
        default=80,
        help="候选段节点目标上限；扁平容器或显式父级锚点可超出",
    )
    parser.add_argument("--min-pattern-nodes", type=int, default=2, help="重复结构模式的子树最小节点数")
    parser.add_argument("--min-instances", type=int, default=2, help="重复结构模式的最小实例数")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="产出三份全局产物（不给 --out-dir 则只打印统计）")
    add_common_arguments(extract_parser)
    extract_parser.add_argument("--out-dir", help="落盘目录，实际运行时取 <requirement-dir>/design-spec/")
    extract_parser.add_argument("--format", choices=["text", "json"], default="text")
    extract_parser.add_argument(
        "--acknowledge-coverage-gaps",
        action="store_true",
        help="已把覆盖缺口登记进「已知缺口」，不再以退出码 4 阻断",
    )

    block_parser = subparsers.add_parser("block", help="按任意可复算元素锚点吐出单个语义区块切片")
    add_common_arguments(block_parser)
    block_parser.add_argument("--anchor", required=True, help="区块锚点，如 `.page-box-0` 或 `.section[2]`")
    block_parser.add_argument("--out", help="写入文件而非打印到 stdout")

    blocks_parser = subparsers.add_parser("blocks", help="列出区块锚点与内容哈希，供缓存校验")
    add_common_arguments(blocks_parser)
    blocks_parser.add_argument("--format", choices=["text", "json"], default="text")

    visual_cache_parser = subparsers.add_parser(
        "visual-cache",
        help="仅在存在 YELLOW 视觉项时查询或写入不可变原型视觉缓存",
    )
    visual_cache_parser.add_argument("--facts", required=True, help="design-facts.json")
    visual_cache_parser.add_argument(
        "--design-spec-dir",
        required=True,
        help="<requirement-dir>/design-spec/",
    )
    visual_cache_parser.add_argument("--anchor", required=True)
    visual_cache_parser.add_argument("--viewport", required=True, help="如 1440x900")
    visual_cache_parser.add_argument("--dpr", type=float, required=True)
    visual_cache_parser.add_argument("--browser-engine", required=True)
    visual_cache_parser.add_argument("--browser-version", required=True)
    visual_cache_parser.add_argument("--font-fingerprint", required=True)
    visual_source = visual_cache_parser.add_mutually_exclusive_group(required=True)
    visual_source.add_argument(
        "--report",
        help="机器报告；自动只数本锚点 required_layers 含 visual 的 YELLOW",
    )
    visual_source.add_argument(
        "--yellow-count",
        type=int,
        help="兼容测试/底层调用；常规流程应使用 --report",
    )
    visual_cache_parser.add_argument(
        "--png",
        help="缓存未命中且已截图时给 PNG；查询命中时不需要",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            return command_extract(args)
        if args.command == "block":
            return command_block(args)
        if args.command == "blocks":
            return command_blocks(args)
        if args.command == "visual-cache":
            return command_visual_cache(args)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
