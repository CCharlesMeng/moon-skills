#!/usr/bin/env python3
"""Manage exact preflight-quality reuse and compact Story execution telemetry."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
DEFAULT_MAX_AGE_HOURS = 24.0
CACHE_RELATIVE_PATH = "sdd-dev-frontend/preflight-quality.json"
SECRET_KEY = re.compile(
    r"(?:^|[_-])(token|secret|password|passwd|cookie|credential|api[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)


class EvidenceError(RuntimeError):
    """Raised when evidence is malformed or cannot be safely recorded."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def isoformat(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EvidenceError(f"invalid ISO-8601 timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise EvidenceError(f"timestamp must include timezone: {value}")
    return parsed.astimezone(dt.timezone.utc)


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
    except Exception as error:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        if isinstance(error, OSError):
            raise EvidenceError(f"cannot write JSON {path}: {error}") from error
        raise


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError(f"cannot read JSON {path}: {error}") from error


def git(repo_root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise EvidenceError(f"git-unavailable: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError(f"git-failed: {detail or 'unknown error'}")
    return result.stdout


def cache_path(repo_root: Path) -> Path:
    raw = git(repo_root, "rev-parse", "--git-path", CACHE_RELATIVE_PATH)
    value = raw.decode("utf-8", errors="strict").strip()
    if not value:
        raise EvidenceError("git-failed: empty --git-path result")
    path = Path(value)
    return path if path.is_absolute() else (repo_root / path).resolve()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def untracked_records(repo_root: Path) -> list[dict[str, str]]:
    raw = git(repo_root, "ls-files", "--others", "--exclude-standard", "-z")
    records: list[dict[str, str]] = []
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        relative = encoded.decode("utf-8", errors="surrogateescape")
        path = repo_root / relative
        try:
            if path.is_symlink():
                kind = "symlink"
                content_hash = sha256_bytes(os.readlink(path).encode("utf-8"))
            elif path.is_file():
                kind = "file"
                content_hash = hash_file(path)
            else:
                kind = "missing"
                content_hash = sha256_bytes(b"")
        except OSError as error:
            raise EvidenceError(f"cannot hash untracked path {relative}: {error}") from error
        records.append({"path": relative, "type": kind, "sha256": content_hash})
    return sorted(records, key=lambda item: item["path"])


def parse_key_values(values: Iterable[str], label: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise EvidenceError(f"{label} must be key=value: {value}")
        key, item = value.split("=", 1)
        key = key.strip()
        if not key or not item:
            raise EvidenceError(f"{label} must have non-empty key and value: {value}")
        if SECRET_KEY.search(key):
            raise EvidenceError(f"{label} key may contain a secret and is forbidden: {key}")
        if key in parsed:
            raise EvidenceError(f"duplicate {label} key: {key}")
        parsed[key] = item
    return dict(sorted(parsed.items()))


def validate_command_specs(values: Iterable[str], label: str) -> list[str]:
    commands = list(values)
    if label == "quality-command" and not commands:
        raise EvidenceError("at least one --quality-command is required")
    for command in commands:
        scope, separator, body = command.partition("::")
        if not separator or not scope.strip() or not body.strip():
            raise EvidenceError(f"{label} must be '<scope>::<complete command>': {command}")
    if len(set(commands)) != len(commands):
        raise EvidenceError(f"duplicate {label} is forbidden")
    return commands


def repository_state(repo_root: Path) -> dict[str, Any]:
    resolved = repo_root.resolve()
    head = git(resolved, "rev-parse", "HEAD").decode("ascii", errors="strict").strip()
    staged = git(resolved, "diff", "--cached", "--binary", "--no-ext-diff", "--")
    unstaged = git(resolved, "diff", "--binary", "--no-ext-diff", "--")
    return {
        "head": head,
        "staged_diff_sha256": sha256_bytes(staged),
        "unstaged_diff_sha256": sha256_bytes(unstaged),
        "untracked": untracked_records(resolved),
    }


def build_snapshot(
    repo_root: Path,
    quality_version: str,
    quality_commands: list[str],
    uncacheable_commands: list[str],
    toolchains: dict[str, str],
    runtime: dict[str, str],
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9]{1,9}", quality_version):
        raise EvidenceError("--quality-version must be a non-negative integer")
    unknown_uncacheable = [
        command for command in uncacheable_commands if command not in quality_commands
    ]
    if unknown_uncacheable:
        raise EvidenceError(
            "every --uncacheable-command must also appear as an exact --quality-command"
        )
    if not toolchains:
        raise EvidenceError("at least one toolchain name/version is required")
    if not runtime:
        raise EvidenceError("at least one non-secret runtime identifier is required")
    resolved = repo_root.resolve()
    state_inputs = {
        "repo_root": str(resolved),
        "repository": repository_state(resolved),
        "quality_version": quality_version,
        "quality_commands": quality_commands,
        "uncacheable_commands": uncacheable_commands,
        "toolchains": toolchains,
        "runtime": runtime,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": isoformat(utc_now()),
        **state_inputs,
        "state_fingerprint": sha256_bytes(canonical_json(state_inputs)),
    }


def refresh_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return build_snapshot(
        Path(required_string(snapshot, "repo_root")),
        required_string(snapshot, "quality_version"),
        required_string_list(snapshot, "quality_commands"),
        required_string_list(snapshot, "uncacheable_commands"),
        required_string_map(snapshot, "toolchains"),
        required_string_map(snapshot, "runtime"),
    )


def required_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"missing or invalid string field: {key}")
    return value


def required_string_list(mapping: dict[str, Any], key: str) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise EvidenceError(f"missing or invalid string list field: {key}")
    return value


def required_string_map(mapping: dict[str, Any], key: str) -> dict[str, str]:
    value = mapping.get(key)
    if not isinstance(value, dict) or not all(
        isinstance(item_key, str) and isinstance(item_value, str)
        for item_key, item_value in value.items()
    ):
        raise EvidenceError(f"missing or invalid string map field: {key}")
    return value


def normalize_quality_result(value: Any, expected_specs: list[str]) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("quality_gate"), dict):
        value = value["quality_gate"]
    if not isinstance(value, dict) or not isinstance(value.get("commands"), list):
        raise EvidenceError("quality result must contain commands[]")
    normalized: list[dict[str, Any]] = []
    for index, command in enumerate(value["commands"]):
        if not isinstance(command, dict):
            raise EvidenceError(f"quality result commands[{index}] must be an object")
        spec = command.get("spec")
        exit_code = command.get("exit_code")
        duration_ms = command.get("duration_ms")
        failures = command.get("failures")
        if not isinstance(spec, str):
            raise EvidenceError(f"quality result commands[{index}].spec must be a string")
        if not isinstance(exit_code, int):
            raise EvidenceError(f"quality result commands[{index}].exit_code must be an integer")
        if not isinstance(duration_ms, int) or duration_ms < 0:
            raise EvidenceError(
                f"quality result commands[{index}].duration_ms must be a non-negative integer"
            )
        if not isinstance(failures, list) or not all(isinstance(item, str) for item in failures):
            raise EvidenceError(f"quality result commands[{index}].failures must be strings")
        normalized.append(
            {
                "spec": spec,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "failures": failures,
            }
        )
    if [item["spec"] for item in normalized] != expected_specs:
        raise EvidenceError("quality result command specs do not exactly match snapshot order")
    return {"commands": normalized}


def probe_cache(snapshot: dict[str, Any], maximum_age_hours: float) -> dict[str, Any]:
    path = cache_path(Path(snapshot["repo_root"]))
    base = {
        "cache_path": str(path),
        "state_fingerprint": snapshot["state_fingerprint"],
    }
    if snapshot["uncacheable_commands"]:
        return {"status": "MISS", "reason": "uncacheable-command", **base}
    if not path.exists():
        return {"status": "MISS", "reason": "cache-not-found", **base}
    try:
        cached = read_json(path)
        if not isinstance(cached, dict) or cached.get("schema_version") != SCHEMA_VERSION:
            raise EvidenceError("unsupported cache schema")
        recorded_at = parse_time(required_string(cached, "recorded_at"))
        age = utc_now() - recorded_at
        if age.total_seconds() < 0 or age > dt.timedelta(hours=maximum_age_hours):
            return {"status": "MISS", "reason": "ttl-expired", **base}
        if cached.get("state_fingerprint") != snapshot["state_fingerprint"]:
            reason = fingerprint_miss_reason(cached, snapshot)
            return {"status": "MISS", "reason": reason, **base}
        quality_result = normalize_quality_result(
            cached.get("quality_result"), snapshot["quality_commands"]
        )
        return {
            "status": "HIT",
            "reason": "exact-match",
            **base,
            "recorded_at": cached["recorded_at"],
            "source": cached.get("source", "unknown"),
            "quality_result": quality_result,
        }
    except EvidenceError:
        return {"status": "MISS", "reason": "cache-invalid", **base}


def fingerprint_miss_reason(cached: dict[str, Any], current: dict[str, Any]) -> str:
    cached_repository = cached.get("repository")
    current_repository = current.get("repository")
    if not isinstance(cached_repository, dict) or not isinstance(current_repository, dict):
        return "cache-invalid"
    repository_fields = (
        ("head", "head-changed"),
        ("staged_diff_sha256", "staged-diff-changed"),
        ("unstaged_diff_sha256", "unstaged-diff-changed"),
        ("untracked", "untracked-changed"),
    )
    for field, reason in repository_fields:
        if cached_repository.get(field) != current_repository.get(field):
            return reason
    other_fields = (
        ("repo_root", "repo-root-changed"),
        ("quality_version", "quality-version-changed"),
        ("quality_commands", "quality-commands-changed"),
        ("uncacheable_commands", "uncacheable-commands-changed"),
        ("toolchains", "toolchains-changed"),
        ("runtime", "runtime-changed"),
    )
    for field, reason in other_fields:
        if cached.get(field) != current.get(field):
            return reason
    return "state-fingerprint-changed"


def command_probe(arguments: argparse.Namespace) -> int:
    try:
        commands = validate_command_specs(arguments.quality_command, "quality-command")
        uncacheable = validate_command_specs(
            arguments.uncacheable_command, "uncacheable-command"
        )
        snapshot = build_snapshot(
            Path(arguments.repo_root),
            arguments.quality_version,
            commands,
            uncacheable,
            parse_key_values(arguments.toolchain, "toolchain"),
            parse_key_values(arguments.runtime, "runtime"),
        )
        if arguments.snapshot_out:
            atomic_write_json(Path(arguments.snapshot_out), snapshot)
        result = probe_cache(snapshot, arguments.max_age_hours)
    except EvidenceError as error:
        result = {"status": "MISS", "reason": str(error).split(":", 1)[0]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def command_record(arguments: argparse.Namespace) -> int:
    snapshot = read_json(Path(arguments.snapshot))
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("unsupported snapshot schema")
    if required_string_list(snapshot, "uncacheable_commands"):
        raise EvidenceError("cannot record a snapshot with uncacheable commands")
    refreshed = refresh_snapshot(snapshot)
    if refreshed["state_fingerprint"] != snapshot.get("state_fingerprint"):
        raise EvidenceError("repository state changed during quality gate; probe again")
    quality_result = normalize_quality_result(
        read_json(Path(arguments.quality_result)),
        required_string_list(snapshot, "quality_commands"),
    )
    path = cache_path(Path(required_string(snapshot, "repo_root")))
    payload = {
        **snapshot,
        "recorded_at": isoformat(utc_now()),
        "source": arguments.source,
        "quality_result": quality_result,
    }
    atomic_write_json(path, payload)
    print(
        json.dumps(
            {
                "status": "RECORDED",
                "cache_path": str(path),
                "state_fingerprint": snapshot["state_fingerprint"],
                "source": arguments.source,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def parse_counts(values: Iterable[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise EvidenceError(f"count must be key=non-negative-integer: {value}")
        key, raw = value.split("=", 1)
        try:
            number = int(raw)
        except ValueError as error:
            raise EvidenceError(f"count must be an integer: {value}") from error
        if not key or number < 0 or key in parsed:
            raise EvidenceError(f"invalid or duplicate count: {value}")
        parsed[key] = number
    return dict(sorted(parsed.items()))


def command_telemetry(arguments: argparse.Namespace) -> int:
    path = Path(arguments.file)
    started = parse_time(arguments.started_at)
    ended = parse_time(arguments.ended_at)
    if ended < started:
        raise EvidenceError("ended-at must not precede started-at")
    if arguments.attempt < 1:
        raise EvidenceError("attempt must be at least 1")
    if path.exists():
        payload = read_json(path)
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            raise EvidenceError("unsupported telemetry schema")
        if payload.get("story") != arguments.story:
            raise EvidenceError("telemetry story does not match --story")
        steps = payload.get("steps")
        if not isinstance(steps, list):
            raise EvidenceError("telemetry steps must be a list")
    else:
        payload = {"schema_version": SCHEMA_VERSION, "story": arguments.story, "steps": []}
        steps = payload["steps"]
    if any(
        isinstance(step, dict)
        and step.get("id") == arguments.id
        and step.get("attempt") == arguments.attempt
        for step in steps
    ):
        raise EvidenceError(f"duplicate telemetry step: {arguments.id} attempt {arguments.attempt}")
    step = {
        "id": arguments.id,
        "attempt": arguments.attempt,
        "kind": arguments.kind,
        "started_at": isoformat(started),
        "ended_at": isoformat(ended),
        "duration_ms": int((ended - started).total_seconds() * 1000),
        "result": arguments.result,
        "counts": parse_counts(arguments.count),
        "evidence": list(arguments.evidence),
        "note": arguments.note,
    }
    steps.append(step)
    atomic_write_json(path, payload)
    print(
        json.dumps(
            {
                "status": "APPENDED",
                "file": str(path),
                "id": arguments.id,
                "attempt": arguments.attempt,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe", help="compute exact repository state and probe cache")
    probe.add_argument("--repo-root", required=True)
    probe.add_argument("--quality-version", required=True)
    probe.add_argument("--quality-command", action="append", required=True)
    probe.add_argument("--uncacheable-command", action="append", default=[])
    probe.add_argument("--toolchain", action="append", required=True)
    probe.add_argument("--runtime", action="append", required=True)
    probe.add_argument("--snapshot-out")
    probe.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    probe.set_defaults(handler=command_probe)

    record = commands.add_parser("record", help="record a completed deterministic quality gate")
    record.add_argument("--snapshot", required=True)
    record.add_argument("--quality-result", required=True)
    record.add_argument("--source", choices=("phase-0", "phase-c", "phase-d"), required=True)
    record.set_defaults(handler=command_record)

    telemetry = commands.add_parser("telemetry", help="append one compact completed step")
    telemetry.add_argument("--file", required=True)
    telemetry.add_argument("--story", required=True)
    telemetry.add_argument("--id", required=True)
    telemetry.add_argument("--attempt", type=int, required=True)
    telemetry.add_argument("--kind", choices=("agent", "human_wait"), required=True)
    telemetry.add_argument("--started-at", required=True)
    telemetry.add_argument("--ended-at", required=True)
    telemetry.add_argument("--result", choices=("run", "reuse", "skip", "blocked"), required=True)
    telemetry.add_argument("--count", action="append", default=[])
    telemetry.add_argument("--evidence", action="append", default=[])
    telemetry.add_argument("--note", default="")
    telemetry.set_defaults(handler=command_telemetry)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if getattr(arguments, "max_age_hours", DEFAULT_MAX_AGE_HOURS) <= 0:
        print("error: --max-age-hours must be positive", file=sys.stderr)
        return 2
    try:
        return arguments.handler(arguments)
    except EvidenceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
