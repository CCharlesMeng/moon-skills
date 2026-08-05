#!/usr/bin/env python3
"""Discover, fingerprint, validate, and finalize frontend repository baselines."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
SECTION_TITLES = {
    "REPO-1": "环境与运行",
    "REPO-2": "工程质量",
    "REPO-3": "工程范式",
}
READY_STATES = {"READY", "READY_WITH_LIMITS", "BLOCKED"}
IGNORED_DIRS = {
    ".agents",
    ".codex",
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    ".yarn",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
    "target",
    "vendor",
}
LOCKFILES = {
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
}
ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".defaults")
QUALITY_TOKENS = (
    "eslint",
    "prettier",
    "biome",
    "stylelint",
    "jest",
    "vitest",
    "playwright",
    "cypress",
    "test",
    "lint",
    "tsconfig",
    "babel",
    "swc",
)
CONVENTION_TOKENS = (
    "route",
    "router",
    "menu",
    "permission",
    "auth",
    "theme",
    "style",
    "token",
    "request",
    "client",
    "api",
    "hook",
    "util",
    "form",
    "store",
    "state",
    "feature",
    "flag",
    "analytics",
    "track",
    "schema",
    "codegen",
)
SOURCE_SUFFIXES = {
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".graphql",
    ".gql",
    ".json",
    ".yaml",
    ".yml",
}


class BaselineError(RuntimeError):
    """A user-actionable baseline failure."""


class AmbiguousTarget(BaselineError):
    def __init__(self, candidates: list[str]) -> None:
        super().__init__("multiple target apps found")
        self.candidates = candidates


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BaselineError(f"expected JSON object in {path}")
    return data


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".cache"))
        current_path = Path(current)
        for name in sorted(names):
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                continue
            files.append(path)
    return files


def is_env_template(path: Path) -> bool:
    name = path.name.lower()
    if not name.startswith(".env"):
        return False
    if name in {".env", ".env.local", ".env.development", ".env.production", ".env.test"}:
        return False
    return name.endswith(ENV_TEMPLATE_SUFFIXES) or any(
        marker in name for marker in (".example.", ".sample.", ".template.")
    )


def has_path_token(value: str, token: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", value))


def classify_inputs(files: Iterable[Path], root: Path, target: Path | None = None) -> dict[str, list[Path]]:
    result = {section: [] for section in SECTION_TITLES}
    readme_roots = {root.resolve(), (target or root).resolve()}
    for path in files:
        rel = relative(path, root)
        lower = rel.lower()
        name = path.name.lower()
        suffix = path.suffix.lower()

        common_manifest = name == "package.json"
        repo1 = (
            common_manifest
            or name in LOCKFILES
            or name in {".nvmrc", ".node-version", ".tool-versions", "pnpm-workspace.yaml"}
            or is_env_template(path)
            or name.startswith(("vite.config", "next.config", "nuxt.config", "webpack.config"))
            or name.startswith(("docker-compose", "compose."))
            or (name in {"readme.md", "readme"} and path.parent.resolve() in readme_roots)
        )
        repo2 = common_manifest or (
            suffix in SOURCE_SUFFIXES and any(has_path_token(lower, token) for token in QUALITY_TOKENS)
        )
        if lower.startswith((".github/workflows/", ".gitlab/")):
            repo2 = True
        repo3 = common_manifest or (
            suffix in SOURCE_SUFFIXES and any(token in lower for token in CONVENTION_TOKENS)
        )

        if repo1:
            result["REPO-1"].append(path)
        if repo2:
            result["REPO-2"].append(path)
        if repo3:
            result["REPO-3"].append(path)
    return result


def input_records(paths: Iterable[Path], root: Path) -> list[dict[str, str]]:
    records = []
    for path in sorted(set(paths), key=lambda item: relative(item, root)):
        try:
            digest = sha256_file(path)
        except OSError:
            digest = "unreadable"
        records.append({"path": relative(path, root), "sha256": digest})
    return records


def fingerprint(records: list[dict[str, str]]) -> str:
    canonical = "\n".join(
        f"{record['path']}\t{record['sha256']}"
        for record in sorted(records, key=lambda item: item["path"])
    )
    return sha256_bytes(canonical.encode("utf-8"))


def load_package(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BaselineError(f"package.json not found: {path}")
    return read_json(path)


def frontend_score(package: dict[str, Any]) -> int:
    scripts = package.get("scripts") or {}
    deps = {}
    deps.update(package.get("dependencies") or {})
    deps.update(package.get("devDependencies") or {})
    score = 0
    if any(name in scripts for name in ("dev", "start", "serve", "preview")):
        score += 2
    if any(name in deps for name in ("react", "vue", "svelte", "next", "nuxt", "@angular/core")):
        score += 2
    if any(name in deps for name in ("vite", "webpack", "parcel")):
        score += 1
    return score


def discover_target_app(root: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = (root / explicit).resolve() if not Path(explicit).is_absolute() else Path(explicit).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise BaselineError("target app must be inside repo root") from exc
        load_package(candidate / "package.json")
        return candidate

    candidates: list[tuple[Path, int]] = []
    root_package = root / "package.json"
    if root_package.exists():
        candidates.append((root, frontend_score(load_package(root_package))))

    for path in walk_files(root):
        if path.name != "package.json" or path == root_package:
            continue
        rel_parts = path.relative_to(root).parts
        if len(rel_parts) > 5:
            continue
        package = load_package(path)
        score = frontend_score(package)
        if score > 0:
            candidates.append((path.parent, score))

    if not candidates:
        raise BaselineError("no frontend package.json candidate found")

    best_score = max(score for _, score in candidates)
    best = sorted({relative(path, root) or "." for path, score in candidates if score == best_score})
    if len(best) > 1:
        raise AmbiguousTarget(best)
    return root if best[0] == "." else root / best[0]


def detect_package_manager(root_package: dict[str, Any], root: Path) -> dict[str, Any]:
    declared = root_package.get("packageManager")
    name = None
    version = None
    if isinstance(declared, str) and "@" in declared:
        name, version = declared.split("@", 1)
    lockfile = None
    for filename, manager in LOCKFILES.items():
        if (root / filename).exists():
            lockfile = filename
            name = name or manager
            break
    name = name or "npm"
    install = {
        "pnpm": "pnpm install --frozen-lockfile",
        "yarn": "yarn install --immutable",
        "npm": "npm ci" if lockfile in {"package-lock.json", "npm-shrinkwrap.json"} else "npm install",
        "bun": "bun install --frozen-lockfile",
    }.get(name, f"{name} install")
    return {
        "name": name,
        "declared_version": version,
        "lockfile": lockfile,
        "install_command": install,
    }


def node_constraints(root: Path, root_package: dict[str, Any], target_package: dict[str, Any]) -> list[dict[str, str]]:
    constraints: list[dict[str, str]] = []
    for source, package in (("package.json", root_package), ("target package.json", target_package)):
        engines = package.get("engines") or {}
        if isinstance(engines, dict) and isinstance(engines.get("node"), str):
            entry = {"source": source, "value": engines["node"]}
            if not any(item["value"] == entry["value"] for item in constraints):
                constraints.append(entry)
    for filename in (".nvmrc", ".node-version", ".tool-versions"):
        path = root / filename
        if path.exists():
            value = safe_text(path).strip()
            if value:
                constraints.append({"source": filename, "value": value})
    return constraints


def command_for(manager: str, script: str) -> str:
    if manager == "yarn":
        return f"yarn {script}"
    return f"{manager} run {script}"


def classify_script(name: str) -> str | None:
    lower = name.lower()
    if lower in {"dev", "start", "serve", "preview"} or lower.startswith(("dev:", "start:", "serve:")):
        return "runtime"
    if "typecheck" in lower or "type-check" in lower or lower in {"check", "check-types", "check:types"}:
        return "typecheck"
    if "e2e" in lower or "playwright" in lower or "cypress" in lower:
        return "e2e"
    if "integration" in lower:
        return "integration"
    if "codegen" in lower or "generate" in lower and ("api" in lower or "schema" in lower):
        return "codegen"
    if lower == "test" or lower.startswith("test:"):
        return "test"
    if lower == "lint" or lower.startswith("lint:"):
        return "lint"
    if "format" in lower and ("check" in lower or lower in {"format", "fmt"}):
        return "format"
    if lower == "build" or lower.startswith("build:"):
        return "build"
    if any(token in lower for token in ("mock", "fixture", "seed")):
        return "runtime_support"
    return None


def discover_commands(package: dict[str, Any], manager: str, cwd: str) -> dict[str, list[dict[str, str]]]:
    categories = {
        "runtime": [],
        "runtime_support": [],
        "test": [],
        "typecheck": [],
        "lint": [],
        "format": [],
        "build": [],
        "integration": [],
        "e2e": [],
        "codegen": [],
    }
    scripts = package.get("scripts") or {}
    if not isinstance(scripts, dict):
        return categories
    for name in sorted(scripts):
        category = classify_script(name)
        if category:
            categories[category].append(
                {
                    "script": name,
                    "command": command_for(manager, name),
                    "cwd": cwd,
                    "source": f"{cwd}/package.json" if cwd != "." else "package.json",
                }
            )
    return categories


def sensitive_env_key(key: str) -> bool:
    return bool(re.search(r"(secret|token|password|passwd|private|credential|api_?key)", key, re.I))


def discover_env_contract(files: Iterable[Path], root: Path) -> dict[str, Any]:
    templates = sorted((path for path in files if is_env_template(path)), key=lambda p: relative(p, root))
    variables: dict[str, dict[str, Any]] = {}
    pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
    for path in templates:
        for line in safe_text(path).splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = pattern.match(line)
            if not match:
                continue
            key, value = match.groups()
            entry = variables.setdefault(
                key,
                {
                    "key": key,
                    "sensitive": sensitive_env_key(key),
                    "has_template_default": bool(value.strip()),
                    "sources": [],
                },
            )
            entry["has_template_default"] = entry["has_template_default"] or bool(value.strip())
            source = relative(path, root)
            if source not in entry["sources"]:
                entry["sources"].append(source)
    return {
        "templates": [relative(path, root) for path in templates],
        "variables": [variables[key] for key in sorted(variables)],
        "secrets_policy": "store keys and readiness only; never store values",
    }


DEPENDENCY_GROUPS = {
    "framework": ("react", "react-dom", "vue", "svelte", "next", "nuxt", "@angular/core"),
    "ui": ("antd", "@mui/material", "@chakra-ui/react", "element-plus", "vuetify", "naive-ui"),
    "state": ("redux", "@reduxjs/toolkit", "zustand", "pinia", "mobx", "jotai", "recoil"),
    "form": ("react-hook-form", "formik", "final-form", "vee-validate"),
    "style": ("tailwindcss", "styled-components", "@emotion/react", "sass", "less"),
    "request": ("axios", "ky", "swr", "@tanstack/react-query", "urql", "@apollo/client"),
    "test": ("jest", "vitest", "playwright", "@playwright/test", "cypress", "testing-library"),
    "codegen": ("openapi", "orval", "graphql-codegen", "@graphql-codegen/cli"),
}


def dependency_groups(packages: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    combined: dict[str, str] = {}
    for package in packages:
        for field in ("dependencies", "devDependencies", "peerDependencies"):
            values = package.get(field) or {}
            if isinstance(values, dict):
                for name, version in values.items():
                    if isinstance(version, str):
                        combined[name] = version
    result: dict[str, list[dict[str, str]]] = {}
    for group, needles in DEPENDENCY_GROUPS.items():
        matches = []
        for name, version in sorted(combined.items()):
            lower = name.lower()
            if any(needle in lower for needle in needles):
                matches.append({"name": name, "version": version})
        result[group] = matches
    return result


def convention_candidates(files: Iterable[Path], root: Path) -> dict[str, list[str]]:
    groups = {
        "routing_menu_permissions": ("route", "router", "menu", "permission", "auth"),
        "theme_tokens_styles": ("theme", "token", "style"),
        "requests_and_api": ("request", "client", "api"),
        "hooks_utils_forms_state": ("hook", "util", "form", "store", "state"),
        "feature_flags_analytics": ("feature", "flag", "analytics", "track"),
        "schema_codegen": ("schema", "codegen", "graphql", "openapi"),
    }
    result: dict[str, list[str]] = {}
    for group, needles in groups.items():
        matched = []
        for path in files:
            rel = relative(path, root)
            lower = rel.lower()
            if path.suffix.lower() in SOURCE_SUFFIXES and any(
                has_path_token(lower, needle) for needle in needles
            ):
                matched.append(rel)
        result[group] = sorted(matched)[:200]
    return result


def git_metadata(root: Path) -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "remote": run("remote", "get-url", "origin"),
    }


def build_discovery(
    root: Path,
    target: Path,
    files: list[Path],
    section_inputs: dict[str, list[dict[str, str]]],
) -> dict[str, dict[str, Any]]:
    target_package = load_package(target / "package.json")
    root_package = load_package(root / "package.json") if (root / "package.json").exists() else target_package
    manager = detect_package_manager(root_package, root)
    target_rel = relative(target, root) or "."
    commands = discover_commands(target_package, manager["name"], target_rel)
    packages = [root_package] if target == root else [root_package, target_package]

    repo1 = {
        "toolchain": {
            "node_constraints": node_constraints(root, root_package, target_package),
            "package_manager": manager,
            "workspace": root_package.get("workspaces"),
            "git": git_metadata(root),
        },
        "target_app": {
            "path": target_rel,
            "package_name": target_package.get("name"),
            "private": target_package.get("private"),
        },
        "environment_contract": discover_env_contract(files, root),
        "runtime_commands": {
            "start": commands["runtime"],
            "support": commands["runtime_support"],
        },
        "runtime_candidates": [
            record["path"]
            for record in section_inputs["REPO-1"]
            if any(
                token in record["path"].lower()
                for token in ("vite", "next", "nuxt", "webpack", "proxy", "docker", "compose", "readme")
            )
        ],
        "rendering_contract": {
            "browser": "unknown",
            "viewport": "unknown",
            "dpr": "unknown",
            "fonts": "unknown",
            "locale": "unknown",
            "timezone": "unknown",
            "screenshot": "unverified",
            "structured_capture": "unverified",
        },
    }
    repo2 = {
        "commands": {key: commands[key] for key in (
            "test",
            "typecheck",
            "lint",
            "format",
            "build",
            "integration",
            "e2e",
            "codegen",
        )},
        "configuration_candidates": [
            record["path"] for record in section_inputs["REPO-2"] if record["path"] != "package.json"
        ],
    }
    repo3 = {
        "dependency_candidates": dependency_groups(packages),
        "evidence_candidates": convention_candidates(files, root),
        "source_roots": sorted(
            {
                relative(path.parent, root)
                for path in files
                if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte"}
                and any(part in {"src", "app", "pages"} for part in path.relative_to(root).parts)
            }
        )[:100],
    }
    return {"REPO-1": repo1, "REPO-2": repo2, "REPO-3": repo3}


AUTO_HEADING = "自动发现（脚本维护）"
MANUAL_HEADING = "人工维护（agent 维护）"
LEGACY_FILES = ("manifest.json", "repo-baseline.json")


def default_readiness(reason: str = "onboarding not finalized") -> dict[str, Any]:
    return {
        "status": "DRAFT",
        "verified_at": None,
        "report_sha256": None,
        "reason": reason,
    }


def table_cell(value: Any) -> str:
    return str(value).replace("\n", "<br>").replace("|", r"\|")


def md_code(value: Any) -> str:
    rendered = str(value).replace("`", "'")
    return f"`{rendered}`"


def render_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    rendered = [
        "| " + " | ".join(table_cell(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    rendered.extend(
        "| " + " | ".join(table_cell(value) for value in row) + " |"
        for row in rows
    )
    return rendered


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells: list[str] = []
    buffer: list[str] = []
    escaped = False
    for char in stripped[1:-1]:
        if escaped:
            buffer.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
    if escaped:
        buffer.append("\\")
    cells.append("".join(buffer).strip())
    return cells


def uncode(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def first_table(block: str) -> tuple[list[str], list[list[str]]]:
    lines = block.splitlines()
    for index in range(len(lines) - 1):
        headers = split_markdown_row(lines[index])
        separator = split_markdown_row(lines[index + 1])
        if not headers or len(headers) != len(separator):
            continue
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator):
            continue
        rows: list[list[str]] = []
        for line in lines[index + 2 :]:
            row = split_markdown_row(line)
            if not row:
                break
            if len(row) == len(headers):
                rows.append(row)
        return headers, rows
    return [], []


def heading_block(text: str, heading: str, level: int, include_heading: bool = False) -> str:
    lines = text.splitlines()
    marker = "#" * level + " " + heading
    try:
        start = lines.index(marker)
    except ValueError:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,%d})\s+" % level, lines[index])
        if match:
            end = index
            break
    selected = lines[start if include_heading else start + 1 : end]
    return "\n".join(selected).strip("\n")


def nested_heading_block(parent: str, heading: str, level: int) -> str:
    return heading_block(parent, heading, level, include_heading=False)


def parse_status_table(text: str) -> dict[str, str]:
    _, rows = first_table(heading_block(text, "状态", 2))
    return {
        uncode(row[0]): uncode(row[1])
        for row in rows
        if len(row) >= 2
    }


def parse_section_index(text: str) -> dict[str, dict[str, Any]]:
    _, rows = first_table(heading_block(text, "Section", 2))
    sections: dict[str, dict[str, Any]] = {}
    for row in rows:
        if len(row) < 4:
            continue
        section_id = uncode(row[0])
        if section_id not in SECTION_TITLES:
            continue
        try:
            input_count = int(uncode(row[3]))
        except ValueError:
            input_count = -1
        sections[section_id] = {
            "title": row[1],
            "fingerprint": uncode(row[2]),
            "input_count": input_count,
        }
    return sections


def parse_input_ledgers(text: str) -> dict[str, list[dict[str, str]]]:
    ledger = heading_block(text, "新鲜度账本", 2)
    result: dict[str, list[dict[str, str]]] = {}
    for section_id in SECTION_TITLES:
        _, rows = first_table(nested_heading_block(ledger, section_id, 3))
        result[section_id] = [
            {"path": uncode(row[0]), "sha256": uncode(row[1])}
            for row in rows
            if len(row) >= 2
        ]
    return result


def parse_baseline_markdown(text: str) -> dict[str, Any]:
    status = parse_status_table(text)
    try:
        schema_version = int(status.get("schema_version", "0"))
    except ValueError:
        schema_version = 0
    section_index = parse_section_index(text)
    inputs = parse_input_ledgers(text)
    sections: dict[str, dict[str, Any]] = {}
    for section_id, title in SECTION_TITLES.items():
        section_text = heading_block(text, f"{section_id} {title}", 2)
        sections[section_id] = {
            **(section_index.get(section_id) or {}),
            "inputs": inputs.get(section_id, []),
            "auto": nested_heading_block(section_text, AUTO_HEADING, 3),
            "manual": nested_heading_block(section_text, MANUAL_HEADING, 3),
        }
    return {
        "schema_version": schema_version,
        "repo_id": status.get("repo_id"),
        "repo_root": status.get("repo_root"),
        "target_app": status.get("target_app"),
        "generated_at": status.get("generated_at"),
        "readiness": {
            "status": status.get("readiness", "DRAFT"),
            "verified_at": status.get("verified_at"),
            "report_sha256": status.get("report_sha256"),
            "reason": status.get("reason"),
        },
        "sections": sections,
        "text": text,
    }


def readable_value(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(item for item in (readable_value(child) for child in value) if item)
    if isinstance(value, dict):
        return "；".join(
            f"{key}={rendered}"
            for key, child in value.items()
            if (rendered := readable_value(child))
        )
    return str(value)


def collect_evidence(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"path", "file", "source_path"} and isinstance(child, str):
                paths.append(child.split("#", 1)[0])
            paths.extend(collect_evidence(child))
    elif isinstance(value, list):
        for child in value:
            paths.extend(collect_evidence(child))
    return list(dict.fromkeys(path for path in paths if path))


def flatten_curated(value: Any, prefix: str = "") -> list[list[str]]:
    rows: list[list[str]] = []
    if not isinstance(value, dict):
        rendered = readable_value(value)
        return [[prefix or "结论", rendered]] if rendered else []
    for key, child in value.items():
        if key in {"evidence", "path", "file", "source_path"}:
            continue
        label = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            rows.extend(flatten_curated(child, label))
        else:
            rendered = readable_value(child)
            if rendered:
                rows.append([label, rendered])
    return rows


def legacy_manual_block(section_id: str, curated: dict[str, Any]) -> str:
    if not curated:
        return ""
    prefix = {"REPO-1": "CONTRACT", "REPO-2": "QUALITY", "REPO-3": "PATTERN"}[section_id]
    lines: list[str] = []
    for key, value in curated.items():
        slug = re.sub(r"[^A-Z0-9]+", "-", key.upper()).strip("-") or "FACT"
        title = key.replace("_", " ")
        lines.extend([f"#### `{prefix}-{slug}` · {title}", ""])
        rows = flatten_curated(value)
        if rows:
            lines.extend(render_table(["项", "内容"], rows))
            lines.append("")
        evidence = collect_evidence(value)
        if evidence:
            lines.extend(["##### 证据", ""])
            lines.extend(render_table(["路径"], [[md_code(path)] for path in evidence]))
            lines.append("")
    return "\n".join(lines).strip()


def load_existing_baseline(baseline_dir: Path) -> tuple[dict[str, Any], bool]:
    markdown_path = baseline_dir / "repo-baseline.md"
    if markdown_path.exists():
        parsed = parse_baseline_markdown(markdown_path.read_text(encoding="utf-8"))
        if parsed["schema_version"] == SCHEMA_VERSION:
            return parsed, False
    legacy_baseline_path = baseline_dir / "repo-baseline.json"
    legacy_manifest_path = baseline_dir / "manifest.json"
    if legacy_baseline_path.exists() and legacy_manifest_path.exists():
        legacy = read_json(legacy_baseline_path)
        manifest = read_json(legacy_manifest_path)
        legacy_sections = legacy.get("sections") or {}
        sections: dict[str, dict[str, Any]] = {}
        for section_id in SECTION_TITLES:
            manifest_section = (manifest.get("sections") or {}).get(section_id) or {}
            legacy_section = legacy_sections.get(section_id) or {}
            sections[section_id] = {
                "title": SECTION_TITLES[section_id],
                "fingerprint": manifest_section.get("fingerprint"),
                "input_count": len(manifest_section.get("inputs") or []),
                "inputs": manifest_section.get("inputs") or [],
                "auto": "",
                "manual": legacy_manual_block(section_id, legacy_section.get("curated") or {}),
            }
        repository = legacy.get("repository") or {}
        return {
            "schema_version": manifest.get("schema_version", 1),
            "repo_id": manifest.get("repo_id") or repository.get("id"),
            "repo_root": manifest.get("repo_root") or repository.get("root"),
            "target_app": manifest.get("target_app") or repository.get("target_app"),
            "generated_at": manifest.get("generated_at") or legacy.get("generated_at"),
            "readiness": manifest.get("readiness") or default_readiness(),
            "sections": sections,
            "text": "",
        }, True
    if markdown_path.exists():
        raise BaselineError("repo-baseline.md does not match Markdown baseline contract v2")
    return {}, False


def declared_evidence_paths_markdown(manual: str, root: Path) -> list[Path]:
    paths: list[Path] = []
    for raw in re.findall(r"`([^`]+)`", manual):
        normalized = raw.split("#", 1)[0].strip()
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            continue
        if candidate.is_file() and candidate not in paths:
            paths.append(candidate)
    return paths


def render_repo1(discovered: dict[str, Any]) -> str:
    lines: list[str] = []
    toolchain = discovered["toolchain"]
    manager = toolchain["package_manager"]
    rows: list[list[Any]] = [
        ["包管理器", md_code(manager["name"]), md_code("package.json")],
        ["安装命令", md_code(manager["install_command"]), md_code(manager["lockfile"] or "package.json")],
        ["目标 app", md_code(discovered["target_app"]["path"]), md_code("package.json")],
    ]
    if manager.get("declared_version"):
        rows.append(["包管理器版本", md_code(manager["declared_version"]), md_code("package.json#packageManager")])
    if manager.get("lockfile"):
        rows.append(["lockfile", md_code(manager["lockfile"]), md_code(manager["lockfile"])])
    if discovered["target_app"].get("package_name"):
        rows.append(["包名", md_code(discovered["target_app"]["package_name"]), md_code("package.json#name")])
    for constraint in toolchain["node_constraints"]:
        rows.append(["Node 约束", md_code(constraint["value"]), md_code(constraint["source"])])
    lines.extend(["#### 工具链与目标 app", ""])
    lines.extend(render_table(["项", "结论", "证据"], rows))

    variables = discovered["environment_contract"]["variables"]
    if variables:
        lines.extend(["", "#### 环境变量契约", ""])
        lines.extend(
            render_table(
                ["键", "敏感", "模板默认值", "来源"],
                [
                    [
                        md_code(item["key"]),
                        "是" if item["sensitive"] else "否",
                        "有" if item["has_template_default"] else "需提供",
                        "、".join(md_code(source) for source in item["sources"]),
                    ]
                    for item in variables
                ],
            )
        )

    commands = discovered["runtime_commands"]
    runtime_rows = [
        ["启动", md_code(item["command"]), md_code(item["cwd"]), md_code(item["source"])]
        for item in commands["start"]
    ] + [
        ["辅助", md_code(item["command"]), md_code(item["cwd"]), md_code(item["source"])]
        for item in commands["support"]
    ]
    if runtime_rows:
        lines.extend(["", "#### 运行命令", ""])
        lines.extend(render_table(["用途", "命令", "工作目录", "证据"], runtime_rows))
    else:
        lines.extend(["", "#### 待处理动作", ""])
        lines.extend(
            render_table(
                ["ID", "能力", "影响", "补齐动作"],
                [[
                    md_code("ACTION-RUNTIME-1"),
                    "目标 app 启动",
                    "无法完成页面与浏览器实证",
                    "确认并补齐 package.json 中的 dev/start/serve/preview 脚本",
                ]],
            )
        )

    candidates = discovered["runtime_candidates"]
    if candidates:
        lines.extend(["", "#### 运行配置入口", ""])
        lines.extend(render_table(["路径"], [[md_code(path)] for path in candidates]))
    return "\n".join(lines).strip()


def render_repo2(discovered: dict[str, Any]) -> str:
    command_rows: list[list[Any]] = []
    for category, commands in discovered["commands"].items():
        for item in commands:
            command_rows.append([
                category,
                md_code(item["command"]),
                md_code(item["cwd"]),
                md_code(item["source"]),
            ])
    lines: list[str] = []
    if command_rows:
        lines.extend(["#### 规范质量命令", ""])
        lines.extend(render_table(["类别", "命令", "工作目录", "证据"], command_rows))
    candidates = discovered["configuration_candidates"]
    if candidates:
        if lines:
            lines.append("")
        lines.extend(["#### 质量配置入口", ""])
        lines.extend(render_table(["路径"], [[md_code(path)] for path in candidates]))
    return "\n".join(lines).strip()


def render_repo3(discovered: dict[str, Any]) -> str:
    lines: list[str] = []
    dependency_rows = [
        [category, md_code(item["name"]), md_code(item["version"])]
        for category, values in discovered["dependency_candidates"].items()
        for item in values
    ]
    if dependency_rows:
        lines.extend(["#### 技术依赖候选", ""])
        lines.extend(render_table(["类别", "依赖", "版本"], dependency_rows))
    evidence_rows = [
        [category, md_code(path)]
        for category, paths in discovered["evidence_candidates"].items()
        for path in paths
    ]
    if evidence_rows:
        if lines:
            lines.append("")
        lines.extend(["#### 范式证据入口", ""])
        lines.extend(render_table(["类别", "路径"], evidence_rows))
    if discovered["source_roots"]:
        if lines:
            lines.append("")
        lines.extend(["#### 源码入口", ""])
        lines.extend(render_table(["路径"], [[md_code(path)] for path in discovered["source_roots"]]))
    return "\n".join(lines).strip()


def render_auto_section(section_id: str, discovered: dict[str, Any]) -> str:
    return {
        "REPO-1": render_repo1,
        "REPO-2": render_repo2,
        "REPO-3": render_repo3,
    }[section_id](discovered)


def render_baseline(baseline: dict[str, Any]) -> str:
    readiness = baseline["readiness"]
    status_rows: list[list[Any]] = [
        [md_code("schema_version"), md_code(SCHEMA_VERSION)],
        [md_code("repo_id"), md_code(baseline["repo_id"])],
        [md_code("repo_root"), md_code(baseline["repo_root"])],
        [md_code("target_app"), md_code(baseline["target_app"])],
        [md_code("readiness"), md_code(readiness["status"])],
        [md_code("generated_at"), md_code(baseline["generated_at"])],
    ]
    for field in ("verified_at", "report_sha256", "reason"):
        if readiness.get(field):
            status_rows.append([md_code(field), md_code(readiness[field])])

    lines = [
        f"# Frontend Repository Baseline — {baseline['repo_id']}",
        "",
        "> 本文件是仓库级 REPO-1～3 的唯一事实源；当前机器实证见 `onboarding-report.md`。",
        "",
        "## 状态",
        "",
        *render_table(["字段", "值"], status_rows),
        "",
        "## Section",
        "",
        *render_table(
            ["ID", "名称", "指纹", "输入数"],
            [
                [
                    md_code(section_id),
                    SECTION_TITLES[section_id],
                    md_code(baseline["sections"][section_id]["fingerprint"]),
                    len(baseline["sections"][section_id]["inputs"]),
                ]
                for section_id in SECTION_TITLES
            ],
        ),
    ]
    for section_id, title in SECTION_TITLES.items():
        section = baseline["sections"][section_id]
        auto = section.get("auto", "").strip()
        manual = section.get("manual", "").strip()
        if not auto and not manual:
            continue
        lines.extend(["", f"## {section_id} {title}"])
        if auto:
            lines.extend(["", f"### {AUTO_HEADING}", "", auto])
        if manual:
            lines.extend(["", f"### {MANUAL_HEADING}", "", manual])

    lines.extend(["", "## 新鲜度账本"])
    for section_id in SECTION_TITLES:
        lines.extend(["", f"### {section_id}", ""])
        lines.extend(
            render_table(
                ["路径", "SHA-256"],
                [
                    [md_code(item["path"]), md_code(item["sha256"])]
                    for item in baseline["sections"][section_id]["inputs"]
                ],
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def default_report(repo_id: str, root: Path, target_rel: str, fingerprints: dict[str, str]) -> str:
    return f"""# Frontend Onboarding Report — {repo_id}

## 结论

| 项 | 值 |
| --- | --- |
| 状态 | `DRAFT` |
| 仓库 | `{root}` |
| 目标 app | `{target_rel}` |
| 执行时间 | 待执行 |
| baseline 指纹 | `REPO-1 {fingerprints['REPO-1'][:12]}` / `REPO-2 {fingerprints['REPO-2'][:12]}` / `REPO-3 {fingerprints['REPO-3'][:12]}` |

## 下一步

- 准备当前开发必需的依赖、配置与服务，启动目标页面，并执行仓库实际存在的质量门禁。
- 完成后用实证替换本节；只保留适用事实，必要缺口写成具体补齐动作。

<!-- ONBOARDING_DRAFT -->
"""


def scan(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        raise BaselineError(f"repo root is not a directory: {root}")
    target = discover_target_app(root, args.target_app)
    baseline_dir = Path(args.baseline_dir).resolve()
    baseline_dir.mkdir(parents=True, exist_ok=True)
    repo_id = args.repo_id or root.name

    baseline_path = baseline_dir / "repo-baseline.md"
    existing, migrated_legacy = load_existing_baseline(baseline_dir)
    requested_sections = set(args.section or SECTION_TITLES)
    if args.section and (not existing or migrated_legacy):
        raise BaselineError("partial scan requires an existing complete baseline")
    files = walk_files(root)
    classified = classify_inputs(files, root, target)
    for section_id in SECTION_TITLES:
        for path in declared_evidence_paths_markdown(
            ((existing.get("sections") or {}).get(section_id) or {}).get("manual", ""),
            root,
        ):
            if path not in classified[section_id]:
                classified[section_id].append(path)
    records = {section: input_records(paths, root) for section, paths in classified.items()}
    fingerprints = {section: fingerprint(values) for section, values in records.items()}
    discovered = build_discovery(root, target, files, records)

    existing_sections = existing.get("sections") or {}
    old_fingerprints = {
        section: (existing_sections.get(section) or {}).get("fingerprint")
        for section in SECTION_TITLES
    }
    changed = [section for section in SECTION_TITLES if old_fingerprints[section] != fingerprints[section]]
    existing_root = existing.get("repo_root")
    root_changed = bool(existing_root) and Path(str(existing_root)).resolve() != root
    identity_changed = root_changed or (
        existing.get("target_app") not in {None, relative(target, root) or "."}
    )
    if identity_changed and args.section:
        raise BaselineError("partial scan cannot be used after repository identity or schema changes")
    if changed or identity_changed:
        readiness = default_readiness(
            "repository inputs changed: " + ", ".join(changed or ["identity"])
        )
    else:
        readiness = existing.get("readiness") or default_readiness()

    sections: dict[str, Any] = {}
    for section_id, title in SECTION_TITLES.items():
        previous = existing_sections.get(section_id) or {}
        if section_id in requested_sections or not previous:
            sections[section_id] = {
                "title": title,
                "fingerprint": fingerprints[section_id],
                "inputs": records[section_id],
                "auto": render_auto_section(section_id, discovered[section_id]),
                "manual": "" if identity_changed else previous.get("manual", ""),
            }
        else:
            sections[section_id] = previous

    baseline = {
        "schema_version": SCHEMA_VERSION,
        "repo_id": repo_id,
        "repo_root": str(root),
        "target_app": relative(target, root) or ".",
        "generated_at": utc_now(),
        "sections": sections,
        "readiness": readiness,
    }
    baseline_path.write_text(render_baseline(baseline), encoding="utf-8")
    report_path = baseline_dir / "onboarding-report.md"
    if not report_path.exists():
        stored_fingerprints = {
            section_id: sections[section_id]["fingerprint"] for section_id in SECTION_TITLES
        }
        report_path.write_text(
            default_report(repo_id, root, baseline["target_app"], stored_fingerprints),
            encoding="utf-8",
        )

    print("# Baseline Scan")
    print()
    print("| 字段 | 值 |")
    print("| --- | --- |")
    print(f"| repo_id | `{repo_id}` |")
    print(f"| target_app | `{baseline['target_app']}` |")
    print(f"| readiness | `{readiness['status']}` |")
    print(f"| refreshed_sections | `{'、'.join(sorted(requested_sections))}` |")
    remaining = sorted(set(changed) - requested_sections)
    if remaining:
        print(f"| stale_sections | `{'、'.join(remaining)}` |")
    if migrated_legacy:
        print()
        print("## 迁移提醒")
        print()
        print("- 已把旧 baseline 人工事实迁入 Markdown；确认内容后移除 `manifest.json` 与 `repo-baseline.json`。")
    return 0


def structural_errors(baseline: dict[str, Any], baseline_dir: Path) -> list[str]:
    errors: list[str] = []
    if baseline.get("schema_version") != SCHEMA_VERSION:
        errors.append("repo-baseline.md schema_version mismatch")
    if not baseline.get("repo_id"):
        errors.append("repo_id missing")
    if not baseline.get("repo_root"):
        errors.append("repo_root missing")
    if not baseline.get("target_app"):
        errors.append("target_app missing")
    for section in SECTION_TITLES:
        baseline_section = (baseline.get("sections") or {}).get(section)
        if not isinstance(baseline_section, dict):
            errors.append(f"{section} missing from baseline")
            continue
        if not baseline_section.get("fingerprint"):
            errors.append(f"{section} fingerprint missing")
        records = baseline_section.get("inputs") or []
        if baseline_section.get("input_count") != len(records):
            errors.append(f"{section} input count differs from freshness ledger")
        if fingerprint(records) != baseline_section.get("fingerprint"):
            errors.append(f"{section} fingerprint differs from freshness ledger")
    pattern_ids = re.findall(r"^####\s+`(PATTERN-[A-Z0-9-]+)`", baseline.get("text", ""), flags=re.M)
    duplicates = sorted({item for item in pattern_ids if pattern_ids.count(item) > 1})
    if duplicates:
        errors.append("duplicate REPO-3 pattern IDs: " + ", ".join(duplicates))
    legacy = [name for name in LEGACY_FILES if (baseline_dir / name).exists()]
    if legacy:
        errors.append("legacy baseline JSON remains: " + ", ".join(legacy))
    return errors


def current_status(root: Path, baseline_dir: Path) -> tuple[dict[str, Any], int]:
    baseline_path = baseline_dir / "repo-baseline.md"
    if not baseline_path.exists():
        result = {
            "usable": False,
            "readiness": "MISSING",
            "stale_sections": list(SECTION_TITLES),
            "errors": ["repo-baseline.md missing"],
        }
        return result, 3

    baseline = parse_baseline_markdown(baseline_path.read_text(encoding="utf-8"))
    errors = structural_errors(baseline, baseline_dir)
    recorded_root = baseline.get("repo_root")
    if not recorded_root or Path(str(recorded_root)).resolve() != root:
        errors.append(f"repo_root mismatch: expected {root}, got {baseline.get('repo_root')}")

    stale: list[str] = []
    if not errors:
        files = walk_files(root)
        target = root / str(baseline.get("target_app") or ".")
        classified = classify_inputs(files, root, target)
        for section in SECTION_TITLES:
            for path in declared_evidence_paths_markdown(
                baseline["sections"][section].get("manual", ""), root
            ):
                if path not in classified[section]:
                    classified[section].append(path)
            current_records = input_records(classified[section], root)
            current_fingerprint = fingerprint(current_records)
            recorded = baseline["sections"][section].get("fingerprint")
            if current_fingerprint != recorded:
                stale.append(section)

    readiness = (baseline.get("readiness") or {}).get("status", "DRAFT")
    usable = not errors and not stale and readiness in {"READY", "READY_WITH_LIMITS"}
    report = ""
    report_path = baseline_dir / "onboarding-report.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
    result = {
        "usable": usable,
        "readiness": readiness,
        "limits": markdown_list_section(report, "限制"),
        "blockers": markdown_list_section(report, "阻断"),
        "stale_sections": stale,
        "errors": errors,
        "repo_id": baseline.get("repo_id"),
        "target_app": baseline.get("target_app"),
        "baseline_dir": str(baseline_dir),
    }
    return result, 0 if usable else 3


def markdown_list_section(text: str, heading: str) -> list[str]:
    block = heading_block(text, heading, 2)
    return [
        match.group(1).strip()
        for line in block.splitlines()
        if (match := re.match(r"^\s*-\s+(.+?)\s*$", line))
    ]


def render_command_result(title: str, result: dict[str, Any]) -> str:
    rows = [
        ["usable", "是" if result.get("usable") else "否"],
        ["readiness", md_code(result.get("readiness", "MISSING"))],
    ]
    for field in ("repo_id", "target_app", "baseline_dir"):
        if result.get(field):
            rows.append([field, md_code(result[field])])
    lines = [f"# {title}", "", *render_table(["字段", "值"], rows)]
    for key, heading in (
        ("stale_sections", "失效 Section"),
        ("limits", "限制"),
        ("blockers", "阻断"),
        ("errors", "错误"),
    ):
        values = result.get(key) or []
        if values:
            lines.extend(["", f"## {heading}", ""])
            lines.extend(f"- {value}" for value in values)
    return "\n".join(lines).rstrip() + "\n"


def status(args: argparse.Namespace) -> int:
    result, exit_code = current_status(Path(args.repo_root).resolve(), Path(args.baseline_dir).resolve())
    print(render_command_result("Baseline Status", result), end="")
    return exit_code


def validate(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    baseline_dir = Path(args.baseline_dir).resolve()
    result, _ = current_status(root, baseline_dir)
    report_path = baseline_dir / "onboarding-report.md"
    if not report_path.exists():
        result["errors"].append("onboarding-report.md missing")
    else:
        baseline = parse_baseline_markdown(
            (baseline_dir / "repo-baseline.md").read_text(encoding="utf-8")
        )
        expected = (baseline.get("readiness") or {}).get("report_sha256")
        if expected and sha256_file(report_path) != expected:
            result["errors"].append("onboarding report changed after finalize")
    result["valid"] = not result["errors"] and not result["stale_sections"]
    rendered = render_command_result("Baseline Validation", result).rstrip()
    rendered += f"\n\n## 结论\n\n- valid：{'是' if result['valid'] else '否'}\n"
    print(rendered)
    return 0 if result["valid"] else 3


def replace_optional_report_section(report: str, heading: str, values: list[str]) -> str:
    pattern = rf"\n## {re.escape(heading)}[ \t]*\n.*?(?=\n## |\Z)"
    report = re.sub(pattern, "", report, count=1, flags=re.S)
    if not values:
        return report.rstrip() + "\n"

    content = "\n".join(f"- {value}" for value in values)
    section = f"\n\n## {heading}\n\n{content}\n"
    handoff = "\n## 进程交接"
    if handoff in report:
        return report.replace(handoff, section + handoff, 1)
    return report.rstrip() + section


def prune_empty_optional_report_sections(report: str) -> str:
    for heading in ("进程交接",):
        pattern = rf"\n## {re.escape(heading)}[ \t]*\n[ \t\r\n]*(?:无[。.]?)?[ \t\r\n]*(?=\n## |\Z)"
        report = re.sub(pattern, "", report, count=1, flags=re.S)
    return report.rstrip() + "\n"


def replace_report_status(report: str, state: str, limits: list[str], blockers: list[str]) -> str:
    report = re.sub(r"(\|\s*状态\s*\|\s*)`?[^|`]+`?(\s*\|)", rf"\1`{state}`\2", report, count=1)
    report = replace_optional_report_section(report, "限制", limits)
    report = replace_optional_report_section(report, "阻断", blockers)
    return prune_empty_optional_report_sections(report)


def finalize(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    baseline_dir = Path(args.baseline_dir).resolve()
    result, _ = current_status(root, baseline_dir)
    if result["errors"] or result["stale_sections"]:
        raise BaselineError(
            "cannot finalize stale or invalid baseline: "
            + "; ".join(result["errors"] + result["stale_sections"])
        )

    state = args.status
    limits = args.limit or []
    blockers = args.blocker or []
    if state == "READY" and (limits or blockers):
        raise BaselineError("READY cannot have limits or blockers")
    if state == "READY_WITH_LIMITS" and (not limits or blockers):
        raise BaselineError("READY_WITH_LIMITS requires at least one limit and no blockers")
    if state == "BLOCKED" and not blockers:
        raise BaselineError("BLOCKED requires at least one blocker")

    report_path = baseline_dir / "onboarding-report.md"
    if not report_path.exists():
        raise BaselineError("onboarding-report.md missing")
    report = report_path.read_text(encoding="utf-8")
    if state in {"READY", "READY_WITH_LIMITS"} and (
        "待执行" in report or "<!-- ONBOARDING_DRAFT -->" in report
    ):
        raise BaselineError("onboarding-report.md still contains draft placeholders")
    report = replace_report_status(report, state, limits, blockers)
    report_path.write_text(report, encoding="utf-8")

    baseline_path = baseline_dir / "repo-baseline.md"
    baseline = parse_baseline_markdown(baseline_path.read_text(encoding="utf-8"))
    readiness = {
        "status": state,
        "verified_at": utc_now(),
        "report_sha256": sha256_file(report_path),
        "reason": None,
    }
    baseline["readiness"] = readiness
    baseline["generated_at"] = utc_now()
    baseline_path.write_text(render_baseline(baseline), encoding="utf-8")
    print("# Baseline Finalize")
    print()
    print("| 字段 | 值 |")
    print("| --- | --- |")
    print(f"| status | `{state}` |")
    print(f"| baseline_dir | `{baseline_dir}` |")
    return 0


def pattern_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^####\s+`(PATTERN-[A-Z0-9-]+)`.*$", text, flags=re.M))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1), text[match.start() : end].strip()))
    return blocks


def show(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline_dir).resolve() / "repo-baseline.md"
    if not baseline_path.exists():
        raise BaselineError("repo-baseline.md missing")
    text = baseline_path.read_text(encoding="utf-8")
    baseline = parse_baseline_markdown(text)
    if not args.section and not args.pattern_id and not args.tag:
        print(text, end="")
        return 0

    selected: list[str] = []
    for section_id in args.section or []:
        block = heading_block(
            text,
            f"{section_id} {SECTION_TITLES[section_id]}",
            2,
            include_heading=True,
        )
        if block:
            selected.append(block)

    patterns = pattern_blocks(baseline["sections"]["REPO-3"].get("manual", ""))
    requested_ids = set(args.pattern_id or [])
    requested_tags = set(args.tag or [])
    found_ids: set[str] = set()
    for pattern_id, block in patterns:
        id_match = pattern_id in requested_ids
        tag_match = any(tag in block for tag in requested_tags)
        if id_match or tag_match:
            selected.append(block)
            found_ids.add(pattern_id)
    missing = sorted(requested_ids - found_ids)
    if missing:
        raise BaselineError("pattern IDs not found: " + ", ".join(missing))

    print("# Baseline Selection")
    print()
    print(f"- 仓库：`{baseline['repo_id']}`")
    print(f"- REPO-3 指纹：`{baseline['sections']['REPO-3']['fingerprint']}`")
    if selected:
        print()
        print("\n\n".join(dict.fromkeys(selected)))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="discover or refresh repository facts")
    scan_parser.add_argument("--repo-root", required=True)
    scan_parser.add_argument("--target-app")
    scan_parser.add_argument("--baseline-dir", required=True)
    scan_parser.add_argument("--repo-id")
    scan_parser.add_argument(
        "--section",
        action="append",
        choices=sorted(SECTION_TITLES),
        help="refresh only the named section; repeat for multiple sections",
    )
    scan_parser.set_defaults(func=scan)

    for name, func in (("status", status), ("validate", validate)):
        command = subparsers.add_parser(name)
        command.add_argument("--repo-root", required=True)
        command.add_argument("--baseline-dir", required=True)
        command.set_defaults(func=func)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--repo-root", required=True)
    finalize_parser.add_argument("--baseline-dir", required=True)
    finalize_parser.add_argument("--status", choices=sorted(READY_STATES), required=True)
    finalize_parser.add_argument("--limit", action="append")
    finalize_parser.add_argument("--blocker", action="append")
    finalize_parser.set_defaults(func=finalize)

    show_parser = subparsers.add_parser("show", help="show Markdown baseline sections or patterns")
    show_parser.add_argument("--baseline-dir", required=True)
    show_parser.add_argument("--section", action="append", choices=sorted(SECTION_TITLES))
    show_parser.add_argument("--pattern-id", action="append")
    show_parser.add_argument("--tag", action="append")
    show_parser.set_defaults(func=show)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except AmbiguousTarget as exc:
        print("# Baseline Error\n", file=sys.stderr)
        print("- multiple target apps found", file=sys.stderr)
        for candidate in exc.candidates:
            print(f"- `{candidate}`", file=sys.stderr)
        return 2
    except BaselineError as exc:
        print(f"# Baseline Error\n\n- {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
