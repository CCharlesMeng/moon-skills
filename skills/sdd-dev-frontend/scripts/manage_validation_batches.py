#!/usr/bin/env python3
"""Plan validation batches, record granular results, and compute precise reruns."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KINDS = ("command", "browser")
STATUSES = ("pass", "fail", "blocked")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
SECRET_KEY = re.compile(
    r"(?:^|[_-])(token|secret|password|passwd|cookie|credential|api[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)


class ValidationBatchError(RuntimeError):
    """Raised when a validation plan or receipt would be unsafe to use."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationBatchError(f"cannot read JSON {path}: {error}") from error


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationBatchError(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationBatchError(f"{label} must be an array")
    return value


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationBatchError(f"{label} must be non-empty text")
    return value.strip()


def require_identifier(value: Any, label: str) -> str:
    text = require_text(value, label)
    if not IDENTIFIER.fullmatch(text):
        raise ValidationBatchError(f"{label} has an invalid identifier: {text}")
    return text


def require_unique_texts(value: Any, label: str) -> list[str]:
    values = require_list(value, label)
    normalized = [require_text(item, f"{label}[]") for item in values]
    if not normalized:
        raise ValidationBatchError(f"{label} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValidationBatchError(f"{label} must not contain duplicates")
    return normalized


def require_texts(value: Any, label: str) -> list[str]:
    values = require_list(value, label)
    normalized = [require_text(item, f"{label}[]") for item in values]
    if not normalized:
        raise ValidationBatchError(f"{label} must not be empty")
    return normalized


def reject_secret_keys(value: Any, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                raise ValidationBatchError(f"{label} contains forbidden secret key: {key}")
            reject_secret_keys(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_secret_keys(item, f"{label}[{index}]")


def require_safe_relative_path(value: Any, label: str) -> str:
    text = require_text(value, label)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationBatchError(f"{label} must be a safe repo-relative path: {text}")
    return path.as_posix()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValidationBatchError(f"cannot hash dependency {path}: {error}") from error
    return digest.hexdigest()


def capture_dependencies(repo_root: Path, paths: list[str]) -> dict[str, str]:
    root = repo_root.resolve()
    captured: dict[str, str] = {}
    for relative in paths:
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ValidationBatchError(
                f"dependency resolves outside repo root: {relative}"
            ) from error
        if not target.is_file():
            raise ValidationBatchError(f"dependency is not a file: {relative}")
        captured[relative] = hash_file(target)
    return dict(sorted(captured.items()))


def normalize_mapping(value: Any, label: str) -> dict[str, Any]:
    mapping = require_dict(value, label)
    reject_secret_keys(mapping, label)
    return {key: mapping[key] for key in sorted(mapping)}


def normalize_command_execution(value: Any, label: str) -> dict[str, Any]:
    execution = require_dict(value, label)
    package = require_text(execution.get("package"), f"{label}.package")
    commands = require_list(execution.get("commands"), f"{label}.commands")
    if not commands:
        raise ValidationBatchError(f"{label}.commands must not be empty")
    normalized_commands: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(commands):
        command = require_dict(raw, f"{label}.commands[{index}]")
        name = require_identifier(command.get("name"), f"{label}.commands[{index}].name")
        if name in names:
            raise ValidationBatchError(f"duplicate command name: {name}")
        names.add(name)
        argv = require_texts(
            command.get("argv"), f"{label}.commands[{index}].argv"
        )
        if argv.count("{scope}") > 1:
            raise ValidationBatchError(f"command {name} may contain at most one {{scope}}")
        normalized_commands.append({"name": name, "argv": argv})
    return {
        "package": package,
        "commands": normalized_commands,
        "toolchain": normalize_mapping(execution.get("toolchain"), f"{label}.toolchain"),
        "runtime": normalize_mapping(execution.get("runtime"), f"{label}.runtime"),
    }


def normalize_browser_execution(value: Any, label: str) -> dict[str, Any]:
    execution = require_dict(value, label)
    fixture = require_dict(execution.get("fixture"), f"{label}.fixture")
    normalized = {
        "driver": require_text(execution.get("driver"), f"{label}.driver"),
        "page": require_text(execution.get("page"), f"{label}.page"),
        "fixture": {
            "name": require_text(fixture.get("name"), f"{label}.fixture.name"),
            "sha256": require_text(fixture.get("sha256"), f"{label}.fixture.sha256"),
        },
        "reset_strategy": require_text(
            execution.get("reset_strategy"), f"{label}.reset_strategy"
        ),
        "runtime": normalize_mapping(execution.get("runtime"), f"{label}.runtime"),
    }
    reject_secret_keys(normalized, label)
    return normalized


def normalize_browser_scenario(value: Any, label: str) -> dict[str, Any]:
    scenario = require_dict(value, label)
    viewport = require_dict(scenario.get("viewport"), f"{label}.viewport")
    width = viewport.get("width")
    height = viewport.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValidationBatchError(f"{label}.viewport.width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise ValidationBatchError(f"{label}.viewport.height must be a positive integer")
    return {
        "name": require_text(scenario.get("name"), f"{label}.name"),
        "viewport": {"width": width, "height": height},
        "steps": require_unique_texts(scenario.get("steps"), f"{label}.steps"),
    }


def normalize_intent(raw: Any, index: int, repo_root: Path) -> dict[str, Any]:
    label = f"intents[{index}]"
    intent = require_dict(raw, label)
    identifier = require_identifier(intent.get("id"), f"{label}.id")
    kind = require_text(intent.get("kind"), f"{label}.kind")
    if kind not in KINDS:
        raise ValidationBatchError(f"{label}.kind must be one of {KINDS}")
    barrier = intent.get("barrier", False)
    if not isinstance(barrier, bool):
        raise ValidationBatchError(f"{label}.barrier must be boolean")
    dependencies = [
        require_safe_relative_path(item, f"{label}.depends_on[]")
        for item in require_list(intent.get("depends_on"), f"{label}.depends_on")
    ]
    if not dependencies:
        raise ValidationBatchError(f"{label}.depends_on must not be empty")
    if len(set(dependencies)) != len(dependencies):
        raise ValidationBatchError(f"{label}.depends_on must not contain duplicates")
    normalized: dict[str, Any] = {
        "id": identifier,
        "kind": kind,
        "boundary": require_text(intent.get("boundary"), f"{label}.boundary"),
        "barrier": barrier,
        "consumers": sorted(require_unique_texts(intent.get("consumers"), f"{label}.consumers")),
        "assertions": sorted(require_unique_texts(intent.get("assertions"), f"{label}.assertions")),
        "depends_on": sorted(dependencies),
        "captured_dependency_hashes": capture_dependencies(repo_root, dependencies),
    }
    if kind == "command":
        if "cleanup_required" in intent:
            raise ValidationBatchError(f"{label}.cleanup_required is only valid for browser intents")
        normalized["execution"] = normalize_command_execution(
            intent.get("execution"), f"{label}.execution"
        )
        raw_scope = require_unique_texts(intent.get("scope"), f"{label}.scope")
        normalized["scope"] = sorted(
            require_safe_relative_path(item, f"{label}.scope[]") for item in raw_scope
        )
    else:
        cleanup_required = intent.get("cleanup_required", False)
        if not isinstance(cleanup_required, bool):
            raise ValidationBatchError(f"{label}.cleanup_required must be boolean")
        if cleanup_required and not barrier:
            raise ValidationBatchError(
                f"{label}.cleanup_required browser intent must also set barrier=true"
            )
        normalized["cleanup_required"] = cleanup_required
        normalized["execution"] = normalize_browser_execution(
            intent.get("execution"), f"{label}.execution"
        )
        normalized["scenario"] = normalize_browser_scenario(
            intent.get("scenario"), f"{label}.scenario"
        )
    normalized["intent_fingerprint"] = fingerprint(normalized)
    return normalized


def group_key(intent: dict[str, Any]) -> bytes:
    value: dict[str, Any] = {
        "kind": intent["kind"],
        "boundary": intent["boundary"],
        "execution": intent["execution"],
    }
    if intent["barrier"]:
        value["barrier_intent"] = intent["id"]
    return canonical_json(value)


def render_commands(intents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    scopes = sorted({scope for intent in intents for scope in intent["scope"]})
    rendered: list[dict[str, Any]] = []
    for command in intents[0]["execution"]["commands"]:
        argv: list[str] = []
        for item in command["argv"]:
            if item == "{scope}":
                argv.extend(scopes)
            else:
                argv.append(item)
        rendered.append({"name": command["name"], "argv": argv})
    return rendered, scopes


def build_plan(payload: Any, repo_root: Path) -> dict[str, Any]:
    source = require_dict(payload, "input")
    if source.get("schema_version") != SCHEMA_VERSION:
        raise ValidationBatchError("unsupported input schema_version")
    story = require_text(source.get("story"), "input.story")
    raw_intents = require_list(source.get("intents"), "input.intents")
    if not raw_intents:
        raise ValidationBatchError("input.intents must not be empty")
    intents = [normalize_intent(raw, index, repo_root) for index, raw in enumerate(raw_intents)]
    identifiers = [intent["id"] for intent in intents]
    if len(set(identifiers)) != len(identifiers):
        raise ValidationBatchError("intent ids must be unique")

    grouped: dict[bytes, list[dict[str, Any]]] = {}
    for intent in sorted(intents, key=lambda item: item["id"]):
        grouped.setdefault(group_key(intent), []).append(intent)

    ordered_groups = sorted(
        grouped.values(),
        key=lambda items: (KINDS.index(items[0]["kind"]), group_key(items[0])),
    )
    batches: list[dict[str, Any]] = []
    batch_ids: set[str] = set()
    for items in ordered_groups:
        kind = items[0]["kind"]
        execution = dict(items[0]["execution"])
        batch_id = f"VAL-B-{hashlib.sha256(group_key(items[0])).hexdigest()[:12]}"
        if batch_id in batch_ids:
            raise ValidationBatchError(f"validation batch id collision: {batch_id}")
        batch_ids.add(batch_id)
        batch: dict[str, Any] = {
            "id": batch_id,
            "kind": kind,
            "boundary": items[0]["boundary"],
            "consumers": sorted({consumer for item in items for consumer in item["consumers"]}),
            "assertions": sorted({assertion for item in items for assertion in item["assertions"]}),
            "execution": execution,
            "intents": items,
        }
        if kind == "command":
            commands, scopes = render_commands(items)
            batch["execution"] = {**execution, "commands": commands, "scope": scopes}
        else:
            batch["execution"] = {
                **execution,
                "session_strategy": "open-once-reset-between-intents",
                "scenarios": [
                    {
                        "intent_id": item["id"],
                        **item["scenario"],
                        "assertions": item["assertions"],
                    }
                    for item in items
                ],
            }
        batch["batch_fingerprint"] = fingerprint({
            "kind": batch["kind"],
            "boundary": batch["boundary"],
            "execution": batch["execution"],
            "intents": [
                {"id": item["id"], "intent_fingerprint": item["intent_fingerprint"]}
                for item in items
            ],
        })
        batches.append(batch)

    return {
        "schema_version": SCHEMA_VERSION,
        "story": story,
        "repo_root": str(repo_root.resolve()),
        "source_fingerprint": fingerprint({
            "story": story,
            "intents": [
                {"id": item["id"], "intent_fingerprint": item["intent_fingerprint"]}
                for item in sorted(intents, key=lambda item: item["id"])
            ],
        }),
        "batches": batches,
    }


def validate_plan(payload: Any) -> dict[str, Any]:
    plan = require_dict(payload, "plan")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ValidationBatchError("unsupported plan schema_version")
    require_text(plan.get("story"), "plan.story")
    batches = require_list(plan.get("batches"), "plan.batches")
    if not batches:
        raise ValidationBatchError("plan.batches must not be empty")
    batch_ids: set[str] = set()
    intent_ids: set[str] = set()
    for batch_index, raw_batch in enumerate(batches):
        label = f"plan.batches[{batch_index}]"
        batch = require_dict(raw_batch, label)
        batch_id = require_identifier(batch.get("id"), f"{label}.id")
        if batch_id in batch_ids:
            raise ValidationBatchError(f"duplicate plan batch id: {batch_id}")
        batch_ids.add(batch_id)
        kind = require_text(batch.get("kind"), f"{label}.kind")
        if kind not in KINDS:
            raise ValidationBatchError(f"{label}.kind must be one of {KINDS}")
        boundary = require_text(batch.get("boundary"), f"{label}.boundary")
        execution = require_dict(batch.get("execution"), f"{label}.execution")
        intents = require_list(batch.get("intents"), f"{label}.intents")
        if not intents:
            raise ValidationBatchError(f"{label}.intents must not be empty")
        intent_fingerprints: list[dict[str, str]] = []
        for intent_index, raw_intent in enumerate(intents):
            intent_label = f"{label}.intents[{intent_index}]"
            intent = require_dict(raw_intent, intent_label)
            intent_id = require_identifier(intent.get("id"), f"{intent_label}.id")
            if intent_id in intent_ids:
                raise ValidationBatchError(f"duplicate plan intent id: {intent_id}")
            intent_ids.add(intent_id)
            stored_fingerprint = require_text(
                intent.get("intent_fingerprint"), f"{intent_label}.intent_fingerprint"
            )
            material = {key: value for key, value in intent.items() if key != "intent_fingerprint"}
            expected_fingerprint = fingerprint(material)
            if stored_fingerprint != expected_fingerprint:
                raise ValidationBatchError(
                    f"{intent_label}.intent_fingerprint mismatch: "
                    f"expected {expected_fingerprint}, got {stored_fingerprint}"
                )
            intent_fingerprints.append({
                "id": intent_id,
                "intent_fingerprint": stored_fingerprint,
            })
        stored_batch_fingerprint = require_text(
            batch.get("batch_fingerprint"), f"{label}.batch_fingerprint"
        )
        expected_batch_fingerprint = fingerprint({
            "kind": kind,
            "boundary": boundary,
            "execution": execution,
            "intents": intent_fingerprints,
        })
        if stored_batch_fingerprint != expected_batch_fingerprint:
            raise ValidationBatchError(
                f"{label}.batch_fingerprint mismatch: "
                f"expected {expected_batch_fingerprint}, got {stored_batch_fingerprint}"
            )
    return plan


def derive_item_status(results: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in results}
    if "fail" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "blocked"
    return "passed"


def normalize_result_item(raw: Any, intent: dict[str, Any], label: str) -> dict[str, Any]:
    item = require_dict(raw, label)
    intent_id = require_identifier(item.get("intent_id"), f"{label}.intent_id")
    if intent_id != intent["id"]:
        raise ValidationBatchError(f"{label}.intent_id does not match selected intent")
    raw_results = require_list(item.get("results"), f"{label}.results")
    results: list[dict[str, Any]] = []
    for index, raw_result in enumerate(raw_results):
        result = require_dict(raw_result, f"{label}.results[{index}]")
        assertion = require_text(
            result.get("assertion"), f"{label}.results[{index}].assertion"
        )
        status = require_text(result.get("status"), f"{label}.results[{index}].status")
        if status not in STATUSES:
            raise ValidationBatchError(
                f"{label}.results[{index}].status must be one of {STATUSES}"
            )
        evidence = require_unique_texts(
            result.get("evidence"), f"{label}.results[{index}].evidence"
        )
        results.append({"assertion": assertion, "status": status, "evidence": evidence})
    actual = [item["assertion"] for item in results]
    if len(set(actual)) != len(actual) or set(actual) != set(intent["assertions"]):
        raise ValidationBatchError(
            f"{label}.results must cover every assertion exactly once; "
            f"expected {intent['assertions']}, got {actual}"
        )
    results.sort(key=lambda result: result["assertion"])
    normalized = {
        "intent_id": intent_id,
        "intent_fingerprint": intent["intent_fingerprint"],
        "status": derive_item_status(results),
        "results": results,
    }
    if intent.get("cleanup_required"):
        cleanup = require_dict(item.get("cleanup"), f"{label}.cleanup")
        cleanup_status = require_text(cleanup.get("status"), f"{label}.cleanup.status")
        if cleanup_status not in ("cleaned", "not-cleaned"):
            raise ValidationBatchError(
                f"{label}.cleanup.status must be cleaned or not-cleaned"
            )
        normalized["cleanup"] = {
            "status": cleanup_status,
            "evidence": require_unique_texts(
                cleanup.get("evidence"), f"{label}.cleanup.evidence"
            ),
        }
    return normalized


def normalize_metrics(value: Any, kind: str) -> dict[str, int]:
    metrics = require_dict(value, "result.metrics")
    normalized: dict[str, int] = {}
    for key in ("browser_calls", "commands", "retries"):
        raw = metrics.get(key, 0)
        if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
            raise ValidationBatchError(f"result.metrics.{key} must be a non-negative integer")
        normalized[key] = raw
    if kind == "browser" and normalized["browser_calls"] < 1:
        raise ValidationBatchError("browser batch must record at least one browser call")
    if kind == "command" and normalized["commands"] < 1:
        raise ValidationBatchError("command batch must record at least one command")
    return normalized


def append_receipt(
    plan_payload: Any, result_payload: Any, receipts_payload: Any | None
) -> dict[str, Any]:
    plan = validate_plan(plan_payload)
    result = require_dict(result_payload, "result")
    batch_id = require_identifier(result.get("batch_id"), "result.batch_id")
    batch = next((item for item in plan["batches"] if item.get("id") == batch_id), None)
    if batch is None:
        raise ValidationBatchError(f"result.batch_id is not present in plan: {batch_id}")
    executed_at = require_text(result.get("executed_at"), "result.executed_at")
    try:
        parsed = dt.datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationBatchError("result.executed_at must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise ValidationBatchError("result.executed_at must include timezone")
    raw_items = require_list(result.get("items"), "result.items")
    if not raw_items:
        raise ValidationBatchError("result.items must not be empty")
    intents = {item["id"]: item for item in batch["intents"]}
    normalized_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        raw_item = require_dict(raw, f"result.items[{index}]")
        intent_id = require_identifier(
            raw_item.get("intent_id"), f"result.items[{index}].intent_id"
        )
        if intent_id in seen:
            raise ValidationBatchError(f"duplicate result intent: {intent_id}")
        if intent_id not in intents:
            raise ValidationBatchError(f"result intent is not in {batch_id}: {intent_id}")
        seen.add(intent_id)
        normalized_items.append(
            normalize_result_item(raw_item, intents[intent_id], f"result.items[{index}]")
        )
    normalized_items.sort(key=lambda item: item["intent_id"])

    if receipts_payload is None:
        receipts: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "story": plan["story"],
            "records": [],
        }
    else:
        receipts = require_dict(receipts_payload, "receipts")
        if receipts.get("schema_version") != SCHEMA_VERSION:
            raise ValidationBatchError("unsupported receipts schema_version")
        if receipts.get("story") != plan["story"]:
            raise ValidationBatchError("receipts story does not match plan story")
        require_list(receipts.get("records"), "receipts.records")
    records = receipts["records"]
    attempts = [
        record.get("attempt", 0)
        for record in records
        if isinstance(record, dict) and record.get("batch_id") == batch_id
    ]
    attempt = max(attempts, default=0) + 1
    item_statuses = {item["status"] for item in normalized_items}
    status = "failed" if "failed" in item_statuses else (
        "blocked" if "blocked" in item_statuses else "passed"
    )
    records.append({
        "batch_id": batch_id,
        "batch_fingerprint": batch["batch_fingerprint"],
        "attempt": attempt,
        "executed_at": parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "metrics": normalize_metrics(result.get("metrics"), batch["kind"]),
        "items": normalized_items,
    })
    return receipts


def item_history(receipts: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    for record_index, raw_record in enumerate(receipts.get("records", [])):
        record = require_dict(raw_record, f"receipts.records[{record_index}]")
        items = require_list(record.get("items"), f"receipts.records[{record_index}].items")
        for raw_item in items:
            item = require_dict(raw_item, f"receipts.records[{record_index}].items[]")
            intent_id = require_identifier(item.get("intent_id"), "receipt intent_id")
            history.setdefault(intent_id, []).append(item)
    return history


def summarize_status(plan_payload: Any, receipts_payload: Any | None) -> dict[str, Any]:
    plan = validate_plan(plan_payload)
    if receipts_payload is None:
        receipts = {"schema_version": SCHEMA_VERSION, "story": plan["story"], "records": []}
    else:
        receipts = require_dict(receipts_payload, "receipts")
        if receipts.get("schema_version") != SCHEMA_VERSION:
            raise ValidationBatchError("unsupported receipts schema_version")
        if receipts.get("story") != plan["story"]:
            raise ValidationBatchError("receipts story does not match plan story")
    history = item_history(receipts)
    intent_states: dict[str, dict[str, Any]] = {}
    consumer_intents: dict[str, list[str]] = {}
    next_batches: list[dict[str, Any]] = []

    for batch in plan["batches"]:
        rerun: list[str] = []
        for intent in batch["intents"]:
            identifier = intent["id"]
            receipts_for_intent = history.get(identifier, [])
            receipt = next((
                item for item in reversed(receipts_for_intent)
                if item.get("intent_fingerprint") == intent["intent_fingerprint"]
            ), None)
            if receipt is None and not receipts_for_intent:
                state = "pending"
            elif receipt is None:
                state = "stale"
            else:
                state = receipt.get("status")
                if state not in ("passed", "failed", "blocked"):
                    raise ValidationBatchError(f"receipt has invalid item status: {state}")
            intent_states[identifier] = {
                "status": state,
                "batch_id": batch["id"],
                "consumers": intent["consumers"],
                "assertions": intent["assertions"],
            }
            for consumer in intent["consumers"]:
                consumer_intents.setdefault(consumer, []).append(identifier)
            if state != "passed":
                rerun.append(identifier)
        if rerun:
            selected = [item for item in batch["intents"] if item["id"] in rerun]
            if batch["kind"] == "command":
                commands, scopes = render_commands(selected)
                execution = {**batch["execution"], "commands": commands, "scope": scopes}
            else:
                execution = {
                    **batch["execution"],
                    "scenarios": [
                        scenario
                        for scenario in batch["execution"]["scenarios"]
                        if scenario["intent_id"] in rerun
                    ],
                }
            next_batches.append({
                "batch_id": batch["id"],
                "kind": batch["kind"],
                "intent_ids": rerun,
                "execution": execution,
            })

    consumers: dict[str, Any] = {}
    for consumer, identifiers in sorted(consumer_intents.items()):
        states = [intent_states[identifier]["status"] for identifier in identifiers]
        status = "passed" if all(state == "passed" for state in states) else (
            "failed" if "failed" in states else (
                "blocked" if "blocked" in states else (
                    "stale" if "stale" in states else "pending"
                )
            )
        )
        consumers[consumer] = {"status": status, "intent_ids": sorted(identifiers)}

    state_counts: dict[str, int] = {}
    for item in intent_states.values():
        state_counts[item["status"]] = state_counts.get(item["status"], 0) + 1
    metrics = {"browser_calls": 0, "commands": 0, "retries": 0}
    for record in receipts.get("records", []):
        for key in metrics:
            value = record.get("metrics", {}).get(key, 0)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                metrics[key] += value
    return {
        "schema_version": SCHEMA_VERSION,
        "story": plan["story"],
        "ready": bool(intent_states) and all(
            item["status"] == "passed" for item in intent_states.values()
        ),
        "counts": {
            "batches": len(plan["batches"]),
            "browser_batches": sum(batch["kind"] == "browser" for batch in plan["batches"]),
            "command_batches": sum(batch["kind"] == "command" for batch in plan["batches"]),
            "intents": len(intent_states),
            "consumers": len(consumers),
            "assertions": sum(len(item["assertions"]) for item in intent_states.values()),
            **dict(sorted(state_counts.items())),
            **metrics,
        },
        "intents": intent_states,
        "consumers": consumers,
        "next_batches": next_batches,
    }


def command_plan(arguments: argparse.Namespace) -> int:
    plan = build_plan(read_json(Path(arguments.intents)), Path(arguments.repo_root))
    atomic_write_json(Path(arguments.output), plan)
    print(json.dumps({
        "status": "PLANNED",
        "output": arguments.output,
        "batches": len(plan["batches"]),
        "intents": sum(len(batch["intents"]) for batch in plan["batches"]),
    }, ensure_ascii=False, sort_keys=True))
    return 0


def command_record(arguments: argparse.Namespace) -> int:
    receipts_path = Path(arguments.receipts)
    receipts = append_receipt(
        read_json(Path(arguments.plan)),
        read_json(Path(arguments.result)),
        read_json(receipts_path) if receipts_path.exists() else None,
    )
    atomic_write_json(receipts_path, receipts)
    record = receipts["records"][-1]
    print(json.dumps({
        "status": "RECORDED",
        "batch_id": record["batch_id"],
        "attempt": record["attempt"],
        "result": record["status"],
        "items": len(record["items"]),
    }, ensure_ascii=False, sort_keys=True))
    return 0


def command_status(arguments: argparse.Namespace) -> int:
    receipts_path = Path(arguments.receipts)
    summary = summarize_status(
        read_json(Path(arguments.plan)),
        read_json(receipts_path) if receipts_path.exists() else None,
    )
    if arguments.output:
        atomic_write_json(Path(arguments.output), summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="compile compatible intents into validation batches")
    plan.add_argument("--repo-root", required=True)
    plan.add_argument("--intents", required=True)
    plan.add_argument("--output", required=True)
    plan.set_defaults(handler=command_plan)

    record = commands.add_parser("record", help="append granular results for one batch or subset")
    record.add_argument("--plan", required=True)
    record.add_argument("--result", required=True)
    record.add_argument("--receipts", required=True)
    record.set_defaults(handler=command_record)

    status = commands.add_parser("status", help="show readiness and exact incremental reruns")
    status.add_argument("--plan", required=True)
    status.add_argument("--receipts", required=True)
    status.add_argument("--output")
    status.set_defaults(handler=command_status)
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        arguments = parser().parse_args(argv)
        return arguments.handler(arguments)
    except ValidationBatchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
