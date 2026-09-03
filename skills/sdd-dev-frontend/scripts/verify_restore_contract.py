#!/usr/bin/env python3
"""Compile, validate, and report frozen frontend restore contracts.

V3 keeps one rule on one evidence layer. V2 contracts remain readable so existing
GREEN stories do not need a migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_NOT_GREEN = 3
CONTRACT_SCHEMA_VERSION = 3
ADAPTER_SCHEMA_VERSION = 2
RESULT_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 3

V2_CHECK_MODES = {
    "exact", "structure", "numeric", "color", "state",
    "overflow", "overlap", "clip", "stacking", "visual",
}
V3_CHECK_MODES = {"exact", "numeric", "overflow", "overlap", "clip", "stacking"}
THRESHOLD_MODES = {"overflow", "overlap", "clip"}
LOCATOR_STRATEGIES = {"role", "text", "testid", "css"}
GENERATED_CLASS_RE = re.compile(
    r"(?:\.[A-Za-z_-]*[0-9a-fA-F]{8,}\b|\.[A-Za-z][\w-]*_[A-Za-z0-9]{6,}\b)"
)
CSS_NUMBER_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:px)?\s*$")
BASELINE_RULE_ID_RE = re.compile(r"^\|\s*`?(R[1-6]-\d+)`?\s*\|")
CSS_COLOR_TOKEN_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)")
CSS_ZERO_LENGTH_RE = re.compile(r"(?<![\d.])0px\b")
CSS_PROPERTY_ALIASES = {"background": "background-color", "flex": "flex-grow"}
STATIC_KINDS = {
    "text", "i18n_key", "token", "state_selector", "regex", "absent",
    "forbidden_literals",
}
V3_RULE_FIELDS = {
    "id", "baseline_id", "subject", "scenario", "fixture_required",
    "check_mode", "expected", "tolerance", "static_check", "frozen_exemption",
}

class ContractError(ValueError):
    """Raised when a restore artifact cannot be trusted."""
def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def require_frozen_baseline(path: Path) -> None:
    if "已冻结 ✅" not in path.read_text(encoding="utf-8"):
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
    if not path.exists() or path.read_text(encoding="utf-8") != body:
        path.write_text(body, encoding="utf-8")
def is_empty_expectation(value: Any) -> bool:
    return value is None or (
        isinstance(value, (dict, list, tuple, str)) and len(value) == 0
    )
def default_tolerance(mode: str) -> dict[str, float]:
    return {"css_px": 1.0 if mode in {"numeric", *THRESHOLD_MODES} else 0.0}
def normalized_tolerance(rule: dict[str, Any]) -> dict[str, float]:
    tolerance = rule.get("tolerance", default_tolerance(str(rule.get("check_mode", "exact"))))
    if not isinstance(tolerance, dict):
        raise ContractError(f"规则 {rule.get('id')} 的 tolerance 必须是对象")
    css_px = tolerance.get("css_px", 0)
    if isinstance(css_px, bool) or not isinstance(css_px, (int, float)) or css_px < 0:
        raise ContractError(f"规则 {rule.get('id')} 的 tolerance.css_px 必须是非负数")
    return {"css_px": float(css_px)}
def validate_exemption(rule: dict[str, Any], *, v2: bool) -> None:
    exemption = rule.get("frozen_exemption")
    if exemption is None:
        return
    if not isinstance(exemption, dict) or not exemption.get("id") or not exemption.get("reason"):
        raise ContractError(f"规则 {rule.get('id')} 的 frozen_exemption 缺 id 或 reason")
    if v2 and exemption.get("frozen") is not True:
        raise ContractError(f"规则 {rule.get('id')} 的豁免未冻结，不能写入契约")
def validate_static_check(rule: dict[str, Any]) -> None:
    spec = rule.get("static_check")
    if not isinstance(spec, dict) or spec.get("kind") not in STATIC_KINDS:
        raise ContractError(f"规则 {rule.get('id')} 的 static_check 不合法")
def validate_rule_v3(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ContractError(f"第 {index} 条规则必须是对象")
    rule = dict(raw)
    missing = [name for name in ("id", "baseline_id", "subject") if not rule.get(name)]
    if missing:
        raise ContractError(f"规则 {rule.get('id', index)} 缺字段：{', '.join(missing)}")
    unsupported = sorted(set(rule) - V3_RULE_FIELDS)
    if unsupported:
        raise ContractError(f"v3 规则 {rule['id']} 含已删除字段：{', '.join(unsupported)}")
    if "scenario" in rule and not isinstance(rule["scenario"], str):
        raise ContractError(f"规则 {rule['id']} 的 scenario 必须是字符串")
    if "fixture_required" in rule and not isinstance(rule["fixture_required"], bool):
        raise ContractError(f"规则 {rule['id']} 的 fixture_required 必须是布尔值")
    validate_exemption(rule, v2=False)
    forms = sum(
        bool(value)
        for value in (
            rule.get("frozen_exemption"), rule.get("static_check"), rule.get("check_mode")
        )
    )
    if forms != 1:
        raise ContractError(
            f"规则 {rule['id']} 必须且只能是 render、static、exempt 三种形态之一"
        )
    if rule.get("static_check"):
        validate_static_check(rule)
        forbidden = [name for name in ("check_mode", "expected", "tolerance") if name in rule]
        if forbidden:
            raise ContractError(f"static 规则 {rule['id']} 不应含：{', '.join(forbidden)}")
        return rule
    if rule.get("frozen_exemption"):
        forbidden = [name for name in ("check_mode", "expected", "static_check", "tolerance") if name in rule]
        if forbidden:
            raise ContractError(f"exempt 规则 {rule['id']} 不应含：{', '.join(forbidden)}")
        return rule
    mode = str(rule["check_mode"])
    if mode not in V3_CHECK_MODES:
        raise ContractError(f"规则 {rule['id']} 的 check_mode 不支持：{mode}")
    if mode == "stacking":
        expected = rule.get("expected")
        if not isinstance(expected, dict) or not isinstance(expected.get("subject_on_top"), bool):
            raise ContractError(
                f"规则 {rule['id']} 的 stacking expected.subject_on_top 必须是布尔值"
            )
    elif mode not in THRESHOLD_MODES and is_empty_expectation(rule.get("expected")):
        raise ContractError(f"规则 {rule['id']} 的 render expected 为空：没有期望值就没有判据")
    if mode in THRESHOLD_MODES and "expected" in rule:
        raise ContractError(f"规则 {rule['id']} 的 {mode} 阈值由 tolerance 表达，不写 expected")
    tolerance = normalized_tolerance(rule)
    if "tolerance" in rule:
        rule["tolerance"] = tolerance
    return rule
def expected_for_layer(rule: dict[str, Any], layer: str) -> Any:
    expected = rule.get("expected")
    if (
        "required_layers" in rule
        and isinstance(expected, dict)
        and {"static", "render", "visual"} & set(expected)
    ):
        return expected.get(layer)
    return expected
def validate_rule_v2(raw: Any, index: int) -> dict[str, Any]:
    """Read legacy rules without forcing them through a V3 migration."""
    if not isinstance(raw, dict):
        raise ContractError(f"第 {index} 条规则必须是对象")
    rule = dict(raw)
    required = ("id", "baseline_id", "dimension", "block", "subject", "check_mode")
    missing = [name for name in required if not rule.get(name)]
    if missing:
        raise ContractError(f"规则 {rule.get('id', index)} 缺字段：{', '.join(missing)}")
    if rule["check_mode"] not in V2_CHECK_MODES:
        raise ContractError(f"规则 {rule['id']} 的 check_mode 不支持：{rule['check_mode']}")
    layers = rule.get("required_layers") or ["static" if rule.get("static_check") else "render"]
    if not isinstance(layers, list) or not layers or set(layers) - {"static", "render", "visual"}:
        raise ContractError(f"规则 {rule['id']} 的 required_layers 不合法")
    if "static" in layers:
        validate_static_check(rule)
    validate_exemption(rule, v2=True)
    rule["required_layers"] = layers
    rule["tolerance"] = normalized_tolerance(rule)
    return rule
def baseline_rule_ids(path: Path) -> tuple[set[str], set[str]]:
    known: set[str] = set()
    required: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = BASELINE_RULE_ID_RE.match(line.strip())
        if match:
            known.add(match.group(1))
            if "不适用" not in line:
                required.add(match.group(1))
    return known, required
def require_baseline_mapping(rules: list[dict[str, Any]], baseline_path: Path) -> None:
    known, required = baseline_rule_ids(baseline_path)
    if not known:
        raise ContractError(f"{baseline_path} 的还原侧表格里找不到 R1–R6 编号")
    referenced = {str(rule["baseline_id"]) for rule in rules}
    unknown = sorted(referenced - known)
    uncovered = sorted(required - referenced)
    if unknown:
        raise ContractError(f"契约引用了基线里不存在的 baseline_id：{'、'.join(unknown)}")
    if uncovered:
        raise ContractError(f"基线里这些条目没有对应的契约规则：{'、'.join(uncovered)}")
def require_unique_rule_ids(rules: list[dict[str, Any]]) -> None:
    counts = Counter(rule["id"] for rule in rules)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    if duplicates:
        raise ContractError(f"规则 id 必须唯一，重复：{'、'.join(duplicates)}")
def read_rules(source: Path | str) -> Any:
    if str(source) == "-":
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as error:
            raise ContractError(f"stdin JSON 无法解析：{error}") from error
    return load_json(Path(source).expanduser())
def compile_contract(baseline_path: Path, rules_source: Path | str) -> dict[str, Any]:
    require_frozen_baseline(baseline_path)
    payload = read_rules(rules_source)
    raw_rules = payload.get("rules") if isinstance(payload, dict) else payload
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ContractError("规则输入必须是非空数组，或含非空 rules 数组的对象")
    rules = [validate_rule_v3(raw, index) for index, raw in enumerate(raw_rules, 1)]
    require_unique_rule_ids(rules)
    require_baseline_mapping(rules, baseline_path)
    core = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "baseline_sha256": sha256_file(baseline_path),
        "rules": rules,
    }
    return {**core, "contract_sha256": sha256_text(canonical_json(core))}
def validate_contract(contract: Any, baseline_path: Path) -> dict[str, Any]:
    require_frozen_baseline(baseline_path)
    if not isinstance(contract, dict):
        raise ContractError("restore-contract.json 顶层必须是对象")
    version = contract.get("schema_version")
    if version not in {2, 3}:
        raise ContractError("契约 schema_version 必须为 2 或 3")
    stored = contract.get("baseline_sha256") if version == 3 else (contract.get("baseline") or {}).get("sha256")
    actual = sha256_file(baseline_path)
    if not stored or stored != actual:
        raise ContractError(
            "dev-baseline.md 与 restore-contract.json 哈希不一致，拒绝执行："
            f" contract={stored} actual={actual}"
        )
    if not contract.get("contract_sha256"):
        raise ContractError("契约缺 contract_sha256 链接键")
    raw_rules = contract.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ContractError("契约 rules 必须是非空数组")
    validator = validate_rule_v3 if version == 3 else validate_rule_v2
    rules = [validator(raw, index) for index, raw in enumerate(raw_rules, 1)]
    require_unique_rule_ids(rules)
    require_baseline_mapping(rules, baseline_path)
    return {**contract, "rules": rules}
def rule_layers(rule: dict[str, Any]) -> list[str]:
    if "required_layers" in rule:
        return list(rule["required_layers"])
    if rule.get("frozen_exemption"):
        return []
    return ["static" if rule.get("static_check") else "render"]
def validate_locator(locator: Any, rule_id: str) -> dict[str, Any]:
    if not isinstance(locator, dict) or locator.get("strategy") not in LOCATOR_STRATEGIES:
        raise ContractError(f"规则 {rule_id} 的 locator 不合法")
    strategy = locator["strategy"]
    required = {"role": ("role", "name"), "text": ("text",), "testid": ("testid",), "css": ("selector",)}
    if any(not locator.get(name) for name in required[strategy]):
        raise ContractError(f"规则 {rule_id} 的 {strategy} locator 缺必要字段")
    if strategy == "css" and GENERATED_CLASS_RE.search(str(locator["selector"])):
        warnings.warn(
            f"规则 {rule_id} 的 CSS locator 疑似依赖构建生成随机 class：{locator['selector']}",
            stacklevel=2,
        )
    return dict(locator)
def validate_adapter(adapter: Any, contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(adapter, dict) or adapter.get("schema_version") not in {1, 2}:
        raise ContractError("restore-adapter.json 顶层或 schema_version 不合法")
    entries = adapter.get("rules")
    if not isinstance(entries, dict):
        raise ContractError("adapter.rules 必须是对象")
    normalized: dict[str, Any] = {}
    for rule in contract["rules"]:
        if rule.get("frozen_exemption"):
            continue
        rule_id = rule["id"]
        entry = entries.get(rule_id)
        if not isinstance(entry, dict):
            raise ContractError(f"adapter 缺规则 {rule_id} 的实现定位")
        layers = rule_layers(rule)
        output = dict(entry)
        source_files = entry.get("source_files", [])
        if not isinstance(source_files, list) or any(not isinstance(item, str) or not item for item in source_files):
            raise ContractError(f"规则 {rule_id} 的 source_files 必须是路径字符串数组")
        if contract["schema_version"] == 3 and "static" in layers and not source_files:
            raise ContractError(f"static 规则 {rule_id} 必须给 source_files")
        output["source_files"] = source_files
        if "render" in layers:
            locators = entry.get("locators")
            if not isinstance(locators, list) or not locators:
                raise ContractError(f"render 规则 {rule_id} 的 locators 必须是非空数组")
            output["locators"] = [validate_locator(item, rule_id) for item in locators]
            if not isinstance(entry.get("collect"), dict):
                raise ContractError(f"render 规则 {rule_id} 必须给 collect")
        normalized[rule_id] = output
    extra = sorted(set(entries) - {rule["id"] for rule in contract["rules"]})
    if extra:
        raise ContractError(f"adapter 含契约中不存在的规则：{'、'.join(extra)}")
    return {"schema_version": adapter["schema_version"], "rules": normalized}
def resolve_source_files(repo_root: Path, patterns: list[str]) -> list[Path]:
    root = repo_root.resolve()
    files: list[Path] = []
    for pattern in patterns:
        candidates = list(repo_root.glob(pattern)) if any(c in pattern for c in "*?[") else [repo_root / pattern]
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as error:
                raise ContractError(f"source_files 越出 repo-root：{pattern}") from error
            if resolved.is_file() and resolved not in files:
                files.append(resolved)
    return sorted(files)
def run_static_check(rule: dict[str, Any], entry: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    spec = rule["static_check"]
    kind = spec.get("kind")
    files = resolve_source_files(repo_root, entry.get("source_files", []))
    root = repo_root.resolve()
    if not files:
        return {"status": "error", "reason": "没有命中任何 source_files", "actual": {"files": []}}
    bodies = [(path, path.read_text(encoding="utf-8", errors="replace")) for path in files]
    if kind in {"text", "i18n_key", "token", "state_selector"}:
        needle = spec.get("value")
        if not isinstance(needle, str) or not needle:
            return {"status": "error", "reason": f"{kind} 缺 value", "actual": None}
        matches = [str(path.relative_to(root)) for path, body in bodies if needle in body]
        matched_via = "exact" if matches else None
        if not matches and kind in {"token", "state_selector"}:
            normalized = [(path, normalize_css_text(body)) for path, body in bodies]
            for variant in css_needle_variants(needle):
                matches = [str(path.relative_to(root)) for path, body in normalized if variant in body]
                if matches:
                    matched_via = "css-normalized"
                    break
        actual: dict[str, Any] = {"needle": needle, "matching_files": matches}
        if matched_via:
            actual["matched_via"] = matched_via
        return {"status": "pass" if matches else "fail", "actual": actual}
    if kind == "regex":
        pattern = spec.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            return {"status": "error", "reason": "regex 缺 pattern", "actual": None}
        try:
            compiled = re.compile(pattern, re.M)
        except re.error as error:
            return {"status": "error", "reason": f"regex 无效：{error}", "actual": None}
        matches = [str(path.relative_to(root)) for path, body in bodies if compiled.search(body)]
        return {"status": "pass" if matches else "fail", "actual": {"pattern": pattern, "matching_files": matches}}
    if kind in {"absent", "forbidden_literals"}:
        values = spec.get("values")
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            return {"status": "error", "reason": f"{kind} 缺 values", "actual": None}
        hits = [
            {"file": str(path.relative_to(root)), "value": value}
            for path, body in bodies for value in values if value in body
        ]
        return {"status": "pass" if not hits else "fail", "actual": {"forbidden_hits": hits}}
    return {"status": "error", "reason": f"不支持的 static_check.kind：{kind}", "actual": None}
def run_static_preflight(contract: dict[str, Any], adapter: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    rules = {
        rule["id"]: run_static_check(rule, adapter["rules"][rule["id"]], repo_root)
        for rule in contract["rules"]
        if "static" in rule_layers(rule) and not rule.get("frozen_exemption")
    }
    payload = {"schema_version": RESULT_SCHEMA_VERSION, "contract_sha256": contract["contract_sha256"], "rules": rules}
    payload["result_sha256"] = sha256_text(canonical_json(payload))
    return payload
def format_decimal(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
def normalize_color(value: Any) -> str:
    text = str(value).strip().lower()
    if text == "transparent":
        return "rgba(0,0,0,0)"
    match = re.fullmatch(r"#([0-9a-f]{3,8})", text)
    if match and len(match.group(1)) in {3, 4, 6, 8}:
        digits = match.group(1)
        if len(digits) in {3, 4}:
            digits = "".join(c * 2 for c in digits)
        if len(digits) == 6:
            digits += "ff"
        channels = [int(digits[i:i + 2], 16) for i in range(0, 8, 2)]
        return f"rgba({channels[0]},{channels[1]},{channels[2]},{format_decimal(channels[3] / 255)})"
    match = re.fullmatch(r"rgba?\(([^)]*)\)", text)
    if match:
        parts = [part for part in re.split(r"\s*,\s*|\s+", match.group(1).replace("/", ",")) if part]
        if len(parts) in {3, 4}:
            try:
                rgb = [round(float(p[:-1]) * 2.55) if p.endswith("%") else round(float(p)) for p in parts[:3]]
                alpha = (float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3])) if len(parts) == 4 else 1.0
                return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{format_decimal(alpha)})"
            except ValueError:
                pass
    return re.sub(r"\s+", "", text)
def normalize_css_text(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"-apple-system|\bblinkmacsystemfont\b", "system-ui", text)
    text = re.sub(r"(['\"])system-ui\1", "system-ui", text)
    text = CSS_COLOR_TOKEN_RE.sub(lambda match: normalize_color(match.group(0)), text)
    text = re.sub(r"\s*([,:;/])\s*", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    text = CSS_ZERO_LENGTH_RE.sub("0", text)
    while "system-ui,system-ui" in text:
        text = text.replace("system-ui,system-ui", "system-ui")
    return text
def split_top_level(text: str, separator: str) -> list[str]:
    output: list[str] = []
    current: list[str] = []
    depth = 0
    for character in text:
        depth += character == "("
        depth -= character == ")"
        if character == separator and depth == 0:
            output.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    output.append("".join(current).strip())
    return [item for item in output if item]
def canonicalize_css_value(value: Any) -> str:
    segments = []
    for segment in split_top_level(normalize_css_text(value), ","):
        tokens = segment.split(" ")
        colors = [token for token in tokens if token.startswith("rgba(")]
        segments.append(" ".join([token for token in tokens if token not in colors] + colors))
    return ",".join(segments)
def css_values_equivalent(expected: Any, actual: Any) -> bool:
    return canonicalize_css_value(expected) == canonicalize_css_value(actual)
def css_needle_variants(needle: str) -> list[str]:
    base = normalize_css_text(needle)
    variants = [base]
    for shorthand, longhand in CSS_PROPERTY_ALIASES.items():
        variants += [base.replace(f"{shorthand}:", f"{longhand}:"), base.replace(f"{longhand}:", f"{shorthand}:")]
    return list(dict.fromkeys(variants))
def parse_css_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    if isinstance(value, (int, float)):
        return float(value)
    match = CSS_NUMBER_RE.match(value) if isinstance(value, str) else None
    if match:
        return float(match.group(1))
    raise ValueError(f"not a CSS number: {value!r}")
def numeric_differences(expected: Any, actual: Any, path: str = "$") -> list[dict[str, Any]]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        output: list[dict[str, Any]] = []
        for key, value in expected.items():
            actual_key = key if key in actual else CSS_PROPERTY_ALIASES.get(key)
            if not actual_key or actual_key not in actual:
                output.append({"path": f"{path}.{key}", "reason": "missing"})
            else:
                output += numeric_differences(value, actual[actual_key], f"{path}.{key}")
        return output
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [{"path": path, "reason": "length", "expected": len(expected), "actual": len(actual)}]
        return [item for index, pair in enumerate(zip(expected, actual)) for item in numeric_differences(*pair, f"{path}[{index}]")]
    try:
        left, right = parse_css_number(expected), parse_css_number(actual)
        return [{"path": path, "expected": left, "actual": right, "delta": abs(right - left)}]
    except ValueError:
        if isinstance(expected, str) and isinstance(actual, str) and css_values_equivalent(expected, actual):
            return [{"path": path, "expected": expected, "actual": actual, "delta": 0.0, "reason": "css-equivalent"}]
        return [{"path": path, "reason": "not-numeric", "expected": expected, "actual": actual}]
def max_metric(value: Any) -> float:
    if isinstance(value, dict):
        return max((max_metric(item) for item in value.values()), default=0.0)
    if isinstance(value, list):
        return max((max_metric(item) for item in value), default=0.0)
    return parse_css_number(value)
def compare_actual(rule: dict[str, Any], expected: Any, actual: Any) -> tuple[bool, dict[str, Any]]:
    mode = rule["check_mode"]
    tolerance = float(rule.get("tolerance", default_tolerance(mode))["css_px"])
    if mode in {"exact", "structure", "state"}:
        return expected == actual, {"expected": expected, "actual": actual}
    if mode == "color":
        left, right = normalize_color(expected), normalize_color(actual)
        return left == right, {"expected": left, "actual": right}
    if mode == "numeric":
        differences = numeric_differences(expected, actual)
        return all(item.get("delta", tolerance + 1) <= tolerance for item in differences), {"tolerance_css_px": tolerance, "differences": differences}
    if mode in THRESHOLD_MODES:
        try:
            measured = max_metric(actual)
        except ValueError:
            return False, {"threshold_css_px": tolerance, "actual": actual, "reason": "not-numeric"}
        return measured <= tolerance, {"threshold_css_px": tolerance, "actual_max_css_px": measured}
    if mode == "stacking":
        observed = actual.get("subject_on_top") if isinstance(actual, dict) else None
        detail = {"expected_subject_on_top": expected.get("subject_on_top"), "actual_subject_on_top": observed, "actual": actual}
        if observed is None:
            detail["reason"] = "采集器没有得出层叠结论"
            return False, detail
        return observed == expected.get("subject_on_top"), detail
    raise ContractError(f"未知 check_mode：{mode}")
def result_rules(payload: Any, name: str, contract_sha256: str) -> dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, dict) or payload.get("contract_sha256") != contract_sha256:
        raise ContractError(f"{name} 的 contract_sha256 与冻结契约不一致")
    if not isinstance(payload.get("rules", {}), dict):
        raise ContractError(f"{name}.rules 必须是对象")
    return payload.get("rules", {})
def render_outcome(rule: dict[str, Any], render_payload: dict[str, Any] | None, render_rules: dict[str, Any]) -> dict[str, Any]:
    if render_payload is None:
        return {"status": "yellow", "reasons": ["未提供页面能力与结构化渲染结果"], "required_evidence": ["启动页面并注入 collect_restore_facts.js"]}
    if render_payload.get("page_available") is False:
        return {"status": "yellow", "reasons": [f"页面不可用：{render_payload.get('reason', '未说明原因')}"]}
    if render_payload.get("capture_error"):
        return {"status": "red", "actual": {"capture_error": render_payload["capture_error"]}, "reasons": ["结构化渲染已尝试但采集失败"]}
    item = render_rules.get(rule["id"])
    if item is None:
        reason = "页面可用但结构化采集缺本规则结果"
        if render_payload.get("merged_from"):
            reason = f"提供的 {render_payload['merged_from']} 份结构化采集结果都没有覆盖本规则"
        return {"status": "red", "actual": None, "reasons": [reason]}
    status = item.get("status")
    if status in {"missing_fixture", "unavailable"}:
        return {"status": "yellow", "actual": item.get("actual"), "reasons": [item.get("reason") or status]}
    if status != "ok":
        return {"status": "red", "actual": item.get("actual"), "reasons": [item.get("reason") or "结构化采集失败"]}
    expected = expected_for_layer(rule, "render")
    passed, comparison = compare_actual(rule, expected, item.get("actual"))
    if passed:
        return {"status": "green", "actual": item.get("actual")}
    output = {
        "status": "red", "expected": expected, "actual": item.get("actual"),
        "comparison": comparison, "reasons": ["结构化渲染实际值不符合冻结契约"],
    }
    if isinstance(expected, str) and isinstance(item.get("actual"), str):
        output["hint"] = "字符串不等，先目视是否序列化差异"
    return output
def evaluate_rule(
    rule: dict[str, Any], static_rules: dict[str, Any], render_payload: dict[str, Any] | None,
    render_rules: dict[str, Any],
) -> dict[str, Any]:
    base = {"rule_id": rule["id"]}
    if rule.get("frozen_exemption"):
        return {**base, "status": "green", "frozen_exemption": rule["frozen_exemption"]["id"]}
    layers = rule_layers(rule)
    if "visual" in layers:
        return {**base, "status": "yellow", "reasons": ["v2 visual 规则交 acceptance.md 人工目视"]}
    outcomes: list[dict[str, Any]] = []
    if "static" in layers:
        item = static_rules.get(rule["id"])
        if item is None:
            outcomes.append({"status": "red", "actual": None, "reasons": ["静态预检未运行或缺本规则结果"]})
        elif item.get("status") == "pass":
            outcomes.append({"status": "green", "actual": item.get("actual")})
        else:
            outcomes.append({"status": "red", "actual": item.get("actual"), "reasons": [item.get("reason") or "静态预检不通过"]})
    if "render" in layers:
        outcomes.append(render_outcome(rule, render_payload, render_rules))
    status = "red" if any(item["status"] == "red" for item in outcomes) else ("yellow" if any(item["status"] == "yellow" for item in outcomes) else "green")
    if len(outcomes) == 1:
        return {**base, **outcomes[0]}
    active_layers = [layer for layer in layers if layer != "visual"]
    entry: dict[str, Any] = {**base, "status": status, "actual": {layer: item.get("actual") for layer, item in zip(active_layers, outcomes)}}
    reasons = [reason for item in outcomes for reason in item.get("reasons", [])]
    if reasons:
        entry["reasons"] = reasons
    render = next((item for item in outcomes if "comparison" in item), None)
    if render:
        entry.update({key: render[key] for key in ("expected", "comparison", "hint") if key in render})
    return entry
def build_report(
    contract: dict[str, Any], adapter: dict[str, Any], phase: str,
    static_payload: dict[str, Any] | None, render_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    static_rules = result_rules(static_payload, "static-results", contract["contract_sha256"])
    render_rules = result_rules(render_payload, "render-results", contract["contract_sha256"])
    entries = [evaluate_rule(rule, static_rules, render_payload, render_rules) for rule in contract["rules"]]
    counts = {status: sum(item["status"] == status for item in entries) for status in ("red", "yellow", "green")}
    overall = "red" if counts["red"] else ("yellow" if counts["yellow"] else "green")
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": phase,
        "contract_sha256": contract["contract_sha256"],
        "observed": (render_payload or {}).get("observed", {}),
        "overall": overall,
        "summary": {**counts, "total": len(entries)},
        "entries": entries,
    }
def optional_json(path: str | None) -> dict[str, Any] | None:
    return load_json(Path(path).expanduser()) if path else None
def merge_render_payloads(paths: list[str] | None, contract_sha256: str) -> dict[str, Any] | None:
    if not paths:
        return None
    payloads = [(path, load_json(Path(path).expanduser())) for path in paths]
    for path, payload in payloads:
        result_rules(payload, f"render-results({path})", contract_sha256)
    if len(payloads) == 1:
        return payloads[0][1]
    available = [(path, payload) for path, payload in payloads if payload.get("page_available") is not False]
    if not available:
        return {"contract_sha256": contract_sha256, "page_available": False, "reason": "提供的全部结构化采集结果都报页面不可用"}
    merged: dict[str, Any] = {}
    for path, payload in available:
        for rule_id, item in (payload.get("rules") or {}).items():
            if not isinstance(item, dict):
                continue
            candidate = {**item, "source_file": path}
            current = merged.get(rule_id)
            usable = candidate.get("status") not in {"error", "capture_error"}
            if current is None or (current.get("status") in {"error", "capture_error"} and usable):
                merged[rule_id] = candidate
    observations = [payload.get("observed") for _, payload in available if payload.get("observed")]
    observed: dict[str, Any] = observations[0] if len(observations) == 1 else {"captures": observations}
    output: dict[str, Any] = {"contract_sha256": contract_sha256, "page_available": True, "merged_from": len(available), "observed": observed, "rules": merged}
    errors = [payload.get("capture_error") for _, payload in available if payload.get("capture_error")]
    if len(errors) == len(available):
        output["capture_error"] = errors[0]
    return output
def require_recompile_is_allowed(out_path: Path, baseline_path: Path, acknowledged: bool) -> None:
    if acknowledged or not out_path.exists():
        return
    existing = load_json(out_path)
    if not isinstance(existing, dict):
        raise ContractError(f"{out_path} 不是可识别的 restore contract，拒绝覆盖")
    previous = existing.get("baseline_sha256") or (existing.get("baseline") or {}).get("sha256")
    actual = sha256_file(baseline_path)
    if previous and previous != actual:
        raise ContractError(
            f"{out_path} 记录的基线哈希与当前 dev-baseline.md 不同；重新确认后加 --after-reconfirmation"
        )
def archive_stale_reports(out_path: Path, previous_sha256: str | None) -> list[str]:
    if not previous_sha256:
        return []
    archived = []
    for report in sorted(out_path.parent.glob("restore-report-*.json")):
        if ".stale-" in report.name:
            continue
        target = report.with_name(f"{report.stem}.stale-{previous_sha256[:8]}.json")
        suffix = 2
        while target.exists():
            target = report.with_name(f"{report.stem}.stale-{previous_sha256[:8]}-{suffix}.json")
            suffix += 1
        report.rename(target)
        archived.append(str(target))
    return archived
def load_contract_and_adapter(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = validate_contract(load_json(Path(args.contract).expanduser()), Path(args.baseline).expanduser())
    return contract, validate_adapter(load_json(Path(args.adapter).expanduser()), contract)
def command_contract(args: argparse.Namespace) -> int:
    baseline, out = Path(args.baseline).expanduser(), Path(args.out).expanduser()
    require_recompile_is_allowed(out, baseline, args.after_reconfirmation)
    existing = load_json(out) if out.exists() else None
    previous = existing.get("contract_sha256") if isinstance(existing, dict) else None
    contract = compile_contract(baseline, args.rules)
    archived = archive_stale_reports(out, previous) if args.after_reconfirmation and previous != contract["contract_sha256"] else []
    write_json(out, contract)
    print(json.dumps({"status": "written", "out": str(out), "contract_sha256": contract["contract_sha256"], "rules": len(contract["rules"]), "archived_reports": archived}, ensure_ascii=False))
    return EXIT_OK
def command_validate(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    print(json.dumps({"status": "valid", "contract_sha256": contract["contract_sha256"], "rules": len(contract["rules"]), "adapter_rules": len(adapter["rules"])}, ensure_ascii=False))
    return EXIT_OK
def command_static(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    result = run_static_preflight(contract, adapter, Path(args.repo_root).expanduser())
    write_json(Path(args.out).expanduser(), result)
    print(json.dumps({"status": "written", "out": args.out, "rules": len(result["rules"])}, ensure_ascii=False))
    return EXIT_OK
def report_exit_code(phase: str, overall: str) -> int:
    return EXIT_NOT_GREEN if phase == "green" and overall != "green" else EXIT_OK
def command_report(args: argparse.Namespace) -> int:
    contract, adapter = load_contract_and_adapter(args)
    report = build_report(
        contract, adapter, args.phase, optional_json(args.static_results),
        merge_render_payloads(args.render_results, contract["contract_sha256"]),
    )
    write_json(Path(args.out).expanduser(), report)
    print(json.dumps({"status": report["overall"], "out": args.out, "summary": report["summary"]}, ensure_ascii=False))
    return report_exit_code(args.phase, report["overall"])
def add_contract_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--adapter", required=True)
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--baseline", required=True)
    contract.add_argument("--rules", required=True, help="规则 JSON 路径；- 表示 stdin")
    contract.add_argument("--out", required=True)
    contract.add_argument("--after-reconfirmation", action="store_true")
    validate = sub.add_parser("validate")
    add_contract_inputs(validate)
    static = sub.add_parser("static")
    add_contract_inputs(static)
    static.add_argument("--repo-root", required=True)
    static.add_argument("--out", required=True)
    report = sub.add_parser("report")
    add_contract_inputs(report)
    report.add_argument("--phase", choices=("red", "green"), required=True)
    report.add_argument("--static-results")
    report.add_argument("--render-results", action="append")
    report.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        return {
            "contract": command_contract, "validate": command_validate,
            "static": command_static, "report": command_report,
        }[args.command](args)
    except (ContractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR

if __name__ == "__main__":
    raise SystemExit(main())
