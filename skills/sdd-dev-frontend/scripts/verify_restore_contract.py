#!/usr/bin/env python3
"""Compile and execute frozen frontend restore contracts.

The verifier is intentionally standard-library only. Browser facts are collected by
``collect_restore_facts.js`` and passed back as JSON; screenshots are never required
for rules that can be decided statically or from structured render facts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_ERROR = 2
EXIT_NOT_GREEN = 3
CONTRACT_SCHEMA_VERSION = 2
ADAPTER_SCHEMA_VERSION = 1
RESULT_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 2

DIMENSIONS = {f"R{index}" for index in range(1, 7)}
CHECK_MODES = {
    "exact",
    "structure",
    "numeric",
    "color",
    "state",
    "overflow",
    "overlap",
    "clip",
    "visual",
}
LAYERS = {"static", "render", "visual"}
LOCATOR_PRIORITY = {"role": 0, "text": 1, "testid": 2, "css": 3}
DEFAULT_LAYERS = {
    "R1": ["render"],
    "R2": ["render"],
    "R3": ["static", "render"],
    "R4": ["static", "render"],
    "R5": ["render"],
    "R6": ["render"],
}
GENERATED_CLASS_RE = re.compile(
    r"(?:\.[A-Za-z_-]*[0-9a-fA-F]{8,}\b|\.[A-Za-z][\w-]*_[A-Za-z0-9]{6,}\b)"
)
CSS_NUMBER_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:px)?\s*$")
# 只匹配表格行的第一格，避免把「取证方式」列里提到的编号当成一行基线。
BASELINE_RULE_ID_RE = re.compile(r"^\|\s*`?(R[1-6]-\d+)`?\s*\|")


class ContractError(ValueError):
    """Raised when a machine-readable restore artifact is invalid."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_frozen_baseline(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    if "已冻结 ✅" not in body:
        raise ContractError("dev-baseline.md 尚未标记为已冻结，拒绝编译或执行契约")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"文件不存在：{path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"JSON 无法解析：{path}: {error}") from error


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == body:
        return
    path.write_text(body, encoding="utf-8")


def default_tolerance(check_mode: str) -> dict[str, float]:
    if check_mode in {"numeric", "overflow", "overlap", "clip"}:
        return {"css_px": 1.0}
    return {"css_px": 0.0}


def is_empty_expectation(payload: Any) -> bool:
    """`0` / `False` 是合法期望值，空容器与缺省不是。"""
    if payload is None:
        return True
    return isinstance(payload, (dict, list, tuple, str)) and len(payload) == 0


def validate_rule(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ContractError(f"第 {index} 条规则必须是对象")
    required = (
        "id",
        "baseline_id",
        "dimension",
        "block",
        "subject",
        "expected",
        "check_mode",
        "design_fact_source",
    )
    missing = [field for field in required if field not in raw]
    if missing:
        raise ContractError(f"规则 {raw.get('id', index)} 缺字段：{', '.join(missing)}")

    rule = dict(raw)
    rule_id = str(rule["id"]).strip()
    if not rule_id:
        raise ContractError(f"第 {index} 条规则 id 为空")
    dimension = str(rule["dimension"]).upper()
    if dimension not in DIMENSIONS:
        raise ContractError(f"规则 {rule_id} 的 dimension 必须是 R1–R6")
    check_mode = str(rule["check_mode"])
    if check_mode not in CHECK_MODES:
        raise ContractError(f"规则 {rule_id} 的 check_mode 不支持：{check_mode}")

    layers = rule.get("required_layers", DEFAULT_LAYERS[dimension])
    if not isinstance(layers, list) or not layers:
        raise ContractError(f"规则 {rule_id} 的 required_layers 必须是非空数组")
    unknown_layers = [layer for layer in layers if layer not in LAYERS]
    if unknown_layers:
        raise ContractError(f"规则 {rule_id} 含未知检查层：{unknown_layers}")
    if check_mode == "visual" and "visual" not in layers:
        raise ContractError(f"规则 {rule_id} 的 visual 模式必须要求 visual 层")
    if check_mode == "visual" and "render" in layers:
        # visual 模式的判定只能来自 visual-results；render 层对它恒判不通过，
        # 两者同时要求会让这条规则永远 RED，且报告里的原因指向渲染值，极难排查。
        raise ContractError(
            f"规则 {rule_id} 的 visual 模式不能同时要求 render 层：render 层无法判定 visual 模式"
        )
    if "static" in layers and not isinstance(rule.get("static_check"), dict):
        raise ContractError(f"规则 {rule_id} 要求 static 层但没有 static_check")

    # render 层是唯一拿 expected 做比对的层（static 走 static_check，visual 走 visual-results）。
    # 空期望值会让 numeric 产生不出差异项、overflow 家族取到 0，两种写法都无条件判绿——
    # 没有期望值就没有判据，必须在编译期挡住，不能等它在报告里自动染绿。
    if "render" in layers and is_empty_expectation(expected_for_layer(rule, "render")):
        raise ContractError(
            f"规则 {rule_id} 的 render 层 expected 为空：没有期望值就没有判据"
        )

    tolerance = rule.get("tolerance", default_tolerance(check_mode))
    if not isinstance(tolerance, dict):
        raise ContractError(f"规则 {rule_id} 的 tolerance 必须是对象")
    css_px = tolerance.get("css_px", 0)
    if not isinstance(css_px, (int, float)) or css_px < 0:
        raise ContractError(f"规则 {rule_id} 的 tolerance.css_px 必须是非负数")

    exemption = rule.get("frozen_exemption")
    if exemption is not None:
        if not isinstance(exemption, dict) or not exemption.get("id"):
            raise ContractError(f"规则 {rule_id} 的 frozen_exemption 缺 id")
        if exemption.get("frozen") is not True:
            raise ContractError(f"规则 {rule_id} 的豁免未冻结，不能写入契约")

    rule["id"] = rule_id
    rule["dimension"] = dimension
    rule["required_layers"] = list(dict.fromkeys(layers))
    rule["tolerance"] = {"css_px": float(css_px)}
    rule["state_scenario"] = rule.get("state_scenario") or {"name": "default"}
    return rule


def baseline_rule_ids(baseline_path: Path) -> tuple[set[str], set[str]]:
    """从基线的还原侧表格里读出 R 编号。

    只认表格行的第一格，避免把「取证方式」列里提到的编号当成一行基线。
    返回 (基线里出现过的全部编号, 其中需要被规则覆盖的)——标了「不适用」的维度
    不要求覆盖，但仍是合法的引用目标。
    """
    known: set[str] = set()
    required: set[str] = set()
    for line in baseline_path.read_text(encoding="utf-8").splitlines():
        match = BASELINE_RULE_ID_RE.match(line.strip())
        if not match:
            continue
        known.add(match.group(1))
        if "不适用" not in line:
            required.add(match.group(1))
    return known, required


def require_baseline_mapping(rules: list[dict[str, Any]], baseline_path: Path) -> None:
    """规则与基线必须一一映射。

    基线哈希只锁住文档本身；没有这一步，写一个基线里不存在的 `baseline_id`、
    或者漏掉基线里的某一条 R，契约照样算合法，而这两种情况都会让
    「全部规则 GREEN」不再等于「基线全部满足」。
    """
    known, required = baseline_rule_ids(baseline_path)
    if not known:
        raise ContractError(
            f"{baseline_path} 的还原侧表格里找不到任何 R1–R6 编号，无法校验规则与基线的映射"
        )

    referenced = {str(rule["baseline_id"]) for rule in rules}
    unknown = sorted(referenced - known)
    if unknown:
        raise ContractError(f"契约引用了基线里不存在的 baseline_id：{'、'.join(unknown)}")

    uncovered = sorted(required - referenced)
    if uncovered:
        raise ContractError(
            f"基线里这些条目没有对应的契约规则：{'、'.join(uncovered)}"
            "（确实不涉及的维度在基线里写「不适用」）"
        )


def require_unique_rule_ids(rules: list[dict[str, Any]]) -> None:
    counts = Counter(rule["id"] for rule in rules)
    duplicates = sorted(rule_id for rule_id, count in counts.items() if count > 1)
    if duplicates:
        raise ContractError(f"规则 id 必须唯一，重复：{'、'.join(duplicates)}")


def compile_contract(baseline_path: Path, rules_path: Path, baseline_ref: str | None = None) -> dict:
    require_frozen_baseline(baseline_path)
    rules_payload = load_json(rules_path)
    raw_rules = rules_payload.get("rules") if isinstance(rules_payload, dict) else rules_payload
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ContractError("规则输入必须是非空数组，或含非空 rules 数组的对象")

    rules = [validate_rule(raw, index) for index, raw in enumerate(raw_rules, start=1)]
    require_unique_rule_ids(rules)
    require_baseline_mapping(rules, baseline_path)

    baseline_sha256 = sha256_file(baseline_path)
    core = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "baseline": {
            "path": baseline_ref or str(baseline_path),
            "sha256": baseline_sha256,
        },
        "rules": rules,
    }
    core["contract_sha256"] = sha256_text(canonical_json(core))
    return core


def validate_contract(contract: Any, baseline_path: Path) -> dict:
    require_frozen_baseline(baseline_path)
    if not isinstance(contract, dict):
        raise ContractError("restore-contract.json 顶层必须是对象")
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ContractError(
            f"契约 schema_version 必须为 {CONTRACT_SCHEMA_VERSION}"
        )
    baseline = contract.get("baseline")
    if not isinstance(baseline, dict) or not baseline.get("sha256"):
        raise ContractError("契约缺 baseline.sha256")

    actual_baseline_sha256 = sha256_file(baseline_path)
    if baseline["sha256"] != actual_baseline_sha256:
        raise ContractError(
            "dev-baseline.md 与 restore-contract.json 哈希不一致，拒绝执行："
            f" contract={baseline['sha256']} actual={actual_baseline_sha256}"
        )

    raw_rules = contract.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ContractError("契约 rules 必须是非空数组")
    rules = [validate_rule(raw, index) for index, raw in enumerate(raw_rules, start=1)]
    if rules != raw_rules:
        raise ContractError("契约规则未规范化；请重新运行 contract 命令生成")
    # 编译期查过一次不等于此后成立：契约是落盘文件，自哈希连同重算就绕过去了。
    require_unique_rule_ids(rules)
    require_baseline_mapping(rules, baseline_path)

    core = {
        "schema_version": contract["schema_version"],
        "baseline": contract["baseline"],
        "rules": contract["rules"],
    }
    expected_contract_sha256 = sha256_text(canonical_json(core))
    if contract.get("contract_sha256") != expected_contract_sha256:
        raise ContractError("restore-contract.json 自身哈希不一致，拒绝执行")
    return contract


def validate_locator(locator: Any, rule_id: str) -> dict[str, Any]:
    if not isinstance(locator, dict):
        raise ContractError(f"规则 {rule_id} 的 locator 必须是对象")
    strategy = locator.get("strategy")
    if strategy not in LOCATOR_PRIORITY:
        raise ContractError(f"规则 {rule_id} 的 locator strategy 不支持：{strategy}")
    if strategy == "role" and (not locator.get("role") or not locator.get("name")):
        raise ContractError(f"规则 {rule_id} 的 role locator 必须同时给 role/name")
    if strategy == "text" and not locator.get("text"):
        raise ContractError(f"规则 {rule_id} 的 text locator 必须给精确文案")
    if strategy == "testid" and not locator.get("testid"):
        raise ContractError(f"规则 {rule_id} 的 testid locator 必须给 testid")
    if strategy == "css":
        selector = locator.get("selector")
        if not selector:
            raise ContractError(f"规则 {rule_id} 的 css locator 必须给 selector")
        if GENERATED_CLASS_RE.search(str(selector)):
            raise ContractError(
                f"规则 {rule_id} 的 CSS locator 疑似依赖构建生成随机 class：{selector}"
            )
    return dict(locator)


ADAPTER_FORBIDDEN_JUDGMENT_FIELDS = (
    "expected",
    "tolerance",
    "design_fact_source",
    "baseline_id",
)


def find_forbidden_adapter_fields(value: Any, path: str = "") -> list[str]:
    """Recursively find judgment-field keys hidden anywhere in an adapter entry."""
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in ADAPTER_FORBIDDEN_JUDGMENT_FIELDS:
                hits.append(child_path)
            hits.extend(find_forbidden_adapter_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            hits.extend(find_forbidden_adapter_fields(child, child_path))
    return hits


def validate_adapter(adapter: Any, contract: dict) -> dict:
    if not isinstance(adapter, dict):
        raise ContractError("restore-adapter.json 顶层必须是对象")
    if adapter.get("schema_version") != ADAPTER_SCHEMA_VERSION:
        raise ContractError(f"adapter schema_version 必须为 {ADAPTER_SCHEMA_VERSION}")
    entries = adapter.get("rules")
    if not isinstance(entries, dict):
        raise ContractError("adapter.rules 必须是对象")

    normalized: dict[str, Any] = {}
    for rule in contract["rules"]:
        rule_id = rule["id"]
        if rule.get("frozen_exemption"):
            continue
        entry = entries.get(rule_id)
        if not isinstance(entry, dict):
            raise ContractError(f"adapter 缺规则 {rule_id} 的实现定位")
        forbidden_fields = find_forbidden_adapter_fields(entry)
        if forbidden_fields:
            raise ContractError(
                f"规则 {rule_id} 的 adapter 混入外部判定字段：{forbidden_fields}"
            )
        locators = entry.get("locators")
        if not isinstance(locators, list) or not locators:
            raise ContractError(f"规则 {rule_id} 的 locators 必须是非空数组")
        checked = [validate_locator(locator, rule_id) for locator in locators]
        priorities = [LOCATOR_PRIORITY[item["strategy"]] for item in checked]
        if priorities != sorted(priorities):
            raise ContractError(
                f"规则 {rule_id} 的 locator 优先级必须是 role/name → 精确文案 → testid → CSS"
            )
        source_files = entry.get("source_files", [])
        if not isinstance(source_files, list) or any(
            not isinstance(item, str) or not item for item in source_files
        ):
            raise ContractError(f"规则 {rule_id} 的 source_files 必须是路径字符串数组")
        normalized[rule_id] = {
            **entry,
            "locators": checked,
            "source_files": source_files,
        }

    # 多出来的条目多半是契约改了而 adapter 没跟着改，静默丢弃会让人以为它还在生效。
    extra = sorted(set(entries) - {rule["id"] for rule in contract["rules"]})
    if extra:
        raise ContractError(f"adapter 含契约中不存在的规则：{'、'.join(extra)}")

    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "rules": normalized,
    }


def resolve_source_files(repo_root: Path, patterns: list[str]) -> list[Path]:
    root = repo_root.resolve()
    files: list[Path] = []
    for pattern in patterns:
        candidates = list(repo_root.glob(pattern)) if any(ch in pattern for ch in "*?[") else [repo_root / pattern]
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as error:
                raise ContractError(f"source_files 越出 repo-root：{pattern}") from error
            if resolved.is_file() and resolved not in files:
                files.append(resolved)
    return sorted(files)


def run_static_check(rule: dict, entry: dict, repo_root: Path) -> dict:
    spec = rule["static_check"]
    kind = spec.get("kind")
    files = resolve_source_files(repo_root, entry.get("source_files", []))
    resolved_root = repo_root.resolve()
    if not files:
        return {
            "status": "error",
            "reason": "没有命中任何 source_files",
            "actual": {"files": []},
        }
    bodies = [(path, path.read_text(encoding="utf-8", errors="replace")) for path in files]

    if kind in {"text", "i18n_key", "token", "state_selector"}:
        needle = spec.get("value")
        if not isinstance(needle, str) or not needle:
            return {"status": "error", "reason": f"{kind} 缺 value", "actual": None}
        matches = [
            str(path.relative_to(resolved_root))
            for path, body in bodies
            if needle in body
        ]
        matched_via = "exact" if matches else None
        # token / state_selector 是 CSS 声明针：原样未命中时按 CSS 序列化等价重试
        # （空白、大小写、hex↔rgb、0px↔0、background↔background-color 等简写别名）。
        # text / i18n_key 是逐字文案，不做归一化。
        if not matches and kind in {"token", "state_selector"}:
            normalized_bodies = [
                (path, normalize_css_text(body)) for path, body in bodies
            ]
            for variant in css_needle_variants(needle):
                matches = [
                    str(path.relative_to(resolved_root))
                    for path, body in normalized_bodies
                    if variant in body
                ]
                if matches:
                    matched_via = "css-normalized"
                    break
        actual: dict[str, Any] = {"needle": needle, "matching_files": matches}
        if matched_via:
            actual["matched_via"] = matched_via
        return {
            "status": "pass" if matches else "fail",
            "actual": actual,
        }

    if kind == "regex":
        pattern = spec.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            return {"status": "error", "reason": "regex 缺 pattern", "actual": None}
        try:
            compiled = re.compile(pattern, re.M)
        except re.error as error:
            return {"status": "error", "reason": f"regex 无效：{error}", "actual": None}
        matches = [
            str(path.relative_to(resolved_root))
            for path, body in bodies
            if compiled.search(body)
        ]
        return {
            "status": "pass" if matches else "fail",
            "actual": {"pattern": pattern, "matching_files": matches},
        }

    if kind in {"absent", "forbidden_literals"}:
        values = spec.get("values")
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            return {"status": "error", "reason": f"{kind} 缺 values", "actual": None}
        hits = []
        for path, body in bodies:
            for value in values:
                if value in body:
                    hits.append({"file": str(path.relative_to(resolved_root)), "value": value})
        return {
            "status": "pass" if not hits else "fail",
            "actual": {"forbidden_hits": hits},
        }

    return {"status": "error", "reason": f"不支持的 static_check.kind：{kind}", "actual": None}


def run_static_preflight(contract: dict, adapter: dict, repo_root: Path) -> dict:
    results: dict[str, Any] = {}
    for rule in contract["rules"]:
        if "static" not in rule["required_layers"] or rule.get("frozen_exemption"):
            continue
        results[rule["id"]] = run_static_check(
            rule,
            adapter["rules"][rule["id"]],
            repo_root,
        )
    payload = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "contract_sha256": contract["contract_sha256"],
        "rules": results,
    }
    payload["result_sha256"] = sha256_text(canonical_json(payload))
    return payload


def expected_for_layer(rule: dict, layer: str) -> Any:
    expected = rule["expected"]
    if isinstance(expected, dict) and set(expected).intersection(LAYERS):
        return expected.get(layer)
    return expected


def parse_css_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = CSS_NUMBER_RE.match(value)
        if match:
            return float(match.group(1))
    raise ValueError(f"not a CSS number: {value!r}")


def numeric_differences(expected: Any, actual: Any, path: str = "$") -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected:
            # 简写键（background / flex）按 longhand 别名回落，与采集端映射一致。
            actual_key = key if key in actual else CSS_PROPERTY_ALIASES.get(key)
            if actual_key is None or actual_key not in actual:
                differences.append({"path": f"{path}.{key}", "reason": "missing"})
            else:
                differences.extend(
                    numeric_differences(expected[key], actual[actual_key], f"{path}.{key}")
                )
        return differences
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [{"path": path, "reason": "length", "expected": len(expected), "actual": len(actual)}]
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(numeric_differences(expected_item, actual_item, f"{path}[{index}]"))
        return differences
    try:
        expected_number = parse_css_number(expected)
        actual_number = parse_css_number(actual)
    except ValueError:
        # 非数值叶子先做 CSS 序列化等价比对：#fff↔rgb(255,255,255)、box-shadow
        # 分量顺序、空白与大小写差异不是还原偏差；语义不同的值仍按差异上报。
        if (
            isinstance(expected, str)
            and isinstance(actual, str)
            and css_values_equivalent(expected, actual)
        ):
            differences.append(
                {
                    "path": path,
                    "expected": expected,
                    "actual": actual,
                    "delta": 0.0,
                    "reason": "css-equivalent",
                }
            )
            return differences
        return [{"path": path, "reason": "not-numeric", "expected": expected, "actual": actual}]
    differences.append(
        {
            "path": path,
            "expected": expected_number,
            "actual": actual_number,
            "delta": abs(actual_number - expected_number),
        }
    )
    return differences


def format_decimal(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def normalize_rgb_channel(value: str) -> int:
    value = value.strip()
    if value.endswith("%"):
        return round(float(value[:-1]) * 2.55)
    return round(float(value))


def normalize_alpha(value: str) -> float:
    value = value.strip()
    if value.endswith("%"):
        return float(value[:-1]) / 100
    return float(value)


def normalize_color(value: Any) -> str:
    """Normalize common CSS color syntaxes to a comparable RGBA tuple."""
    text = str(value).strip().lower()
    if text == "transparent":
        return "rgba(0,0,0,0)"

    hex_match = re.fullmatch(r"#([0-9a-f]{3,8})", text)
    if hex_match and len(hex_match.group(1)) in {3, 4, 6, 8}:
        digits = hex_match.group(1)
        if len(digits) in {3, 4}:
            digits = "".join(character * 2 for character in digits)
        if len(digits) == 6:
            digits += "ff"
        channels = [int(digits[index : index + 2], 16) for index in range(0, 8, 2)]
        return (
            f"rgba({channels[0]},{channels[1]},{channels[2]},"
            f"{format_decimal(channels[3] / 255)})"
        )

    functional = re.fullmatch(r"rgba?\(([^)]*)\)", text)
    if functional:
        body = functional.group(1).replace("/", ",")
        parts = [part.strip() for part in re.split(r"\s*,\s*|\s+", body) if part.strip()]
        if len(parts) in {3, 4}:
            try:
                channels = [normalize_rgb_channel(part) for part in parts[:3]]
                alpha = normalize_alpha(parts[3]) if len(parts) == 4 else 1.0
            except ValueError:
                pass
            else:
                return (
                    f"rgba({channels[0]},{channels[1]},{channels[2]},"
                    f"{format_decimal(alpha)})"
                )
    return re.sub(r"\s+", "", text)


CSS_COLOR_TOKEN_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)")
CSS_ZERO_LENGTH_RE = re.compile(r"(?<![\d.])0px\b")
# 简写属性 → 计算样式 longhand。只收「值形态兼容、误配不改变语义」的极小集合；
# collect_restore_facts.js 里有同一份映射，两端必须一致。
CSS_PROPERTY_ALIASES = {"background": "background-color", "flex": "flex-grow"}


def split_top_level(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for character in text:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == separator and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def normalize_css_text(value: Any) -> str:
    """Canonicalize CSS value/declaration text for equivalence comparison.

    只拉平**序列化差异**：大小写、空白、hex/rgb 颜色写法、`0px`/`0`。
    语义不同的值不会被拉平。仅用于 CSS 值与 CSS 声明比对——R2 文案的
    exact 比对不得经过本函数（大小写与空白在文案里是语义）。
    """
    text = str(value).strip().lower()
    text = CSS_COLOR_TOKEN_RE.sub(lambda match: normalize_color(match.group(0)), text)
    text = re.sub(r"\s*([,:;/])\s*", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    text = CSS_ZERO_LENGTH_RE.sub("0", text)
    return text


def canonicalize_css_value(value: Any) -> str:
    """归一化之上，再把每个逗号段里的颜色 token 移到段尾。

    浏览器把 box-shadow / text-shadow 的颜色序列化在最前，而设计稿声明习惯把
    颜色写在最后；分量顺序不携带语义，比对前统一到同一顺序。
    """
    segments: list[str] = []
    for segment in split_top_level(normalize_css_text(value), ","):
        tokens = segment.split(" ")
        colors = [token for token in tokens if token.startswith("rgba(")]
        rest = [token for token in tokens if not token.startswith("rgba(")]
        segments.append(" ".join(rest + colors))
    return ",".join(segments)


def css_values_equivalent(expected: Any, actual: Any) -> bool:
    return canonicalize_css_value(expected) == canonicalize_css_value(actual)


def css_needle_variants(needle: str) -> list[str]:
    """static 针的归一化变体：原样之外，补 CSS 归一形态与简写别名互换形态。"""
    base = normalize_css_text(needle)
    variants = [base]
    for shorthand, longhand in CSS_PROPERTY_ALIASES.items():
        variants.append(base.replace(f"{shorthand}:", f"{longhand}:"))
        variants.append(base.replace(f"{longhand}:", f"{shorthand}:"))
    return list(dict.fromkeys(variants))


def max_metric(value: Any) -> float:
    if isinstance(value, dict):
        numbers = [max_metric(item) for item in value.values()]
        return max(numbers, default=0.0)
    if isinstance(value, list):
        numbers = [max_metric(item) for item in value]
        return max(numbers, default=0.0)
    return parse_css_number(value)


def compare_actual(rule: dict, expected: Any, actual: Any) -> tuple[bool, dict[str, Any]]:
    mode = rule["check_mode"]
    tolerance = float(rule["tolerance"]["css_px"])
    if mode in {"exact", "structure", "state"}:
        return expected == actual, {"expected": expected, "actual": actual}
    if mode == "numeric":
        differences = numeric_differences(expected, actual)
        passed = all(
            item.get("delta", tolerance + 1) <= tolerance for item in differences
        )
        return passed, {"tolerance_css_px": tolerance, "differences": differences}
    if mode == "color":
        normalized_expected = normalize_color(expected)
        normalized_actual = normalize_color(actual)
        return normalized_expected == normalized_actual, {
            "expected": normalized_expected,
            "actual": normalized_actual,
        }
    if mode in {"overflow", "overlap", "clip"}:
        try:
            measured = max_metric(actual)
        except ValueError:
            return False, {"threshold_css_px": tolerance, "actual": actual, "reason": "not-numeric"}
        return measured <= tolerance, {
            "threshold_css_px": tolerance,
            "actual_max_css_px": measured,
        }
    if mode == "visual":
        return False, {"reason": "visual mode must be decided by visual-results"}
    raise ContractError(f"未知 check_mode：{mode}")


def result_rules(payload: Any, name: str, contract_sha256: str) -> dict:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ContractError(f"{name} 顶层必须是对象")
    if payload.get("contract_sha256") != contract_sha256:
        raise ContractError(f"{name} 的 contract_sha256 与冻结契约不一致")
    rules = payload.get("rules", {})
    if not isinstance(rules, dict):
        raise ContractError(f"{name}.rules 必须是对象")
    return rules


def evidence_request(layer: str, rule: dict) -> str:
    if layer == "static":
        return "运行同一冻结契约的 static 子命令并提供 static-results.json"
    if layer == "render":
        if rule["dimension"] == "R5":
            return "提供冻结基线指定的状态 fixture，再注入 collect_restore_facts.js"
        if rule["dimension"] == "R4":
            return "实际触发 state_scenario 后，再注入 collect_restore_facts.js"
        return "启动页面并注入 collect_restore_facts.js，提供结构化渲染结果"
    return "命中或生成原型视觉缓存，并提供同视口实现截图作选择性视觉补证"


def evaluate_rule(
    rule: dict,
    adapter_entry: dict | None,
    static_rules: dict,
    render_payload: dict | None,
    render_rules: dict,
    visual_rules: dict,
) -> dict:
    base = {
        "rule_id": rule["id"],
        "baseline_id": rule["baseline_id"],
        "dimension": rule["dimension"],
        "block": rule["block"],
        "subject": rule["subject"],
        "expected": rule["expected"],
        "check_mode": rule["check_mode"],
        "required_layers": rule["required_layers"],
        "contract_source": {
            "baseline_id": rule["baseline_id"],
            "design_fact_source": rule["design_fact_source"],
        },
        "implementation_locator": (
            {"locators": adapter_entry["locators"]} if adapter_entry else {"exempt": True}
        ),
    }

    exemption = rule.get("frozen_exemption")
    if exemption:
        return {
            **base,
            "status": "green",
            "verified_layers": [],
            "frozen_exemption": exemption,
        }

    red_reasons: list[str] = []
    yellow_reasons: list[str] = []
    required_evidence: list[str] = []
    actual_by_layer: dict[str, Any] = {}
    verified_layers: list[str] = []

    for layer in rule["required_layers"]:
        expected = expected_for_layer(rule, layer)
        if layer == "static":
            item = static_rules.get(rule["id"])
            actual_by_layer[layer] = item
            if item is None:
                red_reasons.append("静态预检未运行或缺本规则结果")
            elif item.get("status") == "pass":
                verified_layers.append(layer)
            else:
                red_reasons.append(item.get("reason") or "静态预检不通过")
            continue

        if layer == "render":
            if render_payload is None:
                yellow_reasons.append("未提供页面能力与结构化渲染结果")
                required_evidence.append(evidence_request(layer, rule))
                continue
            if render_payload.get("page_available") is False:
                yellow_reasons.append(
                    f"页面不可用：{render_payload.get('reason', '未说明原因')}"
                )
                required_evidence.append(evidence_request(layer, rule))
                continue
            if render_payload.get("capture_error"):
                actual_by_layer[layer] = {"capture_error": render_payload["capture_error"]}
                red_reasons.append("结构化渲染已尝试但采集失败")
                continue
            item = render_rules.get(rule["id"])
            actual_by_layer[layer] = item
            if item is None:
                red_reasons.append("页面可用但结构化采集缺本规则结果")
                continue
            status = item.get("status")
            if status in {"missing_fixture", "unavailable"}:
                yellow_reasons.append(item.get("reason") or status)
                required_evidence.append(evidence_request(layer, rule))
                continue
            if status in {"error", "capture_error"}:
                red_reasons.append(item.get("reason") or "结构化采集失败")
                continue
            if status != "ok":
                red_reasons.append(f"结构化采集返回未知状态：{status}")
                continue
            passed, detail = compare_actual(rule, expected, item.get("actual"))
            actual_by_layer[layer] = {**item, "comparison": detail}
            if passed:
                verified_layers.append(layer)
            else:
                red_reasons.append("结构化渲染实际值不符合冻结契约")
            continue

        if layer == "visual":
            item = visual_rules.get(rule["id"])
            actual_by_layer[layer] = item
            if item is None or item.get("status") in {"unavailable", "yellow"}:
                yellow_reasons.append(
                    (item or {}).get("reason", "机器无法可靠判定，尚无视觉补证")
                )
                required_evidence.append(evidence_request(layer, rule))
                continue
            if item.get("status") == "green":
                verified_layers.append(layer)
            elif item.get("status") == "red":
                red_reasons.append(item.get("reason") or "视觉补证发现明确偏差")
            else:
                red_reasons.append(f"visual-results 返回未知状态：{item.get('status')}")

    if red_reasons:
        return {
            **base,
            "status": "red",
            "actual": actual_by_layer,
            "reasons": red_reasons,
        }
    if yellow_reasons:
        return {
            **base,
            "status": "yellow",
            "actual": actual_by_layer,
            "reasons": yellow_reasons,
            "required_evidence": list(dict.fromkeys(required_evidence)),
        }
    return {
        **base,
        "status": "green",
        "actual": actual_by_layer,
        "verified_layers": verified_layers,
    }


def build_report(
    contract: dict,
    adapter: dict,
    phase: str,
    static_payload: dict | None,
    render_payload: dict | None,
    visual_payload: dict | None,
) -> dict:
    static_rules = result_rules(
        static_payload,
        "static-results",
        contract["contract_sha256"],
    )
    render_rules = result_rules(
        render_payload,
        "render-results",
        contract["contract_sha256"],
    )
    visual_rules = result_rules(
        visual_payload,
        "visual-results",
        contract["contract_sha256"],
    )

    entries = [
        evaluate_rule(
            rule,
            adapter["rules"].get(rule["id"]),
            static_rules,
            render_payload,
            render_rules,
            visual_rules,
        )
        for rule in contract["rules"]
    ]
    counts = {
        status: sum(1 for entry in entries if entry["status"] == status)
        for status in ("red", "yellow", "green")
    }
    overall = "red" if counts["red"] else ("yellow" if counts["yellow"] else "green")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": phase,
        "contract_sha256": contract["contract_sha256"],
        "baseline_sha256": contract["baseline"]["sha256"],
        "overall": overall,
        "summary": {
            **counts,
            "total": len(entries),
        },
        "entries": entries,
    }
    report["report_sha256"] = sha256_text(canonical_json(report))
    return report


def detect_restore_evidence_format(markdown: str) -> str:
    """Identify legacy screenshot evidence without requiring migration."""
    if (
        "restore-report-red.json" in markdown
        or "restore-report-green.json" in markdown
        or "报告指纹" in markdown
    ):
        return "machine-v2"
    if (
        "还原证据记录" in markdown
        and "RED 双方截图" in markdown
        and "GREEN 复核" in markdown
    ):
        return "legacy-screenshot-v1"
    return "none"


def optional_json(path: str | None) -> dict | None:
    return load_json(Path(path).expanduser()) if path else None


def require_recompile_is_allowed(out_path: Path, baseline_path: Path, acknowledged: bool) -> None:
    """基线改过之后重新编译，必须先经过重新确认。

    「已冻结 ✅」是写在基线正文里的，改基线内容不会把它去掉，所以这一步拦不住的话
    一条命令就能把旧契约连同它记录的基线哈希一起换掉——冻结也就名存实亡。
    """
    if acknowledged or not out_path.exists():
        return
    try:
        existing = load_json(out_path)
    except ContractError:
        return
    if not isinstance(existing, dict):
        return
    previous = (existing.get("baseline") or {}).get("sha256")
    if not previous or previous == sha256_file(baseline_path):
        return
    raise ContractError(
        f"{out_path} 已存在，且它记录的基线哈希与当前 dev-baseline.md 不同："
        f" contract={previous} actual={sha256_file(baseline_path)}。"
        "基线冻结后每一次放宽都要先在「变更记录」登记并重新请用户确认；"
        "确认过了再加 --after-reconfirmation 重新编译。"
    )


def command_contract(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline).expanduser()
    out_path = Path(args.out).expanduser()
    require_recompile_is_allowed(out_path, baseline_path, args.after_reconfirmation)
    contract = compile_contract(
        baseline_path,
        Path(args.rules).expanduser(),
        args.baseline_ref,
    )
    write_json(out_path, contract)
    print(
        json.dumps(
            {
                "status": "written",
                "out": str(out_path),
                "contract_sha256": contract["contract_sha256"],
                "rules": len(contract["rules"]),
            },
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def load_contract_and_adapter(args: argparse.Namespace) -> tuple[dict, dict]:
    contract = validate_contract(
        load_json(Path(args.contract).expanduser()),
        Path(args.baseline).expanduser(),
    )
    adapter = validate_adapter(
        load_json(Path(args.adapter).expanduser()),
        contract,
    )
    return contract, adapter


def command_validate(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    print(
        json.dumps(
            {
                "status": "valid",
                "contract_sha256": contract["contract_sha256"],
                "rules": len(contract["rules"]),
                "adapter_rules": len(adapter["rules"]),
            },
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def command_static(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    result = run_static_preflight(
        contract,
        adapter,
        Path(args.repo_root).expanduser(),
    )
    write_json(Path(args.out).expanduser(), result)
    print(
        json.dumps(
            {
                "status": "written",
                "out": str(Path(args.out).expanduser()),
                "rules": len(result["rules"]),
            },
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def report_exit_code(phase: str, overall: str) -> int:
    if phase == "green" and overall != "green":
        return EXIT_NOT_GREEN
    return EXIT_OK


def command_report(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    report = build_report(
        contract,
        adapter,
        args.phase,
        optional_json(args.static_results),
        optional_json(args.render_results),
        optional_json(args.visual_results),
    )
    write_json(Path(args.out).expanduser(), report)
    print(
        json.dumps(
            {
                "status": report["overall"],
                "out": str(Path(args.out).expanduser()),
                "report_sha256": report["report_sha256"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )
    return report_exit_code(args.phase, report["overall"])


def command_evidence_format(args: argparse.Namespace) -> int:
    path = Path(args.alpha_tests).expanduser()
    print(
        json.dumps(
            {
                "format": detect_restore_evidence_format(
                    path.read_text(encoding="utf-8", errors="replace")
                ),
                "path": str(path),
            },
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def add_contract_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", required=True, help="Story 级 restore-contract.json")
    parser.add_argument("--baseline", required=True, help="权威 dev-baseline.md")
    parser.add_argument("--adapter", required=True, help="实现定位 restore-adapter.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract_parser = subparsers.add_parser(
        "contract",
        help="把规则草稿与冻结 dev-baseline.md 编译成 restore-contract.json",
    )
    contract_parser.add_argument("--baseline", required=True)
    contract_parser.add_argument("--rules", required=True)
    contract_parser.add_argument("--out", required=True)
    contract_parser.add_argument(
        "--baseline-ref",
        help="写进契约的可移植基线路径；缺省使用 --baseline 原值",
    )
    contract_parser.add_argument(
        "--after-reconfirmation",
        action="store_true",
        help="基线变更已在「变更记录」登记并重新经用户确认，允许覆盖已有契约",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="校验契约哈希、规则和实现定位",
    )
    add_contract_inputs(validate_parser)

    static_parser = subparsers.add_parser(
        "static",
        help="运行文案/i18n key/token/禁用字面量/状态选择器静态预检",
    )
    add_contract_inputs(static_parser)
    static_parser.add_argument("--repo-root", required=True)
    static_parser.add_argument("--out", required=True)

    report_parser = subparsers.add_parser(
        "report",
        help="合并三层结果，生成 restore-report-red/green.json",
    )
    add_contract_inputs(report_parser)
    report_parser.add_argument("--phase", choices=["red", "green"], required=True)
    report_parser.add_argument("--static-results")
    report_parser.add_argument("--render-results")
    report_parser.add_argument("--visual-results")
    report_parser.add_argument("--out", required=True)

    evidence_parser = subparsers.add_parser(
        "evidence-format",
        help="识别旧截图证据或 V2 报告引用；旧 Story 不要求迁移",
    )
    evidence_parser.add_argument("--alpha-tests", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "contract":
            return command_contract(args)
        if args.command == "validate":
            return command_validate(args)
        if args.command == "static":
            return command_static(args)
        if args.command == "report":
            return command_report(args)
        if args.command == "evidence-format":
            return command_evidence_format(args)
    except (ContractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
