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
    if "static" in layers and not isinstance(rule.get("static_check"), dict):
        raise ContractError(f"规则 {rule_id} 要求 static 层但没有 static_check")

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


def compile_contract(baseline_path: Path, rules_path: Path, baseline_ref: str | None = None) -> dict:
    require_frozen_baseline(baseline_path)
    rules_payload = load_json(rules_path)
    raw_rules = rules_payload.get("rules") if isinstance(rules_payload, dict) else rules_payload
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ContractError("规则输入必须是非空数组，或含非空 rules 数组的对象")

    rules = [validate_rule(raw, index) for index, raw in enumerate(raw_rules, start=1)]
    ids = [rule["id"] for rule in rules]
    if len(ids) != len(set(ids)):
        raise ContractError("规则 id 必须唯一")

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
        forbidden_fields = [
            field
            for field in ("expected", "tolerance", "design_fact_source", "baseline_id")
            if field in entry
        ]
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
        return {
            "status": "pass" if matches else "fail",
            "actual": {"needle": needle, "matching_files": matches},
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
            if key not in actual:
                differences.append({"path": f"{path}.{key}", "reason": "missing"})
            else:
                differences.extend(numeric_differences(expected[key], actual[key], f"{path}.{key}"))
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


def command_contract(args: argparse.Namespace) -> int:
    contract = compile_contract(
        Path(args.baseline).expanduser(),
        Path(args.rules).expanduser(),
        args.baseline_ref,
    )
    write_json(Path(args.out).expanduser(), contract)
    print(
        json.dumps(
            {
                "status": "written",
                "out": str(Path(args.out).expanduser()),
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
