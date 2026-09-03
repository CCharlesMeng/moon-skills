#!/usr/bin/env python3
"""Record raw browser scenarios and aggregate independent Phase C reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ROLES = (
    "review-layout",
    "review-convention",
    "review-quality",
    "self-test",
)
# self-test 不在这里：它的 dimension 是分配到的冻结功能行或回归编号（F3-1 / REG-2），
# 没有固定集合，只能靠 aggregate 的 assignment 比对。
ROLE_DIMENSIONS = {
    "review-layout": {f"L{index}" for index in range(1, 7)},
    "review-convention": {f"C{index}" for index in range(1, 8)},
    "review-quality": {f"Q{index}" for index in range(1, 9)},
}
RESTORE_LEVELS = {
    status: {f"R{index}": level for index in range(1, 7)}
    for status, level in (("red", "blocker"), ("yellow", "blocker"), ("green", None))
}
JUDGMENT_KEYS = {
    "finding", "findings", "verdict", "conclusion", "level", "severity",
    "passed", "pass", "failed", "result", "open_questions",
    "deferred_candidates", "user_visible_text",
}
# 静态检视引用的三种形态：仓内范式、Requirement 决策、文件行范围。
# 它们不在证据包里，只能校验形状；BE-n 与命令名必须在包里解析得到。
STATIC_EVIDENCE = re.compile(
    r"PATTERN-[0-9A-Za-z._/-]+|REQ-DEC-[0-9A-Za-z._/-]+|[0-9A-Za-z._/@-]+:L\d+(?:-L?\d+)?"
)


class ReviewPipelineError(RuntimeError):
    """Raised when review evidence or result data is unsafe to reuse."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewPipelineError(f"cannot read JSON {path}: {error}") from error


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReviewPipelineError(f"cannot read {path}: {error}") from error


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewPipelineError(f"{label} must be an object")
    return value


def build_evidence_index(review_evidence: dict[str, Any]) -> set[str]:
    """Collect every evidence id a role is allowed to cite from the shared pack."""
    index: set[str] = set()
    for item in require_list(review_evidence.get("scenarios", []), "review_evidence.scenarios"):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            index.add(item["id"])
    gate = review_evidence.get("quality_gate")
    if isinstance(gate, dict):
        for command in require_list(gate.get("commands", []), "review_evidence.quality_gate.commands"):
            if isinstance(command, dict) and isinstance(command.get("name"), str):
                index.add(command["name"])
    return index


def check_portfolio_floor(portfolio: dict[str, Any], diff_facts: dict[str, Any]) -> list[dict[str, str]]:
    """Every mechanically derived trigger must be carried or explicitly narrowed."""
    floor = set(require_dict(diff_facts.get("risk_triggers", {}), "diff_facts.risk_triggers"))
    declared = {
        require_text(item, f"validation_portfolio.risk_triggers[{index}]")
        for index, item in enumerate(
            require_list(portfolio.get("risk_triggers", []), "validation_portfolio.risk_triggers")
        )
    }
    narrowed: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(
        require_list(portfolio.get("portfolio_narrowed", []), "validation_portfolio.portfolio_narrowed")
    ):
        item = require_dict(raw, f"validation_portfolio.portfolio_narrowed[{index}]")
        trigger = require_text(item.get("trigger"), f"validation_portfolio.portfolio_narrowed[{index}].trigger")
        reason = require_text(item.get("reason"), f"validation_portfolio.portfolio_narrowed[{index}].reason")
        if trigger in declared:
            raise ReviewPipelineError(f"portfolio_narrowed {trigger} is also declared as a trigger")
        if trigger in seen:
            raise ReviewPipelineError(f"duplicate portfolio_narrowed trigger: {trigger}")
        seen.add(trigger)
        narrowed.append({"trigger": trigger, "reason": reason})
    missing = sorted(floor - declared - seen)
    if missing:
        raise ReviewPipelineError(
            "validation portfolio drops mechanically derived triggers without narrowing: "
            f"{missing}"
        )
    return narrowed


def unresolved_evidence(values: list[Any], index: set[str]) -> list[str]:
    """Ids that neither exist in the pack nor take a self-describing static form."""
    return [
        str(value) for value in values
        if value not in index and not (
            isinstance(value, str) and STATIC_EVIDENCE.fullmatch(value)
        )
    ]


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReviewPipelineError(f"{label} must be an array")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewPipelineError(f"{label} must be non-empty text")
    return value


def reject_judgments(value: Any, path: str = "scenario") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in JUDGMENT_KEYS:
                raise ReviewPipelineError(f"raw evidence contains judgment key {path}.{key}")
            reject_judgments(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_judgments(item, f"{path}[{index}]")


def code_hashes(code: dict[str, Any]) -> dict[str, str]:
    base_ref = require_text(code.get("base_ref"), "code.base_ref")
    head = require_text(code.get("head"), "code.head")
    records = require_list(code.get("files"), "code.files")
    hashes: dict[str, str] = {}
    for index, raw in enumerate(records):
        record = require_dict(raw, f"code.files[{index}]")
        path = require_text(record.get("path"), f"code.files[{index}].path")
        digest = require_text(record.get("sha256"), f"code.files[{index}].sha256")
        if path in hashes:
            raise ReviewPipelineError(f"duplicate code path: {path}")
        hashes[path] = digest
    fingerprint = require_text(code.get("code_fingerprint"), "code.code_fingerprint")
    normalized_files = [
        {"path": path, "sha256": hashes[path]} for path in sorted(hashes)
    ]
    expected = sha256({"base_ref": base_ref, "head": head, "files": normalized_files})
    if fingerprint != expected:
        raise ReviewPipelineError(
            f"code.code_fingerprint mismatch: expected {expected}, got {fingerprint}"
        )
    return hashes


def scenario_identity(scenario: dict[str, Any], runtime: dict[str, Any]) -> str:
    identity = {
        "page": scenario.get("page"),
        "fixture": scenario.get("fixture"),
        "viewport": scenario.get("viewport"),
        "steps": scenario.get("steps"),
        "runtime": runtime,
    }
    return sha256(identity)


def stale_dependency_paths(
    scenario: dict[str, Any], current_hashes: dict[str, str]
) -> list[str]:
    depends_on = scenario.get("depends_on")
    captured = scenario.get("captured_dependency_hashes")
    if not isinstance(depends_on, list) or not isinstance(captured, dict):
        return ["dependency-manifest-missing"]
    return sorted(
        path for path in depends_on
        if not isinstance(path, str) or current_hashes.get(path) != captured.get(path)
    )


def scenario_stale_reasons(
    scenario: dict[str, Any], current_hashes: dict[str, str], runtime: dict[str, Any]
) -> list[str]:
    reasons = stale_dependency_paths(scenario, current_hashes)
    if canonical_json(scenario.get("captured_runtime")) != canonical_json(runtime):
        reasons.append("runtime-changed")
    return sorted(set(reasons))


def validate_raw_scenario(
    raw: Any,
    index: int,
    current_hashes: dict[str, str],
    runtime: dict[str, Any],
    source: str,
    label: str = "scenarios",
) -> tuple[dict[str, Any], list[str]]:
    scenario = require_dict(raw, f"{label}[{index}]")
    reject_judgments(scenario, f"{label}[{index}]")
    for field in ("page", "fixture", "viewport", "steps", "observations", "artifacts", "depends_on", "captured_runtime"):
        if field not in scenario:
            raise ReviewPipelineError(f"{label}[{index}] missing {field}")
    require_text(scenario["page"], f"{label}[{index}].page")
    require_dict(scenario["fixture"], f"{label}[{index}].fixture")
    require_dict(scenario["viewport"], f"{label}[{index}].viewport")
    require_list(scenario["steps"], f"{label}[{index}].steps")
    require_list(scenario["observations"], f"{label}[{index}].observations")
    require_list(scenario["artifacts"], f"{label}[{index}].artifacts")
    depends_on = require_list(scenario["depends_on"], f"{label}[{index}].depends_on")
    for dependency_index, dependency in enumerate(depends_on):
        require_text(
            dependency,
            f"{label}[{index}].depends_on[{dependency_index}]",
        )
    if len(set(depends_on)) != len(depends_on):
        raise ReviewPipelineError(f"{label}[{index}] has duplicate depends_on paths")
    captured = require_dict(
        scenario.get("captured_dependency_hashes"),
        f"{label}[{index}].captured_dependency_hashes",
    )
    if not depends_on or set(depends_on) != set(captured):
        raise ReviewPipelineError(
            f"{label}[{index}] dependency hashes must exactly cover depends_on"
        )
    for dependency in depends_on:
        require_text(
            captured[dependency],
            f"{label}[{index}].captured_dependency_hashes[{dependency}]",
        )
    require_dict(scenario["captured_runtime"], f"{label}[{index}].captured_runtime")
    stale = scenario_stale_reasons(scenario, current_hashes, runtime)
    normalized = dict(scenario)
    normalized["scenario_key"] = scenario_identity(normalized, runtime)
    normalized["source"] = source
    return normalized, sorted(stale)


def record_scenarios(
    review_evidence: dict[str, Any],
    code: dict[str, Any],
    additions: list[Any],
    runtime: dict[str, Any],
    source: str = "phase-b",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Append raw scenarios to review-evidence.json and report freshness.

    Called with an empty `additions` list it is a pure freshness check: every
    scenario already in the package is graded against the current code hashes
    and runtime, and nothing is rewritten.
    """
    require_dict(review_evidence, "review_evidence")
    current_hashes = code_hashes(code)

    existing = require_list(review_evidence.get("scenarios", []), "review_evidence.scenarios")
    by_key: dict[str, dict[str, Any]] = {}
    for item in existing:
        record = require_dict(item, "review_evidence.scenarios[]")
        key = record.get("scenario_key") or scenario_identity(record, runtime)
        if key in by_key:
            raise ReviewPipelineError(f"duplicate existing scenario_key: {key}")
        by_key[key] = record

    recorded: list[str] = []
    fresh: list[str] = []
    stale: list[dict[str, Any]] = []
    next_number = 1
    used_ids = {item.get("id") for item in existing if isinstance(item, dict)}
    for index, raw in enumerate(additions):
        scenario, stale_paths = validate_raw_scenario(
            raw, index, current_hashes, runtime, source
        )
        source_id = scenario.get("id") or f"{source}-{index + 1}"
        if stale_paths:
            stale.append({"id": source_id, "reason": stale_paths})
            continue
        key = scenario["scenario_key"]
        if key in by_key:
            existing_id = require_text(by_key[key].get("id"), "existing scenario id")
            if not scenario_stale_reasons(by_key[key], current_hashes, runtime):
                fresh.append(existing_id)
                continue
            scenario["id"] = existing_id
            scenario["recorded_at_code_fingerprint"] = code["code_fingerprint"]
            by_key[key] = scenario
            recorded.append(existing_id)
            continue
        while f"BE-{next_number}" in used_ids:
            next_number += 1
        scenario["id"] = f"BE-{next_number}"
        scenario["recorded_at_code_fingerprint"] = code["code_fingerprint"]
        used_ids.add(scenario["id"])
        by_key[key] = scenario
        recorded.append(scenario["id"])

    added_keys = set()
    for identifier in recorded + fresh:
        for key, record in by_key.items():
            if record.get("id") == identifier:
                added_keys.add(key)
    for key, record in by_key.items():
        if key in added_keys:
            continue
        identifier = require_text(record.get("id"), "existing scenario id")
        reasons = scenario_stale_reasons(record, current_hashes, runtime)
        if reasons:
            stale.append({"id": identifier, "reason": reasons})
        else:
            fresh.append(identifier)

    output = dict(review_evidence)
    output.setdefault("schema_version", SCHEMA_VERSION)
    output["code"] = code
    output["runtime"] = runtime
    output["scenarios"] = sorted(by_key.values(), key=lambda item: item.get("id", ""))
    return output, {
        "recorded": recorded,
        "fresh": sorted(set(fresh)),
        "stale": sorted(stale, key=lambda item: item["id"]),
    }


def validate_common_item(item: dict[str, Any], label: str, fields: tuple[str, ...]) -> None:
    for field in fields:
        if field not in item:
            raise ReviewPipelineError(f"{label} missing {field}")
        if field == "needs_decision":
            if not isinstance(item[field], bool):
                raise ReviewPipelineError(f"{label}.needs_decision must be boolean")
        else:
            require_text(item[field], f"{label}.{field}")
    require_text(item.get("id"), f"{label}.id")
    require_text(item.get("canonical_key"), f"{label}.canonical_key")
    evidence_ids = require_list(item.get("evidence_ids"), f"{label}.evidence_ids")
    if not evidence_ids:
        raise ReviewPipelineError(f"{label}.evidence_ids must not be empty")


def validate_evidence_addition(raw: Any, label: str) -> None:
    scenario = require_dict(raw, label)
    reject_judgments(scenario, label)
    require_text(scenario.get("id"), f"{label}.id")
    for field in (
        "page", "fixture", "viewport", "steps", "observations", "artifacts",
        "depends_on", "captured_dependency_hashes", "captured_runtime",
    ):
        if field not in scenario:
            raise ReviewPipelineError(f"{label} missing {field}")


def validate_review_result(raw: Any, expected_role: str | None = None) -> dict[str, Any]:
    result = require_dict(raw, "review result")
    if result.get("schema_version") != SCHEMA_VERSION:
        raise ReviewPipelineError("review result schema_version must be 1")
    role = require_text(result.get("role"), "review result role")
    if role not in ROLES or (expected_role and role != expected_role):
        raise ReviewPipelineError(f"unexpected review role: {role}")
    require_text(result.get("evidence_epoch"), f"{role}.evidence_epoch")
    require_text(result.get("code_fingerprint"), f"{role}.code_fingerprint")
    status = result.get("status")
    if status not in {"executed", "not_applicable", "unexecuted"}:
        raise ReviewPipelineError(f"{role}.status is invalid")
    coverage = require_list(result.get("coverage"), f"{role}.coverage")
    skipped = require_list(result.get("skipped", []), f"{role}.skipped")
    judged_files = require_list(result.get("judged_files", []), f"{role}.judged_files")
    findings = require_list(result.get("findings"), f"{role}.findings")
    questions = require_list(result.get("open_questions"), f"{role}.open_questions")
    deferred = require_list(result.get("deferred_candidates"), f"{role}.deferred_candidates")
    gaps = require_list(result.get("known_gaps"), f"{role}.known_gaps")
    evidence_reused = require_list(result.get("evidence_reused"), f"{role}.evidence_reused")
    evidence_added = require_list(result.get("evidence_added"), f"{role}.evidence_added")
    for index, addition in enumerate(evidence_added):
        validate_evidence_addition(addition, f"{role}.evidence_added[{index}]")
    if status != "executed":
        if (
            coverage or skipped or findings or questions or deferred
            or judged_files or evidence_reused or evidence_added or not gaps
        ):
            raise ReviewPipelineError(f"{role} non-executed result must only explain known_gaps")
        return result

    # judged_files 是判断的失效键：修复只落在集合外时本份判断存活，落在集合内才重判。
    # 空集合会让「任何修复都不影响我」成立，所以 executed 必须给出非空集合。
    if not judged_files:
        raise ReviewPipelineError(f"{role} executed result must list judged_files")
    for index, path in enumerate(judged_files):
        require_text(path, f"{role}.judged_files[{index}]")
    if len(set(judged_files)) != len(judged_files):
        raise ReviewPipelineError(f"{role} judged_files contains duplicate paths")

    dimensions: set[str] = set()
    for index, raw_coverage in enumerate(coverage):
        item = require_dict(raw_coverage, f"{role}.coverage[{index}]")
        dimension = require_text(item.get("dimension"), f"{role}.coverage[{index}].dimension")
        if dimension in dimensions:
            raise ReviewPipelineError(f"duplicate coverage dimension {role}:{dimension}")
        dimensions.add(dimension)
        require_text(item.get("scope"), f"{role}.coverage[{index}].scope")
        evidence_ids = require_list(
            item.get("evidence_ids"), f"{role}.coverage[{index}].evidence_ids"
        )
        if item.get("result") not in {"clear", "finding", "unrun"}:
            raise ReviewPipelineError(f"invalid coverage result {role}:{dimension}")
        # `clear` 是唯一能把声明推向 PROVEN 的维度结论，所以它必须自带可复核证据。
        # 不然「认真看过没问题」和「没看懂就说没问题」在结构上无法区分。
        if item["result"] == "clear" and not evidence_ids:
            raise ReviewPipelineError(
                f"{role} coverage {dimension} is clear but cites no evidence"
            )
    if role in ROLE_DIMENSIONS and not dimensions <= ROLE_DIMENSIONS[role]:
        extra = sorted(dimensions - ROLE_DIMENSIONS[role])
        raise ReviewPipelineError(f"{role} coverage contains unknown dimensions: {extra}")

    # A dimension that hits skip_when was looked at and ruled out; that is a
    # different fact from `unrun`, and the human needs to see it. It still has
    # to be one of the assigned dimensions, and it cannot also claim coverage.
    skipped_dimensions: set[str] = set()
    for index, raw_skip in enumerate(skipped):
        item = require_dict(raw_skip, f"{role}.skipped[{index}]")
        dimension = require_text(item.get("dimension"), f"{role}.skipped[{index}].dimension")
        require_text(item.get("reason"), f"{role}.skipped[{index}].reason")
        if dimension in skipped_dimensions:
            raise ReviewPipelineError(f"duplicate skipped dimension {role}:{dimension}")
        if dimension in dimensions:
            raise ReviewPipelineError(f"{role} reports {dimension} as both covered and skipped")
        skipped_dimensions.add(dimension)
    if role in ROLE_DIMENSIONS and not skipped_dimensions <= ROLE_DIMENSIONS[role]:
        extra = sorted(skipped_dimensions - ROLE_DIMENSIONS[role])
        raise ReviewPipelineError(f"{role} skipped contains unknown dimensions: {extra}")
    if role == "self-test" and not dimensions and not skipped_dimensions:
        raise ReviewPipelineError("self-test executed result must cover assigned claim dimensions")

    ids: set[str] = set()
    for index, raw_finding in enumerate(findings):
        item = require_dict(raw_finding, f"{role}.findings[{index}]")
        validate_common_item(
            item,
            f"{role}.findings[{index}]",
            ("dimension", "level", "summary", "location", "basis", "impact", "suggested_action"),
        )
        if item["level"] not in {"blocker", "suggestion"}:
            raise ReviewPipelineError(f"invalid finding level: {item['level']}")
        if item["id"] in ids:
            raise ReviewPipelineError(f"duplicate item id in {role}: {item['id']}")
        ids.add(item["id"])
    for collection, label, fields in (
        (questions, "open_questions", ("summary", "needs_decision")),
        (deferred, "deferred_candidates", ("ac", "reason", "resume_condition")),
    ):
        for index, raw_item in enumerate(collection):
            item = require_dict(raw_item, f"{role}.{label}[{index}]")
            validate_common_item(item, f"{role}.{label}[{index}]", fields)
            if item["id"] in ids:
                raise ReviewPipelineError(f"duplicate item id in {role}: {item['id']}")
            ids.add(item["id"])
    if any(item["result"] == "unrun" for item in coverage) and not gaps:
        raise ReviewPipelineError(f"{role} unrun coverage requires known_gaps")
    return result


def merge_findings(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        role = result["role"]
        for item in result["findings"]:
            key = item["canonical_key"]
            if key not in merged:
                merged[key] = {**item, "roles": [role], "source_ids": [item["id"]]}
                continue
            current = merged[key]
            for field in ("summary", "location", "impact", "suggested_action"):
                if current[field] != item[field]:
                    raise ReviewPipelineError(
                        f"canonical_key conflict for {key}: incompatible {field}"
                    )
            current["roles"] = sorted(set(current["roles"] + [role]))
            current["source_ids"] = sorted(set(current["source_ids"] + [item["id"]]))
            current["evidence_ids"] = sorted(set(current["evidence_ids"] + item["evidence_ids"]))
            current["basis"] = "；".join(dict.fromkeys([current["basis"], item["basis"]]))
            if item["level"] == "blocker":
                current["level"] = "blocker"
    return sorted(merged.values(), key=lambda item: (item["level"] != "blocker", item["canonical_key"]))


def merge_named(results: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for item in result[field]:
            key = item["canonical_key"]
            if key in merged and merged[key]["summary"] != item["summary"]:
                raise ReviewPipelineError(f"canonical_key conflict for {key}: incompatible summary")
            if key not in merged:
                merged[key] = {**item, "roles": [result["role"]], "source_ids": [item["id"]]}
            else:
                merged[key]["roles"] = sorted(set(merged[key]["roles"] + [result["role"]]))
                merged[key]["source_ids"] = sorted(set(merged[key]["source_ids"] + [item["id"]]))
                merged[key]["evidence_ids"] = sorted(set(merged[key]["evidence_ids"] + item["evidence_ids"]))
    return [merged[key] for key in sorted(merged)]


def merge_evidence_additions(
    review_evidence: dict[str, Any], results: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge raw reviewer additions and rewrite provisional evidence references."""
    evidence = require_dict(review_evidence, "review_evidence")
    code = require_dict(evidence.get("code"), "review_evidence.code")
    current_hashes = code_hashes(code)
    runtime = require_dict(evidence.get("runtime"), "review_evidence.runtime")
    existing = require_list(evidence.get("scenarios", []), "review_evidence.scenarios")
    by_key: dict[str, dict[str, Any]] = {}
    used_ids: set[str] = set()
    for raw in existing:
        scenario = require_dict(raw, "review_evidence.scenarios[]")
        identifier = require_text(scenario.get("id"), "review_evidence scenario id")
        key = scenario.get("scenario_key") or scenario_identity(scenario, runtime)
        if key in by_key:
            raise ReviewPipelineError(f"duplicate existing scenario_key: {key}")
        by_key[key] = scenario
        used_ids.add(identifier)

    validated = [validate_review_result(result) for result in results]
    evidence_epoch = require_text(evidence.get("evidence_epoch"), "review_evidence.evidence_epoch")
    for result in validated:
        if result["evidence_epoch"] != evidence_epoch:
            raise ReviewPipelineError(
                f"{result['role']} evidence_epoch does not match review_evidence"
            )
        if result["code_fingerprint"] != code["code_fingerprint"]:
            raise ReviewPipelineError(
                f"{result['role']} code_fingerprint does not match review_evidence"
            )
    pending: list[tuple[str, str, str, dict[str, Any]]] = []
    for result in validated:
        role = result["role"]
        for index, raw in enumerate(result["evidence_added"]):
            provisional = require_text(raw.get("id"), f"{role}.evidence_added[{index}].id")
            scenario, stale_paths = validate_raw_scenario(
                raw, index, current_hashes, runtime, role, f"{role}.evidence_added"
            )
            if stale_paths:
                raise ReviewPipelineError(
                    f"{role} evidence addition {provisional} is stale: {stale_paths}"
                )
            pending.append((role, provisional, scenario["scenario_key"], scenario))

    mapping: dict[tuple[str, str], str] = {}
    next_number = 1
    for role, provisional, key, scenario in sorted(pending, key=lambda item: (item[2], item[0], item[1])):
        if key in by_key and not scenario_stale_reasons(by_key[key], current_hashes, runtime):
            final_id = require_text(by_key[key].get("id"), "existing scenario id")
        else:
            if key in by_key:
                final_id = require_text(by_key[key].get("id"), "existing scenario id")
            else:
                while f"BE-{next_number}" in used_ids:
                    next_number += 1
                final_id = f"BE-{next_number}"
            scenario["id"] = final_id
            scenario["source"] = role
            scenario["merged_at_code_fingerprint"] = code["code_fingerprint"]
            by_key[key] = scenario
            used_ids.add(final_id)
        mapping[(role, provisional)] = final_id

    rewritten: list[dict[str, Any]] = []
    for result in validated:
        role = result["role"]
        copy = {**result, "evidence_added": []}
        copy["evidence_reused"] = sorted(set(
            result["evidence_reused"]
            + [mapping[(role, item["id"])] for item in result["evidence_added"]]
        ))
        for field in ("coverage", "findings", "open_questions", "deferred_candidates"):
            copy[field] = []
            for original in result[field]:
                item = dict(original)
                item["evidence_ids"] = [mapping.get((role, identifier), identifier) for identifier in item["evidence_ids"]]
                copy[field].append(item)
        rewritten.append(copy)

    output = dict(evidence)
    output["scenarios"] = sorted(by_key.values(), key=lambda item: item.get("id", ""))
    return output, rewritten


NORM_CANDIDATE_KINDS = {"broken", "new-pattern", "exemption-recurring", "runtime-trap"}


def validate_norm_candidates(raw: Any) -> list[dict[str, Any]]:
    """校验规范候选：Dev 发现的仓库级事实变化，回流给 `sdd-init-frontend`。

    这条通道此前只存在于散文里——`recon-codebase` 会回传「规范待确认」，规则说攒进
    `acceptance.md` 由 init 重新归纳，但 `acceptance.md` 没有这一节、聚合器的 handoff
    也只有 suggestion / open_question / deferred 三类，装不下它。结果是一句「攒进
    handoff」到不了任何人手里。

    三条校验是这个通道能用的前提：

    - **必须点名依据样本。** init 归纳规范要的就是「看了哪几处」；只说「这条规范
      不成立了」而不给样本，维护者得从零重扫，那还不如没有这条回流。
    - **必须指名 `target_id`（`broken` 与 `exemption-recurring`）。** 说不出质疑的是
      哪一条，就没法判断它是同一条的第 n 次复发还是一条新发现——而复发计数正是
      init 决定要不要动规范节的唯一依据。
    - **`runtime-trap` 必须附可复现现象。** 这类知识的根因在第三方库或构建工具的
      运行行为里，代码样本撑不住根因；没有现象，init 无法在门槛 1 次时落规范。

    刻意**不**要求样本数 ≥ 2：跨 Story 的复发计数只有 init 能做，单个 Story 手里
    永远只有自己那一次。在这里卡门槛等于把计数依据吞掉。`runtime-trap` 的门槛是
    1 次，补偿约束就是现象字段，不是样本数。
    """
    items = require_list(raw, "norm_candidates")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(items):
        label = f"norm_candidates[{index}]"
        item = require_dict(entry, label)
        item_id = require_text(item.get("id"), f"{label}.id")
        if item_id in seen:
            raise ReviewPipelineError(f"duplicate norm candidate id: {item_id}")
        seen.add(item_id)
        kind = item.get("kind")
        if kind not in NORM_CANDIDATE_KINDS:
            raise ReviewPipelineError(
                f"{label}.kind must be one of {sorted(NORM_CANDIDATE_KINDS)}"
            )
        require_text(item.get("claim"), f"{label}.claim")
        samples = require_list(item.get("samples"), f"{label}.samples")
        if not samples:
            raise ReviewPipelineError(f"{label}.samples must not be empty")
        for sample_index, sample in enumerate(samples):
            require_text(sample, f"{label}.samples[{sample_index}]")
        if kind in {"broken", "exemption-recurring"}:
            require_text(item.get("target_id"), f"{label}.target_id")
        if kind == "runtime-trap":
            require_text(item.get("phenomenon"), f"{label}.phenomenon")
        validated.append(item)
    return validated


def validate_decisions(raw: Any) -> list[dict[str, Any]]:
    """校验用户对待决项的答复，让答复就地落回 `acceptance.md`。

    原先待决项（规范候选、未决问题、暂缓）只被「报出来」：P7 说攒批上报，但**答复没有
    任何落点**。于是同一件事下一轮会被再问一遍，而「当时为什么这么定」下个月没人说得清。
    Phase A2 的确认早就记进 `dev-baseline.md` 的「确认记录」与「变更记录」了，收口这侧
    一直缺同样的东西。

    `item` 必须对得上某条 handoff 的 `id`，否则记下的是一个无主的答复；这条由
    `aggregate` 在渲染前校验。
    """
    items = require_list(raw, "decisions")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(items):
        label = f"decisions[{index}]"
        item = require_dict(entry, label)
        for field in ("item", "answer", "decided_at"):
            require_text(item.get(field), f"{label}.{field}")
        validated.append(item)
    return validated


def validate_unplanned_carry(raw: Any) -> list[dict[str, Any]]:
    """校验计划外承接：Dev 直接承接的、计划文件清单之外的连带改动。

    这条通道原先有个覆盖 bug：共享执行契约要求「在 `alpha-tests.md` 与 `acceptance.md`
    登记」，而 `acceptance.md` 由聚合器 `atomic_write` **整文件覆盖**——Phase B 手写进去的
    登记会被 Phase C 冲掉，Phase D 再跑一次 aggregate 又冲一次。两个写入者、一个文件、
    没有裁决规则，和这个仓修过的「末步两次写入不是原子的」是同一类。

    现在的分工：**`alpha-tests.md` 是权威登记**（agent 写、脚本只读），聚合器用
    `project_alpha_tests` 直接读它的表并渲染一份摘要进 `acceptance.md`。每个文件只有一个
    写入者，覆盖问题从构造上消失；JSON 形态只留给没有账本的调用方。

    只要求契约明写的那两项（文件、原因）加模板已有的 Task。**不收「失效了哪些证据」**——
    契约说「被承接的文件同样进入依赖闭包与失效判断」，那是 `depends_on` 算出来的，
    再让人手填一份就是同一事实的第二个来源。
    """
    items = require_list(raw, "unplanned_carry")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(items):
        label = f"unplanned_carry[{index}]"
        item = require_dict(entry, label)
        for field in ("file", "task", "reason"):
            require_text(item.get(field), f"{label}.{field}")
        validated.append(item)
    return validated


# 声明状态只有这三个，与 references/execution-contract.md 的状态表同一套。
# `MANUAL` 不在其中：人工验收是验证方法，不是第四种状态。
CLAIM_STATUSES = ("PROVEN", "UNVERIFIED", "DEFERRED")
MANUAL_OUTCOMES = ("NOT_RUN", "PASSED", "FAILED")
MANUAL_BASES = (
    "visual_judgment",
    "motion_judgment",
    "device_dependency",
    "external_dependency",
    "content_approval",
    "automation_cost_exception",
)
# 人工执行结果与声明状态是两根轴，只有这五种配对合法。缺了这张表，
# 「人看过了」就能直接写成 PROVEN，而三态状态机里没有任何东西挡得住它。
MANUAL_PAIRS = {
    ("PASSED", "PROVEN"),
    ("PASSED", "UNVERIFIED"),   # 人判过了但证据不齐，先补证据
    ("FAILED", "UNVERIFIED"),   # 确证阻断，不许写成通过
    ("NOT_RUN", "UNVERIFIED"),  # 计划态与待执行态
    ("NOT_RUN", "DEFERRED"),    # 外部依赖未就绪
}


def validate_manual_acceptance(raw: Any) -> list[dict[str, Any]]:
    """校验待人工验收项的投影。

    权威登记在 `alpha-tests.md`；`--alpha-tests` 时由 `project_alpha_tests` 读表投影到这里，
    否则接受调用方给的 JSON。两条路进的都是同一形状，校验只写一遍。表头按
    `references/templates/story-artifacts.md` 固定，漂移在解析处报错而不是在人手投影里静默丢字段。

    省略参数按零人工项处理，v1 Story 因此天然兼容，不需要「无人工节」特判。

    人工验收是这条流水线里唯一没有可复算外部产物的证据：命令能重跑、契约能重判，
    而「人看过了」不能。所以 `PROVEN` 的门在这里收得比别处紧——执行人、执行时间、
    环境和至少一条证据引用四项齐全才放过，缺一项就退回 `UNVERIFIED`。
    """
    items = require_list(raw, "manual_acceptance")
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(items):
        label = f"manual_acceptance[{index}]"
        item = require_dict(entry, label)
        for field in ("id", "trace", "verification_scope", "manual_basis",
                      "required_environment", "required_evidence"):
            require_text(item.get(field), f"{label}.{field}")
        if item["manual_basis"] not in MANUAL_BASES:
            raise ReviewPipelineError(
                f"{label}.manual_basis must be one of {list(MANUAL_BASES)}, got {item['manual_basis']!r}"
            )
        outcome = item.get("manual_outcome")
        status = item.get("claim_status")
        if outcome not in MANUAL_OUTCOMES:
            raise ReviewPipelineError(
                f"{label}.manual_outcome must be one of {list(MANUAL_OUTCOMES)}, got {outcome!r}"
            )
        if status not in CLAIM_STATUSES:
            raise ReviewPipelineError(
                f"{label}.claim_status must be one of {list(CLAIM_STATUSES)}, got {status!r}"
            )
        if (outcome, status) not in MANUAL_PAIRS:
            raise ReviewPipelineError(
                f"{label} illegal pairing {outcome} + {status}; "
                f"manual_outcome and claim_status are separate axes and cannot substitute for each other"
            )
        evidence_refs = item.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            raise ReviewPipelineError(f"{label}.evidence_refs must be a list")
        if status == "PROVEN":
            for field in ("manual_checked_by", "manual_checked_at"):
                require_text(item.get(field), f"{label}.{field}")
            if not evidence_refs:
                raise ReviewPipelineError(
                    f"{label} is PROVEN but carries no evidence_refs; "
                    f"a human signature without an artifact is not evidence"
                )
        if status == "DEFERRED":
            require_text(item.get("resume_condition"), f"{label}.resume_condition")
        validated.append(item)
    return validated


# ---------------------------------------------------------------- Markdown 账本投影
#
# 权威登记在 alpha-tests.md / tasks.md（agent 写）。原先要求 agent 把表投影成 JSON 再传进来，
# 那是一次「同一事实的手工搬运」，搬错了脚本也校不出来。现在脚本直接读两份 Markdown，
# 列名固定按 references/templates/story-artifacts.md 与 sdd-task-frontend 的模板；表头漂移
# 在这里报错，比在人手投影里静默漂移要好。

def parse_markdown_table(markdown: str, heading: str) -> list[dict[str, str]]:
    """Rows of the first pipe table under `## <heading>` (any heading depth)."""
    section = re.search(rf"^#{{2,3}}\s+{re.escape(heading)}\s*$(.*?)(?=^#{{2,3}}\s|\Z)", markdown, re.M | re.S)
    if not section:
        return []
    lines = [line.strip() for line in section.group(1).splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            raise ReviewPipelineError(
                f"alpha-tests table '{heading}': row has {len(cells)} cells, header has {len(header)}: {line}"
            )
        rows.append(dict(zip(header, cells)))
    return rows


def _cell(row: dict[str, str], column: str, table: str) -> str:
    if column not in row:
        raise ReviewPipelineError(f"table '{table}' lacks column '{column}'; keep the template header")
    value = row[column].strip()
    return "" if value in {"—", "-", "无", ""} else value


def _split_refs(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,，;；]", value) if item.strip()]


def claim_scopes_from_tasks(tasks_md: str) -> dict[str, str]:
    """AT → verification_scope from tasks.md 用例追溯，the single author of that field."""
    scopes: dict[str, str] = {}
    for row in parse_markdown_table(tasks_md, "用例追溯"):
        at = _cell(row, "AT", "用例追溯")
        if at:
            scopes[at] = _cell(row, "验证范围", "用例追溯")
    return scopes


def project_alpha_tests(
    alpha_md: str, tasks_md: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """(unplanned_carry, manual_acceptance, claim_ledger) projected from the ledger, already validated."""
    carry = [
        {
            "file": _cell(row, "文件", "计划外承接"),
            "task": _cell(row, "Task", "计划外承接"),
            "reason": _cell(row, "原因", "计划外承接"),
        }
        for row in parse_markdown_table(alpha_md, "计划外承接")
    ]
    manual_rows = parse_markdown_table(alpha_md, "人工验收记录")
    manual: list[dict[str, Any]] = []
    if manual_rows:
        if tasks_md is None:
            raise ReviewPipelineError("人工验收记录 present but --tasks not given; verification_scope lives in tasks.md")
        scopes = claim_scopes_from_tasks(tasks_md)
        resume = {
            _cell(row, "AT", "Deferred"): _cell(row, "解除条件", "Deferred")
            for row in parse_markdown_table(alpha_md, "Deferred")
        }
        for row in manual_rows:
            at = _cell(row, "声明", "人工验收记录")
            if at not in scopes:
                raise ReviewPipelineError(f"人工验收记录 {at}: no such AT in tasks.md 用例追溯")
            item: dict[str, Any] = {
                "id": at,
                "trace": _cell(row, "追溯", "人工验收记录"),
                "verification_scope": scopes[at],
                "manual_basis": _cell(row, "依据", "人工验收记录"),
                "required_environment": _cell(row, "验收环境", "人工验收记录"),
                "required_evidence": _cell(row, "需留下的证据", "人工验收记录"),
                "manual_outcome": _cell(row, "人工结果", "人工验收记录"),
                "claim_status": _cell(row, "声明状态", "人工验收记录"),
                "evidence_refs": _split_refs(_cell(row, "证据引用", "人工验收记录")),
            }
            for column, field in (("验收人", "manual_checked_by"), ("验收时间", "manual_checked_at")):
                value = _cell(row, column, "人工验收记录")
                if value:
                    item[field] = value
            if item["claim_status"] == "DEFERRED" and resume.get(at):
                item["resume_condition"] = resume[at]
            manual.append(item)
    return validate_unplanned_carry(carry), validate_manual_acceptance(manual), project_claim_ledger(alpha_md)


PROFILE_ORDER = ("mock", "contract", "live")


def project_claim_ledger(alpha_md: str) -> list[dict[str, Any]]:
    """AC ↔ 证据映射 + Deferred → one row per AT with status, actual profile and external dependency.

    The 执行环境 column is what lets a mock pass and a live pass stop sharing one PROVEN:
    it is compared against the portfolio's required_profile in `check_claim_profiles`.
    Ledgers written before that column existed project with actual_profile=None and skip the gate.
    """
    rows = parse_markdown_table(alpha_md, "AC ↔ 证据映射")
    deferred = {
        _cell(row, "AT", "Deferred"): {
            "external_dependency": _cell(row, "外部依赖", "Deferred"),
            "resume_condition": _cell(row, "解除条件", "Deferred"),
            "resume_entry": _cell(row, "恢复入口", "Deferred"),
        }
        for row in parse_markdown_table(alpha_md, "Deferred")
    }
    ledger: list[dict[str, Any]] = []
    for row in rows:
        at = _cell(row, "AT", "AC ↔ 证据映射")
        if not at:
            continue
        status = _cell(row, "状态", "AC ↔ 证据映射")
        if status not in CLAIM_STATUSES:
            raise ReviewPipelineError(f"AC ↔ 证据映射 {at}: 状态 must be one of {list(CLAIM_STATUSES)}, got {status!r}")
        actual = row.get("执行环境", "").strip() if "执行环境" in row else None
        actual = None if actual in {"", "—", "-"} else actual
        if actual is not None and actual not in PROFILE_ORDER:
            raise ReviewPipelineError(f"AC ↔ 证据映射 {at}: 执行环境 must be one of {list(PROFILE_ORDER)}, got {actual!r}")
        item: dict[str, Any] = {
            "id": at,
            "claim_status": status,
            "actual_profile": actual,
            "evidence": _cell(row, "证据记录", "AC ↔ 证据映射"),
            "note": row.get("说明", "").strip(),
        }
        if status == "DEFERRED":
            if at not in deferred:
                raise ReviewPipelineError(f"AC ↔ 证据映射 {at} is DEFERRED but has no row in the Deferred table")
            item.update(deferred[at])
        ledger.append(item)
    return ledger


def check_claim_profiles(ledger: list[dict[str, Any]], portfolio: dict[str, Any]) -> None:
    """PROVEN needs actual_profile ≥ required_profile. Below that the honest value is UNVERIFIED or DEFERRED."""
    required = {
        claim["id"]: claim.get("required_profile")
        for claim in portfolio.get("claims", [])
        if isinstance(claim, dict) and claim.get("id")
    }
    for item in ledger:
        need = required.get(item["id"])
        if need is None or item["actual_profile"] is None or item["claim_status"] != "PROVEN":
            continue
        if PROFILE_ORDER.index(item["actual_profile"]) < PROFILE_ORDER.index(need):
            raise ReviewPipelineError(
                f"{item['id']} is PROVEN with actual_profile={item['actual_profile']} but the portfolio requires "
                f"{need}; a mock pass does not prove a live seam — record UNVERIFIED or DEFERRED"
            )


def manual_is_settled(item: dict[str, Any]) -> bool:
    """只有「人判过、通过、证据齐」才算收口；其余都还欠一个动作。"""
    return item.get("manual_outcome") == "PASSED" and item.get("claim_status") == "PROVEN"


def manual_action_text(item: dict[str, Any]) -> str:
    """把人工项翻成一句「要谁做什么」。

    三种未收口形态要的动作完全不同，写成同一句话读的人就得自己去账本里分辨：
    没执行的要去执行，判过但证据不齐的要去补证据，失败的要去修。
    """
    outcome = item.get("manual_outcome")
    status = item.get("claim_status")
    if outcome == "FAILED":
        action = "人工验收未通过，先修复再复验"
    elif outcome == "PASSED":
        action = f"人工已判通过但证据不齐，补齐{item['required_evidence']}后才能记为已验证"
    elif status == "DEFERRED":
        action = f"外部依赖未就绪，解除条件：{item['resume_condition']}"
    else:
        action = f"待人工验收，环境：{item['required_environment']}；需留下{item['required_evidence']}"
    return f"{item['id']}（{item['trace']}）{action}"


def restore_report_result(raw: Any) -> dict[str, Any] | None:
    """Turn the final GREEN report into the same findings shape as a review role."""
    if raw is None:
        return None
    report = require_dict(raw, "restore-report-green.json")
    if report.get("phase") != "green":
        raise ReviewPipelineError("restore report used at aggregate must have phase=green")
    contract_sha = require_text(report.get("contract_sha256"), "restore report contract_sha256")
    entries = require_list(report.get("entries"), "restore report entries")
    observed = report.get("observed") if isinstance(report.get("observed"), dict) else {}
    route = observed.get("route") or "见 restore-report-green.json"
    findings = []
    for index, raw_entry in enumerate(entries):
        entry = require_dict(raw_entry, f"restore report entries[{index}]")
        rule_id = require_text(entry.get("rule_id"), f"restore report entries[{index}].rule_id")
        dimension = rule_id.split("-", 1)[0]
        status = entry.get("status")
        if status not in RESTORE_LEVELS or dimension not in RESTORE_LEVELS[status]:
            raise ReviewPipelineError(f"invalid restore report entry {rule_id}: {status}")
        level = RESTORE_LEVELS[status][dimension]
        if level is None:
            continue
        reasons = "；".join(str(item) for item in entry.get("reasons", [])) or "未说明原因"
        expected = json.dumps(entry.get("expected"), ensure_ascii=False, sort_keys=True)
        actual = json.dumps(entry.get("actual"), ensure_ascii=False, sort_keys=True)
        findings.append({
            "id": rule_id,
            "canonical_key": f"restore:{rule_id}",
            "dimension": dimension,
            "level": level,
            "summary": f"冻结还原规则 {rule_id} 为 {status.upper()}：{reasons}",
            "location": route,
            "basis": f"契约 {contract_sha[:8]}；expected={expected}；actual={actual}",
            "evidence_ids": [f"restore:{rule_id}"],
            "impact": f"冻结基线 {entry.get('baseline_id', rule_id)} 尚不能判为满足",
            "suggested_action": (
                "按报告实际值修复实现并重跑同一契约"
                if status == "red"
                else "按报告原因补齐页面、fixture 或结构化采集后重跑"
            ),
        })
    return {
        "role": "restore-contract",
        "findings": findings,
        "summary": report.get("summary", {}),
        "overall": report.get("overall"),
        "contract_sha256": contract_sha,
    }


def aggregate_results(
    results: list[dict[str, Any]],
    expected_roles: list[str] | tuple[str, ...] | None = None,
    expected_dimensions: dict[str, list[str] | tuple[str, ...] | set[str]] | None = None,
    evidence_epoch: str | None = None,
    code_fingerprint: str | None = None,
    evidence_index: set[str] | None = None,
    code_files: set[str] | None = None,
    skip_rebuttals: dict[str, list[Any]] | None = None,
    norm_candidates: list[dict[str, Any]] | None = None,
    unplanned_carry: list[dict[str, Any]] | None = None,
    manual_acceptance: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    claim_ledger: list[dict[str, Any]] | None = None,
    restore_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validated = [validate_review_result(item) for item in results]
    if skip_rebuttals:
        # 「看过且不适用」只有在 diff 事实不反驳它时才成立。diff 明确触碰了该类别时
        # skipped 不再是一个合法出口，判不了就走 coverage `unrun` + known_gaps。
        for result in validated:
            for item in result.get("skipped", []):
                evidence = skip_rebuttals.get(item["dimension"])
                if evidence:
                    raise ReviewPipelineError(
                        f"{result['role']} skipped {item['dimension']} but the diff touches it: "
                        f"{[fact.get('evidence') for fact in evidence if isinstance(fact, dict)][:2]}"
                    )
    if code_files is not None:
        for result in validated:
            outside = sorted(set(result.get("judged_files", [])) - code_files)
            if outside:
                raise ReviewPipelineError(
                    f"{result['role']} judged_files outside the reviewed code state: {outside}"
                )
    if evidence_index is not None:
        for result in validated:
            role = result["role"]
            for item in result["coverage"]:
                missing = unresolved_evidence(item["evidence_ids"], evidence_index)
                if missing:
                    raise ReviewPipelineError(
                        f"{role} coverage {item['dimension']} cites unresolvable evidence: {missing}"
                    )
            for field in ("findings", "open_questions", "deferred_candidates"):
                for item in result[field]:
                    missing = unresolved_evidence(item["evidence_ids"], evidence_index)
                    if missing:
                        raise ReviewPipelineError(
                            f"{role}.{field} {item['id']} cites unresolvable evidence: {missing}"
                        )
    by_role = {item["role"]: item for item in validated}
    if len(by_role) != len(validated):
        raise ReviewPipelineError("aggregate contains duplicate role results")
    expected = list(by_role) if expected_roles is None else list(expected_roles)
    if len(set(expected)) != len(expected) or any(role not in ROLES for role in expected):
        raise ReviewPipelineError(f"invalid expected review roles: {sorted(expected)}")
    if set(by_role) != set(expected):
        raise ReviewPipelineError(
            f"aggregate roles mismatch: expected={sorted(expected)}, actual={sorted(by_role)}"
        )
    if expected_dimensions is not None:
        if set(expected_dimensions) != set(expected):
            raise ReviewPipelineError(
                "review dimension assignments must match expected review roles"
            )
        for role in expected:
            assigned_values = list(expected_dimensions[role])
            assigned = set(assigned_values)
            if not assigned or len(assigned) != len(assigned_values):
                raise ReviewPipelineError(
                    f"{role} review dimension assignment must be non-empty and unique"
                )
            if role in ROLE_DIMENSIONS and not assigned <= ROLE_DIMENSIONS[role]:
                extra = sorted(assigned - ROLE_DIMENSIONS[role])
                raise ReviewPipelineError(
                    f"{role} assignment contains unknown dimensions: {extra}"
                )
            actual = {item["dimension"] for item in by_role[role]["coverage"]}
            skipped = {item["dimension"] for item in by_role[role].get("skipped", [])}
            # A selected review can still fail its execution precondition after
            # dispatch. Keep the assignment for claim-to-gap mapping, but accept
            # the honest non-executed result instead of demanding fake coverage.
            if by_role[role]["status"] != "executed":
                continue
            if actual | skipped != assigned:
                missing = sorted(assigned - actual - skipped)
                extra = sorted((actual | skipped) - assigned)
                raise ReviewPipelineError(
                    f"{role} coverage mismatch; missing={missing}, extra={extra}"
                )
    epochs = {item["evidence_epoch"] for item in validated}
    fingerprints = {item["code_fingerprint"] for item in validated}
    if len(epochs) > 1 or len(fingerprints) > 1:
        raise ReviewPipelineError("all review results must share evidence_epoch and code_fingerprint")
    resolved_epoch = next(iter(epochs), evidence_epoch)
    resolved_fingerprint = next(iter(fingerprints), code_fingerprint)
    if not resolved_epoch or not resolved_fingerprint:
        raise ReviewPipelineError(
            "zero-role aggregate requires evidence_epoch and code_fingerprint"
        )
    if evidence_epoch and resolved_epoch != evidence_epoch:
        raise ReviewPipelineError("review results do not match evidence_epoch")
    if code_fingerprint and resolved_fingerprint != code_fingerprint:
        raise ReviewPipelineError("review results do not match code_fingerprint")
    global_ids: dict[str, str] = {}
    for result in validated:
        for field in ("findings", "open_questions", "deferred_candidates"):
            for item in result[field]:
                identifier = item["id"]
                owner = f"{result['role']}.{field}"
                if identifier in global_ids:
                    raise ReviewPipelineError(
                        f"duplicate item id across review results: {identifier} "
                        f"({global_ids[identifier]}, {owner})"
                    )
                global_ids[identifier] = owner
    restore_result = restore_report_result(restore_report)
    finding_sources = list(validated)
    if restore_result:
        finding_sources.append(restore_result)
    findings = merge_findings(finding_sources)
    questions = merge_named(validated, "open_questions")
    deferred = merge_named(validated, "deferred_candidates")
    # handoff 的文本一律由结构化字段拼，不再依赖角色自己写的一段自由文本——
    # 那段文本原先要同时装现象、影响和建议动作，结果三样都说不清。
    handoff = [
        {
            "kind": "suggestion",
            "id": "/".join(item["source_ids"]),
            "user_visible_text": f"{item['summary']}（{item['impact']}）",
            "needs_decision": False,
        }
        for item in findings if item["level"] == "suggestion"
    ] + [
        {"kind": "open_question", "id": "/".join(item["source_ids"]), "user_visible_text": item["summary"], "needs_decision": bool(item["needs_decision"])}
        for item in questions
    ] + [
        {
            "kind": "deferred",
            "id": "/".join(item["source_ids"]),
            "user_visible_text": f"{item['ac']}：{item['reason']}",
            "needs_decision": True,
        }
        for item in deferred
    ] + [
        # 规范候选一律 needs_decision：规范节只有 sdd-init-frontend 能改，Story 侧
        # 无权自行采纳，收口时必须由人裁决要不要把它交给 init。
        {
            "kind": "norm_candidate",
            "id": item["id"],
            "user_visible_text": (
                f"{display(item['kind'])}：{item['claim']}"
                + (f"（质疑 {item['target_id']}）" if item.get("target_id") else "")
                + (f"；现象 {item['phenomenon']}" if item.get("phenomenon") else "")
                + f"；依据样本 {len(item['samples'])} 处"
            ),
            "needs_decision": True,
        }
        for item in (norm_candidates or [])
    ] + [
        # 待人工验收是**动作**而不是决策：要人去执行验收、补证据或修失败，
        # 不是要人在几个选项里拍板。所以 needs_decision=False——`--decisions`
        # 因此够不到它，一句「可以了」不能把人工声明改成 PROVEN。
        {
            "kind": "manual_acceptance",
            "id": item["id"],
            "user_visible_text": manual_action_text(item),
            "needs_decision": False,
        }
        for item in (manual_acceptance or [])
        if not manual_is_settled(item)
    ]
    # 答复必须挂在一条真实的待决项上。挂不上的答复要么是编号写错、要么是那条待决项
    # 已经消失（比如修完之后不再需要决定）——两种都不能静默收下，否则报告里会出现一条
    # 谁也对不上的「你的决定」。
    decidable = {item["id"] for item in handoff if item.get("needs_decision")}
    orphans = sorted(
        item["item"] for item in (decisions or []) if item["item"] not in decidable
    )
    if orphans:
        raise ReviewPipelineError(
            f"decisions reference items that are not awaiting a decision: {orphans}"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_epoch": resolved_epoch,
        "code_fingerprint": resolved_fingerprint,
        "roles": {role: by_role[role]["status"] for role in expected},
        "known_gaps": {role: by_role[role]["known_gaps"] for role in expected},
        "judged_files": {role: by_role[role].get("judged_files", []) for role in expected},
        "coverage": {role: by_role[role]["coverage"] for role in expected},
        "skipped": {role: by_role[role].get("skipped", []) for role in expected},
        "findings": findings,
        "open_questions": questions,
        "deferred_candidates": deferred,
        "norm_candidates": list(norm_candidates or []),
        "unplanned_carry": list(unplanned_carry or []),
        "manual_acceptance": list(manual_acceptance or []),
        "claim_ledger": list(claim_ledger or []),
        "restore_contract": (
            {key: restore_result[key] for key in ("overall", "summary", "contract_sha256")}
            if restore_result else None
        ),
        "decisions": list(decisions or []),
        "handoff": handoff,
        "counts": {
            "blocker": sum(item["level"] == "blocker" for item in findings),
            "suggestion": sum(item["level"] == "suggestion" for item in findings),
            "open_question": len(questions),
            "deferred": len(deferred),
            "norm_candidate": len(norm_candidates or []),
            "unplanned_carry": len(unplanned_carry or []),
            "manual_acceptance": len(manual_acceptance or []),
            "manual_pending": sum(
                not manual_is_settled(item) for item in (manual_acceptance or [])
            ),
            "claims_unverified": sum(item["claim_status"] == "UNVERIFIED" for item in (claim_ledger or [])),
            "claims_deferred": sum(item["claim_status"] == "DEFERRED" for item in (claim_ledger or [])),
            "decided": len(decisions or []),
            "handoff": len(handoff),
            "skipped": sum(len(by_role[role].get("skipped", [])) for role in expected),
        },
    }


def attach_evidence_artifacts(
    aggregate: dict[str, Any], review_evidence: dict[str, Any]
) -> dict[str, Any]:
    scenario_artifacts = {
        item.get("id"): item.get("artifacts", [])
        for item in require_list(review_evidence.get("scenarios", []), "review_evidence.scenarios")
        if isinstance(item, dict)
    }
    for field in ("findings", "open_questions", "deferred_candidates"):
        for item in aggregate[field]:
            artifacts: list[str] = []
            for evidence_id in item.get("evidence_ids", []):
                for artifact in scenario_artifacts.get(evidence_id, []):
                    if artifact not in artifacts:
                        artifacts.append(artifact)
            item["artifacts"] = artifacts
    return aggregate


"""给人读的词表：只作用于 `acceptance.md` 的渲染，不改任何线上值。

`acceptance.md` 的列头一直是中文，但单元格里印的是生的枚举值——「结果」列写 `clear`、
「类型」列写 `norm_candidate`、风险触发器写 `shared-boundary`。读的人得先在脑子里翻译一遍，
而这些词的英文形态对他没有任何用处：他不写 JSON，也不 grep 这份文件。

**线上格式一个字不动**，所以脚本、单测、fixture、ground truth 与回传契约全不受影响。
翻译只发生在渲染这一步。

未登记的值按原样印出，不猜、不隐藏——新增一个枚举值却忘了配词条时，读的人会看到英文原文
（一个可见的提示），而不是一个被悄悄吞掉或翻错的格子。`test_display_vocabulary_is_complete`
守这一条：当前所有枚举值都必须在表里。
"""
DISPLAY = {
    # 角色 / 格子
    "review-layout": "布局检视",
    "review-convention": "规范检视",
    "review-quality": "质量检视",
    "self-test": "功能自测试",
    # 角色执行状态
    "executed": "已执行",
    "not_applicable": "判定不适用",
    "unexecuted": "未执行",
    # coverage 结果
    "clear": "无发现",
    "finding": "有发现",
    "unrun": "未执行",
    "skipped": "判定不适用",
    # 发现级别
    "blocker": "阻断级",
    "suggestion": "建议级",
    # handoff 类型
    "open_question": "未决问题",
    "deferred": "暂缓候选",
    "norm_candidate": "规范候选",
    "manual_acceptance": "待人工验收",
    # 人工执行结果（与声明状态分属两轴，各自有自己的词条）
    "NOT_RUN": "未执行",
    "PASSED": "通过",
    "FAILED": "未通过",
    # 人工例外依据
    "visual_judgment": "视觉判断",
    "motion_judgment": "动效体验判断",
    "device_dependency": "真机或系统能力依赖",
    "external_dependency": "外部环境依赖",
    "content_approval": "内容确认",
    "automation_cost_exception": "自动化成本例外",
    # 风险触发器
    "visual": "视觉",
    "interaction": "交互",
    "navigation": "导航",
    "auth": "鉴权",
    "write": "写操作",
    "async-state": "异步状态",
    "shared-boundary": "共享边界",
    "build-config": "构建配置",
    "new-pattern": "新范式",
    "spec-gap": "规格缺口",
    "unknown-deps": "未知依赖",
    "performance": "性能",
    # 验证模块
    "causal": "因果证据",
    "render": "结构化渲染",
    "story": "用户路径",
    "regression": "回归",
    "targeted-quality": "定向质量",
    "restore-final": "最终还原复核",
    # 规范候选类别
    "broken": "规范不再成立",
    "exemption-recurring": "豁免反复出现",
    "runtime-trap": "运行时陷阱",
    # 声明状态（与 references/execution-contract.md 的状态表同一套词）
    "PROVEN": "已验证",
    "UNVERIFIED": "未验证",
    "DEFERRED": "已暂缓",
    # 布尔
    True: "需要",
    False: "不需要",
}

# 只有这些列装枚举值，才翻。自由文本（summary / reason / basis / scope）与标识符
# （dimension / evidence_ids / source_ids / target_id / samples / 路径）一律原样——
# 把翻译无差别套到所有格子上，会把「R1-1」「BE-2」这类锚点和人写的句子一起弄坏。
TRANSLATED_KEYS = {
    "result", "kind", "level", "trigger", "needs_decision", "status", "role",
    "manual_outcome", "claim_status", "manual_basis",
}


def display(value: Any) -> str:
    """把一个线上值翻成人读的词；未登记的原样返回。"""
    if isinstance(value, bool):
        return DISPLAY[value]
    return DISPLAY.get(value, str(value))


def markdown_table(items: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    if not items:
        return ["无。"]
    lines = ["| " + " | ".join(label for label, _ in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for item in items:
        values = []
        for _, key in columns:
            value = item.get(key, "")
            if key in TRANSLATED_KEYS:
                value = (
                    "、".join(display(part) for part in value)
                    if isinstance(value, list)
                    else display(value)
                )
            elif isinstance(value, list):
                value = "、".join(str(part) for part in value)
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_markdown(aggregate: dict[str, Any]) -> str:
    """渲染验收入口。没有任何机器消费这份 Markdown——结构化数据全在 `review-results.json`。

    所以它只回答人验收时的三个问题，按这个顺序：**能不能验收 / 有什么必须我处理 /
    有什么我该知道但不用动**，最后才是往下追的路径。

    这里刻意不印证据纪元、代码指纹和「全部无发现」的覆盖明细。它们是缓存失效键与审计
    轨迹，人不会对它们做任何决定，而把它们摆在开头会让读的人以为自己得先看懂这些
    才有资格往下读。要审计就去 `review-results.json`，那份是给机器和追查用的。
    """
    counts = aggregate["counts"]
    blockers = [item for item in aggregate["findings"] if item["level"] == "blocker"]
    suggestions = [item for item in aggregate["findings"] if item["level"] == "suggestion"]
    decisions = [item for item in aggregate["handoff"] if item.get("needs_decision")]
    answers = {item["item"]: item for item in aggregate.get("decisions", [])}
    # 已答复的不再算「待你定」——否则答完一轮，顶上那句还在催同一件事。
    pending = [item for item in decisions if item["id"] not in answers]
    manual_open = [
        item for item in aggregate.get("manual_acceptance", []) if not manual_is_settled(item)
    ]
    manual_failed = [item for item in manual_open if item["manual_outcome"] == "FAILED"]
    ledger = aggregate.get("claim_ledger", [])
    manual_ids = {item["id"] for item in aggregate.get("manual_acceptance", [])}
    # 人工项已有自己的措辞；账本里的其余声明按状态分两堆，因为它们对读者的意义完全不同：
    # UNVERIFIED 是「前端还没做完」，DEFERRED 是「前端做完了，等外部接缝」。压成一个词就没法决定能不能先合。
    unverified_claims = [i for i in ledger if i["claim_status"] == "UNVERIFIED" and i["id"] not in manual_ids]
    deferred_claims = [i for i in ledger if i["claim_status"] == "DEFERRED" and i["id"] not in manual_ids]
    deferred_deps = sorted({i.get("external_dependency", "") for i in deferred_claims if i.get("external_dependency")})

    lines = ["# 验收摘要", ""]

    # 第一句必须是结论本身，不是计数。读的人先要知道能不能收。
    # 人工验收未完成时这里绝不能出现无条件「可验收」——实现完成不等于验收通过，
    # 而这份摘要是唯一会被当成验收结论读的东西。
    seam_tail = (
        f"；{len(deferred_claims)} 条真实接缝待外部依赖（{'、'.join(deferred_deps) or '见暂缓表'}）"
        if deferred_claims else ""
    )
    if blockers or manual_failed:
        reasons = []
        if blockers:
            reasons.append(f"{len(blockers)} 条阻断级问题")
        if manual_failed:
            reasons.append(f"{len(manual_failed)} 项人工验收未通过")
        lines += [f"**暂不可验收**：有{'、'.join(reasons)}需要先修。逐条见下。"]
    elif unverified_claims:
        lines += [
            f"**部分验证：{len(unverified_claims)} 条声明未验证**"
            + (f"；待 {len(manual_open)} 项人工验收" if manual_open else "")
            + seam_tail
            + (f"；另有 {len(pending)} 件需要你定" if pending else "")
            + "。未验证项是本阶段做得到但还没做的，先补证再谈收口。",
        ]
    elif manual_open:
        lines += [
            f"**实现完成，待 {len(manual_open)} 项人工验收**"
            + seam_tail
            + (f"；另有 {len(pending)} 件需要你定" if pending else "")
            + "。人工验收通过并留下证据后才可收口。",
        ]
    elif deferred_claims:
        lines += [
            f"**前端已验证，{len(deferred_claims)} 条真实接缝待外部依赖**（{'、'.join(deferred_deps) or '见暂缓表'}）"
            + (f"；另有 {len(pending)} 件需要你定" if pending else "")
            + "。前端范围内的声明全部已验证，可先合并；接缝声明的解除条件见「暂缓的验收项」，外部依赖就绪后按「解除 DEFERRED」入口复跑。",
        ]
    elif pending:
        lines += [
            f"**可验收，但有 {len(pending)} 件需要你定**。修完或拍板后即可收口。",
        ]
    else:
        lines += ["**可验收**：本次检视没有阻断级问题，也没有需要你决定的事项。"]

    if blockers or decisions or manual_open:
        # 逐项分块而不是表格：中文一句 60–100 字塞进单元格，三列一起就没法读了。
        # 表格适合短枚举，不适合成句。
        lines += ["", "## 需要你处理", ""]
        index = 0
        for item in blockers:
            index += 1
            lines += [
                f"### {index}. {item['summary']}",
                "",
                f"- **在哪**：`{item['location']}`",
                f"- **影响**：{item['impact']}",
                f"- **建议**：{item['suggested_action']}",
                f"- 依据与完整证据：`evidence/review-results.json` 的 `{'/'.join(item['source_ids'])}`",
                "",
            ]
        for item in decisions:
            index += 1
            answered = answers.get(item["id"])
            lines += [
                f"### {index}. {item['user_visible_text']}",
                "",
                f"- **类型**：{display(item['kind'])}",
            ]
            if answered:
                # 已答复的就地记下结论，别让人在下一轮再被问一遍同一件事。
                lines.append(f"- **你的决定**：{answered['answer']}（{answered['decided_at']}）")
                if answered.get("rationale"):
                    lines.append(f"- 理由：{answered['rationale']}")
            else:
                lines.append("- **要你定**：见下方提问，回答后会记回本文件")
            lines.append("")
        for item in manual_open:
            index += 1
            lines += [
                f"### {index}. {item['id']}：{item['trace']}",
                "",
                f"- **类型**：{display('manual_acceptance')}（{display(item['manual_basis'])}）",
                f"- **当前**：人工结果 {display(item['manual_outcome'])}、声明状态 {display(item['claim_status'])}",
                f"- **在哪验**：{item['required_environment']}",
                f"- **要留下什么**：{item['required_evidence']}",
                f"- **要做什么**：{manual_action_text(item)}",
                "- 回填后由主 agent 重新聚合；agent 不能代签",
                "",
            ]

    # 建议只在这一节出现。原先它同时进「你该知道」和一张「改进建议」表，
    # 同一条被说两遍——正是要避免的那种重复。
    # 人工验收虽然 needs_decision=False，但它是要人去做的动作，已在「需要你处理」
    # 逐条展开，不能再落到「不用动」这一节里自我矛盾。
    heads_up = [
        item
        for item in aggregate["handoff"]
        if not item.get("needs_decision")
        and item["kind"] not in ("suggestion", "manual_acceptance")
    ]
    if suggestions or heads_up:
        lines += ["", "## 你该知道，但不用动", ""]
        for item in suggestions:
            lines += [
                f"- **{item['summary']}**（`{item['location']}`）",
                f"  {item['impact']}。建议：{item['suggested_action']}",
            ]
        lines += [f"- {item['user_visible_text']}" for item in heads_up]

    # 「这次判了什么」只列没判到的，以及为什么。判到且无发现的用一句话带过——
    # 逐行列出几十条「无发现」不帮任何决定，只会把上面的结论挤到看不见。
    lines += ["", "## 这次判了什么", ""]
    judged, unjudged = [], []
    if (aggregate.get("restore_contract") or {}).get("overall") == "green":
        judged.append("冻结还原契约")
    for role, status in aggregate["roles"].items():
        gaps = aggregate["known_gaps"][role]
        if status == "executed" and not gaps:
            judged.append(display(role))
        else:
            reason = "；".join(str(item) for item in gaps) if gaps else display(status)
            unjudged.append(f"- **{display(role)}**：{reason}")
    if judged:
        lines.append(f"已判并通过：{'、'.join(judged)}。")
    if unjudged:
        lines += ["", "没判到或判不全的："] + unjudged
    if not judged and not unjudged:
        lines.append("本次没有触发任何独立检视。")

    not_applicable = [
        f"- **{display(role)} {row['dimension']}**：{row['reason']}"
        for role, rows in aggregate.get("skipped", {}).items()
        for row in rows
    ]
    if not_applicable:
        lines += ["", "判定不适用的检查项："] + not_applicable

    narrowed = aggregate.get("portfolio_narrowed")
    if narrowed:
        # 收窄必须署名可见——这是它存在的全部意义。
        lines += ["", "**主动少判了这些，理由如下：**"] + [
            f"- {display(item['trigger'])}：{item['reason']}" for item in narrowed
        ]

    if aggregate["open_questions"]:
        lines += ["", "## 未决问题", ""]
        lines += [f"- {item['summary']}" for item in aggregate["open_questions"]]

    # 人工项里被暂缓的那些也在这一节露出：读的人找「什么被缓了」只该看一个地方。
    # 只在渲染层合并，结构化输出里两者仍各归各处——人工暂缓不是角色回传的 deferred
    # 候选，不能混进那条需要决策的通道。
    manual_deferred = [
        {
            "ac": f"{item['id']}（{item['trace']}）",
            "reason": f"待人工验收：{display(item['manual_basis'])}",
            "resume_condition": item.get("resume_condition", ""),
        }
        for item in aggregate.get("manual_acceptance", [])
        if item.get("claim_status") == "DEFERRED"
    ]
    ledger_deferred = [
        {
            "ac": item["id"],
            "reason": f"外部依赖未就绪：{item.get('external_dependency') or '未写明'}",
            "resume_condition": item.get("resume_condition", ""),
        }
        for item in deferred_claims
    ]
    if aggregate["deferred_candidates"] or manual_deferred or ledger_deferred:
        lines += ["", "## 暂缓的验收项", ""]
        lines += markdown_table(
            list(aggregate["deferred_candidates"]) + ledger_deferred + manual_deferred,
            [("验收标准", "ac"), ("为什么缓", "reason"), ("什么条件下解除", "resume_condition")],
        )

    if aggregate.get("manual_acceptance"):
        lines += ["", "## 人工验收总表", ""]
        lines += markdown_table(
            aggregate["manual_acceptance"],
            [("声明", "id"), ("追溯", "trace"), ("范围", "verification_scope"),
             ("依据", "manual_basis"), ("人工结果", "manual_outcome"),
             ("声明状态", "claim_status"), ("验收人", "manual_checked_by"),
             ("验收时间", "manual_checked_at"), ("证据", "evidence_refs")],
        )

    if aggregate.get("unplanned_carry"):
        lines += ["", "## 顺带改到的文件（计划外承接）", ""]
        lines += markdown_table(
            aggregate["unplanned_carry"],
            [("文件", "file"), ("属哪个 Task", "task"), ("为什么必须一并改", "reason")],
        )
    if aggregate.get("norm_candidates"):
        # 这一节有 init 侧的读者，保留可被逐条对账的形状。
        lines += ["", "## 交 sdd-init-frontend 的规范候选", ""]
        lines += markdown_table(
            aggregate["norm_candidates"],
            [("编号", "id"), ("类别", "kind"), ("质疑对象", "target_id"), ("结论", "claim"), ("现象", "phenomenon"), ("依据样本", "samples")],
        )

    lines += [
        "", "## 要往下追的话", "",
        "- 冻结的验收基线：`dev-baseline.md`",
        "- 逐条声明与它的证据：`alpha-tests.md`",
        f"- 全部覆盖明细与结构化结论：`evidence/review-results.json`（共 {counts.get('handoff', 0)} 条交接项、"
        f"{counts.get('skipped', 0)} 条判定不适用）",
        "",
    ]
    return "\n".join(lines)


def command_scenarios(args: argparse.Namespace) -> None:
    evidence_path = Path(args.review_evidence)
    evidence = read_json(evidence_path) if evidence_path.exists() else {
        "schema_version": SCHEMA_VERSION,
        "evidence_epoch": args.evidence_epoch,
        "quality_gate": {},
        "scenarios": [],
    }
    additions = require_list(read_json(Path(args.add)), "add") if args.add else []
    output, summary = record_scenarios(
        require_dict(evidence, "review_evidence"),
        require_dict(read_json(Path(args.code_manifest)), "code_manifest"),
        additions,
        require_dict(read_json(Path(args.runtime)), "runtime"),
        args.source,
    )
    atomic_write_json(evidence_path, output)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


def command_aggregate(args: argparse.Namespace) -> None:
    results = [read_json(Path(path)) for path in args.result]
    evidence_path = Path(args.review_evidence)
    source_evidence = require_dict(read_json(evidence_path), "review_evidence")
    portfolio = require_dict(
        source_evidence.get("validation_portfolio"),
        "review_evidence.validation_portfolio",
    )
    restore_report = None
    if "restore-final" in require_list(portfolio.get("modules", []), "validation_portfolio.modules"):
        restore_path = evidence_path.with_name("restore-report-green.json")
        contract_path = evidence_path.with_name("restore-contract.json")
        restore_report = require_dict(read_json(restore_path), "restore-report-green.json")
        contract = require_dict(read_json(contract_path), "restore-contract.json")
        if restore_report.get("contract_sha256") != contract.get("contract_sha256"):
            raise ReviewPipelineError("restore-report-green.json does not match restore-contract.json")
    expected_roles = require_list(
        portfolio.get("review_roles"),
        "review_evidence.validation_portfolio.review_roles",
    )
    expected_roles = [
        require_text(role, f"review_evidence.validation_portfolio.review_roles[{index}]")
        for index, role in enumerate(expected_roles)
    ]
    raw_dimensions = require_dict(
        portfolio.get("review_dimensions"),
        "review_evidence.validation_portfolio.review_dimensions",
    )
    if set(raw_dimensions) != set(expected_roles):
        raise ReviewPipelineError(
            "review_evidence.validation_portfolio.review_dimensions must match review_roles"
        )
    expected_dimensions = {
        role: [
            require_text(item, f"review_evidence.validation_portfolio.review_dimensions.{role}[{index}]")
            for index, item in enumerate(require_list(
                raw_dimensions[role],
                f"review_evidence.validation_portfolio.review_dimensions.{role}",
            ))
        ]
        for role in expected_roles
    }
    diff_facts = require_dict(read_json(Path(args.diff_facts)), "diff_facts")
    narrowed = check_portfolio_floor(portfolio, diff_facts)
    if args.alpha_tests and (args.unplanned_carry or args.manual_acceptance):
        raise ReviewPipelineError("--alpha-tests already carries unplanned_carry and manual_acceptance; drop the JSON flags")
    claim_ledger: list[dict[str, Any]] = []
    if args.alpha_tests:
        unplanned_carry, manual_acceptance, claim_ledger = project_alpha_tests(
            read_text(Path(args.alpha_tests)),
            read_text(Path(args.tasks)) if args.tasks else None,
        )
        check_claim_profiles(claim_ledger, portfolio)
    else:
        unplanned_carry = (
            validate_unplanned_carry(read_json(Path(args.unplanned_carry))) if args.unplanned_carry else []
        )
        manual_acceptance = (
            validate_manual_acceptance(read_json(Path(args.manual_acceptance))) if args.manual_acceptance else []
        )
    evidence, results = merge_evidence_additions(
        source_evidence, results
    )
    code = require_dict(evidence.get("code"), "review_evidence.code")
    aggregate = aggregate_results(
        results,
        expected_roles=expected_roles,
        expected_dimensions=expected_dimensions,
        evidence_epoch=require_text(evidence.get("evidence_epoch"), "review_evidence.evidence_epoch"),
        code_fingerprint=require_text(code.get("code_fingerprint"), "review_evidence.code.code_fingerprint"),
        evidence_index=build_evidence_index(evidence),
        code_files=set(code_hashes(code)),
        skip_rebuttals=require_dict(
            diff_facts.get("skip_rebuttals", {}), "diff_facts.skip_rebuttals"
        ),
        norm_candidates=(
            validate_norm_candidates(read_json(Path(args.norm_candidates)))
            if args.norm_candidates
            else []
        ),
        unplanned_carry=unplanned_carry,
        manual_acceptance=manual_acceptance,
        claim_ledger=claim_ledger,
        decisions=(
            validate_decisions(read_json(Path(args.decisions))) if args.decisions else []
        ),
        restore_report=restore_report,
    )
    aggregate["validation_portfolio"] = portfolio
    aggregate["portfolio_narrowed"] = narrowed
    aggregate = attach_evidence_artifacts(aggregate, evidence)
    atomic_write_json(evidence_path, evidence)
    atomic_write_json(Path(args.output_json), aggregate)
    atomic_write(Path(args.output_markdown), render_markdown(aggregate))
    print(json.dumps(aggregate["counts"], ensure_ascii=False, sort_keys=True))


def command_merge_additions(args: argparse.Namespace) -> None:
    evidence_path = Path(args.review_evidence)
    evidence, rewritten = merge_evidence_additions(
        require_dict(read_json(evidence_path), "review_evidence"),
        [read_json(Path(args.result))],
    )
    atomic_write_json(evidence_path, evidence)
    atomic_write_json(Path(args.output_result), rewritten[0])
    print(json.dumps({
        "role": rewritten[0]["role"],
        "evidence_ids": rewritten[0]["evidence_reused"],
    }, ensure_ascii=False, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    scenarios = subparsers.add_parser("scenarios")
    scenarios.add_argument("--review-evidence", required=True)
    scenarios.add_argument("--code-manifest", required=True)
    scenarios.add_argument("--runtime", required=True)
    scenarios.add_argument("--add", help="JSON array of new raw scenarios; omit for a freshness check only")
    scenarios.add_argument("--source", default="phase-b")
    scenarios.add_argument("--evidence-epoch", default="review-1")
    scenarios.set_defaults(handler=command_scenarios)
    merge_additions = subparsers.add_parser("merge-additions")
    merge_additions.add_argument("--review-evidence", required=True)
    merge_additions.add_argument("--result", required=True)
    merge_additions.add_argument("--output-result", required=True)
    merge_additions.set_defaults(handler=command_merge_additions)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--result", action="append", default=[])
    aggregate.add_argument("--review-evidence", required=True)
    aggregate.add_argument("--diff-facts", required=True, help="classify_diff.py output for the final diff")
    aggregate.add_argument(
        "--norm-candidates",
        help="JSON array：Dev 发现的仓库级规范变化，回流给 sdd-init-frontend；无则省略",
    )
    aggregate.add_argument(
        "--alpha-tests",
        help="alpha-tests.md：脚本直接读「计划外承接」「人工验收记录」「Deferred」三张表；给了它就不要再传下面两个 JSON",
    )
    aggregate.add_argument(
        "--tasks",
        help="tasks.md：人工验收项的 verification_scope 从「用例追溯」取；有人工验收记录时必填",
    )
    aggregate.add_argument(
        "--unplanned-carry",
        help="JSON array：计划外承接；只在不传 --alpha-tests 时用",
    )
    aggregate.add_argument(
        "--manual-acceptance",
        help="JSON array：待人工验收项；只在不传 --alpha-tests 时用",
    )
    aggregate.add_argument(
        "--decisions",
        help="JSON array：用户对待决项的答复（item / answer / decided_at），就地记回报告",
    )
    aggregate.add_argument("--output-json", required=True)
    aggregate.add_argument("--output-markdown", required=True)
    aggregate.set_defaults(handler=command_aggregate)
    return root


def main() -> int:
    try:
        arguments = parser().parse_args()
        arguments.handler(arguments)
        return 0
    except ReviewPipelineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
