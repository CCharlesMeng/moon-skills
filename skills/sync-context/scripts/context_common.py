#!/usr/bin/env python3
"""Shared helpers for sync-context automation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PurePosixPath


IMPACT_ORDER = ("structure", "reference", "feature")
REQUIRED_ASSETS = {
    "feature": [".project-context/features/index.yaml"],
    "reference": [".project-context/references.yaml"],
    "structure": [".project-context/profile.yaml"],
}
OPTIONAL_ASSETS = {
    "feature": [".project-context/PROFILE.md"],
    "reference": [".project-context/PROFILE.md"],
    "structure": [
        ".project-context/references.yaml",
        ".project-context/features/index.yaml",
        ".project-context/PROFILE.md",
    ],
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def backup_file(path: Path) -> Path:
    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup_path)
    return backup_path


def repo_root(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    output = run_git(repo, "diff", "--name-only", base, head)
    files: list[str] = []
    for line in output.splitlines():
        candidate = line.strip().replace("\\", "/")
        if not candidate:
            continue
        files.append(candidate)
    return files


def load_impact_rules(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"impact rules file not found: {path}")

    rules: dict[str, list[str]] = {"feature": [], "reference": [], "structure": []}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            current = stripped[:-1].strip()
            if current not in rules:
                rules[current] = []
            continue
        if stripped.startswith("- "):
            if current is None:
                raise ValueError(f"invalid rules file, list item without section: {raw_line}")
            value = stripped[2:].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            rules[current].append(value)
            continue
        raise ValueError(f"unsupported rules syntax: {raw_line}")
    return rules


def match_pattern(path: str, pattern: str) -> bool:
    return PurePosixPath(path).match(pattern)


def classify_impact(files: list[str], rules: dict[str, list[str]]) -> tuple[str, list[str]]:
    relevant_files = [path for path in files if not path.startswith(".project-context/")]
    reasons: list[str] = []
    seen_categories: set[str] = set()

    for category in IMPACT_ORDER:
        for path in relevant_files:
            for pattern in rules.get(category, []):
                if match_pattern(path, pattern):
                    seen_categories.add(category)
                    reasons.append(f"{category}: {path} matched {pattern}")
                    break

    for category in IMPACT_ORDER:
        if category in seen_categories:
            return category, reasons
    return "none", reasons


def required_assets_for_impact(impact: str) -> list[str]:
    return REQUIRED_ASSETS.get(impact, [])


def optional_assets_for_impact(impact: str) -> list[str]:
    return OPTIONAL_ASSETS.get(impact, [])
