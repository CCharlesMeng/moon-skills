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
    "review-restore",
    "review-layout",
    "review-convention",
    "review-quality",
    "self-test",
)
# self-test 不在这里：它的 dimension 是分配到的冻结基线行号（F2-1 / REG-2），
# 没有固定集合，只能靠 aggregate 的 assignment 比对。
ROLE_DIMENSIONS = {
    "review-restore": {f"R{index}" for index in range(1, 7)},
    "review-layout": {f"L{index}" for index in range(1, 7)},
    "review-convention": {f"C{index}" for index in range(1, 8)},
    "review-quality": {f"Q{index}" for index in range(1, 9)},
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
    require_text(item.get("user_visible_text"), f"{label}.user_visible_text")
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
        validate_common_item(item, f"{role}.findings[{index}]", ("dimension", "level", "summary", "location", "basis"))
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
            for field in ("summary", "location", "user_visible_text"):
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
            if key in merged and merged[key]["user_visible_text"] != item["user_visible_text"]:
                raise ReviewPipelineError(f"canonical_key conflict for {key}: incompatible user_visible_text")
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


NORM_CANDIDATE_KINDS = {"broken", "new-pattern", "exemption-recurring"}


def validate_norm_candidates(raw: Any) -> list[dict[str, Any]]:
    """校验规范候选：Dev 发现的仓库级事实变化，回流给 `sdd-init-frontend`。

    这条通道此前只存在于散文里——`recon-codebase` 会回传「规范待确认」，规则说攒进
    `acceptance.md` 由 init 重新归纳，但 `acceptance.md` 没有这一节、聚合器的 handoff
    也只有 suggestion / open_question / deferred 三类，装不下它。结果是一句「攒进
    handoff」到不了任何人手里。

    两条校验是这个通道能用的前提：

    - **必须点名依据样本。** init 归纳规范要的就是「看了哪几处」；只说「这条规范
      不成立了」而不给样本，维护者得从零重扫，那还不如没有这条回流。
    - **必须指名 `target_id`（`broken` 与 `exemption-recurring`）。** 说不出质疑的是
      哪一条，就没法判断它是同一条的第 n 次复发还是一条新发现——而复发计数正是
      init 决定要不要动规范节的唯一依据。

    刻意**不**要求样本数 ≥ 2：跨 Story 的复发计数只有 init 能做，单个 Story 手里
    永远只有自己那一次。在这里卡门槛等于把计数依据吞掉。
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
        validated.append(item)
    return validated


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
    findings = merge_findings(validated)
    questions = merge_named(validated, "open_questions")
    deferred = merge_named(validated, "deferred_candidates")
    handoff = [
        {"kind": "suggestion", "id": "/".join(item["source_ids"]), "user_visible_text": item["user_visible_text"], "needs_decision": False}
        for item in findings if item["level"] == "suggestion"
    ] + [
        {"kind": "open_question", "id": "/".join(item["source_ids"]), "user_visible_text": item["user_visible_text"], "needs_decision": bool(item["needs_decision"])}
        for item in questions
    ] + [
        {"kind": "deferred", "id": "/".join(item["source_ids"]), "user_visible_text": item["user_visible_text"], "needs_decision": True}
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
                + f"；依据样本 {len(item['samples'])} 处"
            ),
            "needs_decision": True,
        }
        for item in (norm_candidates or [])
    ]
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
        "handoff": handoff,
        "counts": {
            "blocker": sum(item["level"] == "blocker" for item in findings),
            "suggestion": sum(item["level"] == "suggestion" for item in findings),
            "open_question": len(questions),
            "deferred": len(deferred),
            "norm_candidate": len(norm_candidates or []),
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
    "review-restore": "还原检视",
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
    "journey": "用户路径",
    "regression": "回归",
    "targeted-quality": "定向质量",
    # 规范候选类别
    "broken": "规范不再成立",
    "exemption-recurring": "豁免反复出现",
    # 声明状态（与 docs/skills/frontend-sdd/执行契约.md 的状态表同一套词）
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
TRANSLATED_KEYS = {"result", "kind", "level", "trigger", "needs_decision", "status", "role"}


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

    lines = ["# 验收摘要", ""]

    # 第一句必须是结论本身，不是计数。读的人先要知道能不能收。
    if blockers:
        lines += [
            f"**暂不可验收**：有 {len(blockers)} 条阻断级问题需要先修。逐条见下。",
        ]
    elif decisions:
        lines += [
            f"**可验收，但有 {len(decisions)} 件需要你定**。修完或拍板后即可收口。",
        ]
    else:
        lines += ["**可验收**：本次检视没有阻断级问题，也没有需要你决定的事项。"]

    if blockers or decisions:
        lines += ["", "## 需要你处理", ""]
        rows = [
            {
                "什么问题": item["summary"],
                "在哪": item["location"],
                "要你做什么": "先修掉，它挡住验收",
            }
            for item in blockers
        ] + [
            {
                "什么问题": item["user_visible_text"],
                "在哪": display(item["kind"]),
                "要你做什么": "需要你拍板",
            }
            for item in decisions
        ]
        lines += markdown_table(
            rows, [("什么问题", "什么问题"), ("在哪", "在哪"), ("要你做什么", "要你做什么")]
        )

    heads_up = [item for item in aggregate["handoff"] if not item.get("needs_decision")]
    if heads_up:
        lines += ["", "## 你该知道，但不用动", ""]
        lines += [f"- {item['user_visible_text']}" for item in heads_up]

    # 「这次判了什么」只列没判到的，以及为什么。判到且无发现的用一句话带过——
    # 逐行列出几十条「无发现」不帮任何决定，只会把上面的结论挤到看不见。
    lines += ["", "## 这次判了什么", ""]
    judged, unjudged = [], []
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

    if suggestions:
        lines += ["", "## 改进建议（本次不修）", ""]
        lines += markdown_table(
            suggestions,
            [("建议", "summary"), ("在哪", "location"), ("依据", "basis")],
        )

    if aggregate["open_questions"]:
        lines += ["", "## 未决问题", ""]
        lines += [f"- {item['summary']}" for item in aggregate["open_questions"]]

    if aggregate["deferred_candidates"]:
        lines += ["", "## 暂缓的验收项", ""]
        lines += markdown_table(
            aggregate["deferred_candidates"],
            [("验收标准", "ac"), ("为什么缓", "reason"), ("什么条件下解除", "resume_condition")],
        )

    if aggregate.get("norm_candidates"):
        # 这一节有 init 侧的读者，保留可被逐条对账的形状。
        lines += ["", "## 交 sdd-init-frontend 的规范候选", ""]
        lines += markdown_table(
            aggregate["norm_candidates"],
            [("编号", "id"), ("类别", "kind"), ("质疑对象", "target_id"), ("结论", "claim"), ("依据样本", "samples")],
        )

    lines += [
        "", "## 要往下追的话", "",
        "- 冻结的验收基线：`dev-baseline.md`",
        "- 逐条声明与它的证据：`alpha-tests.md`",
        f"- 全部覆盖明细与结构化结论：`review-results.json`（共 {counts.get('handoff', 0)} 条交接项、"
        f"{counts.get('skipped', 0)} 条判定不适用）",
        "", "## 收口结论", "", "待 Phase D 填写。", "",
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
