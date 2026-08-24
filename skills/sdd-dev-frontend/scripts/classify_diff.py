#!/usr/bin/env python3
"""Derive the mechanical floor for a Story's validation portfolio from its diff.

Two outputs, both auditable:

- `risk_triggers`: triggers that path evidence alone makes certain. The portfolio
  may add to this set; it may not drop from it without recording a narrowing.
- `skip_rebuttals`: dimensions whose `skip_when` the diff contradicts. A rebutted
  dimension cannot be reported as `skipped`.

Everything here is a floor. Triggers needing semantic judgement (`async-state`,
`spec-gap`, `unknown-deps`, `performance`) are never emitted, and every emitted
fact carries the path or line that produced it.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1

DEFAULT_SHARED_PATHS = (
    "*/shared/*", "*/common/*", "*/components/*", "*/hooks/*",
    "*/utils/*", "*/lib/*", "*/api/*", "*/store/*", "*/styles/*",
)
STYLE_SUFFIXES = (".css", ".scss", ".sass", ".less", ".styl")
TEMPLATE_SUFFIXES = (".html", ".vue", ".svelte")
# 内容与路径规则只作用于源码。文档提到 `axios` 或 `i18n` 是在讨论它，不是在用它。
CODE_SUFFIXES = (
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".html",
) + STYLE_SUFFIXES
TOKEN_NAMES = ("tailwind.config", "theme", "tokens", "design-tokens")
BUILD_NAMES = (
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "babel.config", "jest.config", "vitest.config", "playwright.config",
    "vite.config", "webpack.config", "rollup.config", "next.config",
    "tsconfig", ".eslintrc", ".prettierrc", "eslint.config", "postcss.config",
)
ROUTE_PARTS = ("/router/", "/routes/")

# 每条内容规则只在能引用具体新增行时才成立；引用不到就不产出事实。
CONTENT_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("C4", "request-or-cancellation", re.compile(
        r"\bfetch\(|\baxios\b|XMLHttpRequest|useQuery|useMutation|AbortController|\.catch\("
    )),
    ("C6", "check-suppression", re.compile(
        r"@ts-ignore|@ts-expect-error|eslint-disable|tslint:disable"
    )),
    ("C7", "i18n-mechanism", re.compile(
        r"\bi18n\b|useTranslation|FormattedMessage|/locales/"
    )),
    ("Q7", "debug-or-placeholder-residue", re.compile(
        r"\bTODO\b|\bFIXME\b|console\.(?:log|debug|warn)\(|\bdebugger\b"
    )),
)


class ClassifyError(RuntimeError):
    """Raised when the diff cannot be read well enough to produce a floor."""


def git(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ClassifyError(f"git-unavailable: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ClassifyError(f"git-failed: {detail or 'unknown error'}")
    return result.stdout.decode("utf-8", errors="replace")


def changed_files(repo_root: Path, base_ref: str) -> list[dict[str, str]]:
    """Tracked changes against base plus untracked files, deletions excluded."""
    records: dict[str, str] = {}
    raw = git(repo_root, "diff", "--name-status", "--find-renames", "-z", base_ref)
    fields = [field for field in raw.split("\0") if field]
    index = 0
    while index < len(fields):
        status = fields[index]
        if status.startswith("R") and index + 2 < len(fields):
            records[fields[index + 2]] = "R"
            index += 3
            continue
        if index + 1 >= len(fields):
            break
        path = fields[index + 1]
        if status != "D":
            records[path] = status[:1]
        index += 2
    for path in git(repo_root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
        if path:
            records.setdefault(path, "A")
    return [{"path": path, "status": records[path]} for path in sorted(records)]


def added_lines(repo_root: Path, base_ref: str, files: list[dict[str, str]]) -> list[tuple[str, str]]:
    """(path, line) for every added line, so content rules can cite evidence."""
    lines: list[tuple[str, str]] = []
    tracked = [
        item["path"] for item in files
        if item["status"] != "A" and is_code(item["path"])
    ]
    if tracked:
        current: str | None = None
        raw = git(repo_root, "diff", "--unified=0", "--find-renames", base_ref, "--", *tracked)
        for line in raw.splitlines():
            if line.startswith("+++ b/"):
                current = line[6:]
            elif line.startswith("+") and not line.startswith("+++") and current:
                lines.append((current, line[1:].strip()))
    for item in files:
        if item["status"] != "A" or not is_code(item["path"]):
            continue
        path = repo_root / item["path"]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines.extend((item["path"], line.strip()) for line in text.splitlines())
    return lines


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    candidate = f"/{path}"
    return any(fnmatch.fnmatch(candidate, pattern) for pattern in patterns)


def is_code(path: str) -> bool:
    return path.lower().endswith(CODE_SUFFIXES)


def is_style(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(STYLE_SUFFIXES):
        return True
    return is_code(path) and any(name in Path(lowered).name for name in TOKEN_NAMES)


def is_build_config(path: str) -> bool:
    name = Path(path).name.lower()
    return any(name.startswith(item) or name == item for item in BUILD_NAMES)


def fact(rule: str, evidence: str) -> dict[str, str]:
    return {"rule": rule, "evidence": evidence}


def classify(
    files: list[dict[str, str]],
    lines: list[tuple[str, str]],
    shared_paths: tuple[str, ...],
) -> dict[str, list[dict[str, str]]]:
    triggers: dict[str, list[dict[str, str]]] = {}
    rebuttals: dict[str, list[dict[str, str]]] = {}

    def add(bucket: dict[str, list[dict[str, str]]], key: str, rule: str, evidence: str) -> None:
        entries = bucket.setdefault(key, [])
        if not any(item["evidence"] == evidence and item["rule"] == rule for item in entries):
            entries.append(fact(rule, evidence))

    for item in files:
        path = item["path"]
        lowered = path.lower()
        if is_build_config(path):
            add(triggers, "build-config", "build-config-file", path)
        if not is_code(path):
            continue
        if is_style(path):
            add(triggers, "visual", "style-or-token-file", path)
            add(rebuttals, "C3", "style-or-token-file", path)
        if lowered.endswith(TEMPLATE_SUFFIXES):
            add(triggers, "visual", "template-file", path)
        if any(part in f"/{lowered}" for part in ROUTE_PARTS) or "rout" in Path(lowered).stem:
            add(triggers, "navigation", "route-file", path)
        if matches_any(path, shared_paths):
            add(triggers, "shared-boundary", "shared-path", path)
        if item["status"] in {"A", "R"}:
            add(rebuttals, "C1", "added-or-renamed-file", f"{path} ({item['status']})")

    for path, line in lines:
        if not is_code(path):
            continue
        for dimension, rule, pattern in CONTENT_RULES:
            if pattern.search(line):
                add(rebuttals, dimension, rule, f"{path}: {line[:120]}")
    return {"risk_triggers": triggers, "skip_rebuttals": rebuttals}


def build(repo_root: Path, base_ref: str, shared_paths: tuple[str, ...]) -> dict[str, Any]:
    resolved = repo_root.resolve()
    head = git(resolved, "rev-parse", "HEAD").strip()
    files = changed_files(resolved, base_ref)
    lines = added_lines(resolved, base_ref, files)
    classified = classify(files, lines, shared_paths)
    return {
        "schema_version": SCHEMA_VERSION,
        "base_ref": base_ref,
        "head": head,
        "shared_paths": list(shared_paths),
        "changed_files": files,
        **classified,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument(
        "--shared-path", action="append", default=[],
        help="glob for this repo's shared boundary; repeatable, defaults to common layouts",
    )
    parser.add_argument("--out", help="write JSON here instead of stdout")
    arguments = parser.parse_args(argv)
    shared = tuple(arguments.shared_path) or DEFAULT_SHARED_PATHS
    try:
        payload = build(Path(arguments.repo_root), arguments.base_ref, shared)
    except ClassifyError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.out:
        Path(arguments.out).write_text(text, encoding="utf-8")
        print(json.dumps(
            {
                "risk_triggers": sorted(payload["risk_triggers"]),
                "skip_rebuttals": sorted(payload["skip_rebuttals"]),
                "changed_files": len(payload["changed_files"]),
            },
            ensure_ascii=False, sort_keys=True,
        ))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
