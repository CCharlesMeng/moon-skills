#!/usr/bin/env python3
"""Record raw browser scenarios and aggregate independent Phase C reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
ROLES = ("review-layout", "review-convention", "review-quality", "self-test")
ROLE_DIMENSIONS = {
    "review-layout": {f"L{index}" for index in range(1, 7)},
    "review-convention": {f"C{index}" for index in range(1, 8)},
    "review-quality": {f"Q{index}" for index in range(1, 9)},
}
SELF_TEST_FAMILIES = {"F1", "F2", "F3", "F4", "REG"}
JUDGMENT_KEYS = {
    "finding", "findings", "verdict", "conclusion", "level", "severity",
    "passed", "pass", "failed", "result", "open_questions",
    "deferred_candidates", "user_visible_text",
}


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
    findings = require_list(result.get("findings"), f"{role}.findings")
    questions = require_list(result.get("open_questions"), f"{role}.open_questions")
    deferred = require_list(result.get("deferred_candidates"), f"{role}.deferred_candidates")
    gaps = require_list(result.get("known_gaps"), f"{role}.known_gaps")
    require_list(result.get("evidence_reused"), f"{role}.evidence_reused")
    evidence_added = require_list(result.get("evidence_added"), f"{role}.evidence_added")
    for index, addition in enumerate(evidence_added):
        validate_evidence_addition(addition, f"{role}.evidence_added[{index}]")
    if status != "executed":
        if coverage or findings or questions or deferred or not gaps:
            raise ReviewPipelineError(f"{role} non-executed result must only explain known_gaps")
        return result

    dimensions: set[str] = set()
    for index, raw_coverage in enumerate(coverage):
        item = require_dict(raw_coverage, f"{role}.coverage[{index}]")
        dimension = require_text(item.get("dimension"), f"{role}.coverage[{index}].dimension")
        if dimension in dimensions:
            raise ReviewPipelineError(f"duplicate coverage dimension {role}:{dimension}")
        dimensions.add(dimension)
        require_text(item.get("scope"), f"{role}.coverage[{index}].scope")
        require_list(item.get("evidence_ids"), f"{role}.coverage[{index}].evidence_ids")
        if item.get("result") not in {"clear", "finding", "unrun"}:
            raise ReviewPipelineError(f"invalid coverage result {role}:{dimension}")
    if role in ROLE_DIMENSIONS and dimensions != ROLE_DIMENSIONS[role]:
        missing = sorted(ROLE_DIMENSIONS[role] - dimensions)
        extra = sorted(dimensions - ROLE_DIMENSIONS[role])
        raise ReviewPipelineError(f"{role} coverage mismatch; missing={missing}, extra={extra}")
    if role == "self-test":
        families = {dimension.split("-", 1)[0] for dimension in dimensions}
        if not SELF_TEST_FAMILIES.issubset(families):
            raise ReviewPipelineError(
                f"self-test coverage missing families: {sorted(SELF_TEST_FAMILIES - families)}"
            )

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


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if len(results) != len(ROLES):
        raise ReviewPipelineError("aggregate requires exactly four role results")
    validated = [validate_review_result(item) for item in results]
    by_role = {item["role"]: item for item in validated}
    if set(by_role) != set(ROLES):
        raise ReviewPipelineError(f"aggregate roles mismatch: {sorted(by_role)}")
    epochs = {item["evidence_epoch"] for item in validated}
    fingerprints = {item["code_fingerprint"] for item in validated}
    if len(epochs) != 1 or len(fingerprints) != 1:
        raise ReviewPipelineError("all review results must share evidence_epoch and code_fingerprint")
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
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_epoch": epochs.pop(),
        "code_fingerprint": fingerprints.pop(),
        "roles": {role: by_role[role]["status"] for role in ROLES},
        "known_gaps": {role: by_role[role]["known_gaps"] for role in ROLES},
        "coverage": {role: by_role[role]["coverage"] for role in ROLES},
        "findings": findings,
        "open_questions": questions,
        "deferred_candidates": deferred,
        "handoff": handoff,
        "counts": {
            "blocker": sum(item["level"] == "blocker" for item in findings),
            "suggestion": sum(item["level"] == "suggestion" for item in findings),
            "open_question": len(questions),
            "deferred": len(deferred),
            "handoff": len(handoff),
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


def markdown_table(items: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    if not items:
        return ["无。"]
    lines = ["| " + " | ".join(label for label, _ in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for item in items:
        values = []
        for _, key in columns:
            value = item.get(key, "")
            if isinstance(value, list):
                value = "、".join(str(part) for part in value)
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_markdown(aggregate: dict[str, Any]) -> str:
    counts = aggregate["counts"]
    lines = [
        "# Dev Review", "",
        "## 给人的摘要", "",
        f"四份独立检视已聚合：阻断级 {counts['blocker']} 条，建议级 {counts['suggestion']} 条，Open Question {counts['open_question']} 条，Deferred 候选 {counts['deferred']} 条。",
        "## 检视基准", "",
        f"- evidence epoch: `{aggregate['evidence_epoch']}`", f"- code fingerprint: `{aggregate['code_fingerprint']}`",
    ]
    if aggregate["findings"]:
        summary_lines = [
            f"- {item['user_visible_text']}（{'/'.join(item['source_ids'])}）"
            for item in aggregate["findings"]
        ]
    else:
        summary_lines = ["本次检视无需要你关注的发现。"]
    lines[5:5] = ["", *summary_lines, ""]
    for role, status in aggregate["roles"].items():
        gaps = aggregate["known_gaps"][role]
        detail = f"（{'；'.join(str(item) for item in gaps)}）" if gaps else ""
        lines.append(f"- {role}: {status}{detail}")
    lines += ["", "## 覆盖矩阵", ""]
    coverage_rows = []
    for role, rows in aggregate["coverage"].items():
        for row in rows:
            coverage_rows.append({"role": role, **row})
    lines += markdown_table(coverage_rows, [("角色", "role"), ("维度", "dimension"), ("范围", "scope"), ("证据", "evidence_ids"), ("结果", "result")])
    blockers = [item for item in aggregate["findings"] if item["level"] == "blocker"]
    suggestions = [item for item in aggregate["findings"] if item["level"] == "suggestion"]
    for title, items in (("阻断级", blockers), ("建议级", suggestions)):
        if items:
            lines += ["", f"## {title}", ""]
            lines += markdown_table(items, [("来源", "source_ids"), ("发现", "summary"), ("定位", "location"), ("依据", "basis"), ("证据", "evidence_ids"), ("截图 / 工件", "artifacts")])
    if aggregate["open_questions"]:
        lines += ["", "## Open Question", ""]
        lines += markdown_table(aggregate["open_questions"], [("来源", "source_ids"), ("问题", "summary"), ("证据", "evidence_ids")])
    if aggregate["deferred_candidates"]:
        lines += ["", "## Deferred 候选", ""]
        lines += markdown_table(aggregate["deferred_candidates"], [("来源", "source_ids"), ("AC", "ac"), ("原因", "reason"), ("解除条件", "resume_condition")])
    lines += ["", "## Handoff 清单", ""]
    lines += markdown_table(aggregate["handoff"], [("类型", "kind"), ("来源", "id"), ("用户可见文本", "user_visible_text"), ("需用户决定", "needs_decision")])
    lines += ["", "## 收口结论", "", "待 Phase D 填写。", ""]
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
    evidence, results = merge_evidence_additions(
        require_dict(read_json(evidence_path), "review_evidence"), results
    )
    aggregate = attach_evidence_artifacts(aggregate_results(results), evidence)
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
    aggregate.add_argument("--result", action="append", required=True)
    aggregate.add_argument("--review-evidence", required=True)
    aggregate.add_argument("--output-json", required=True)
    aggregate.add_argument("--output-markdown", required=True)
    aggregate.set_defaults(handler=command_aggregate)
    return root


def main() -> int:
    try:
        arguments = parser().parse_args()
        if arguments.command == "aggregate" and len(arguments.result) != len(ROLES):
            raise ReviewPipelineError("--result must be supplied exactly four times")
        arguments.handler(arguments)
        return 0
    except ReviewPipelineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
