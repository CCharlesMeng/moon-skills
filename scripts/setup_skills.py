#!/usr/bin/env python3
"""Install moon-skills bundles into a host skills directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "skills-manifest.json"
IGNORE_PATTERNS = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
GLOBAL_TARGETS = {
    "agents": Path("~/.agents/skills").expanduser(),
    "cursor": Path("~/.cursor/skills").expanduser(),
    "claude": Path("~/.claude/skills").expanduser(),
}
LOCAL_HOST_MARKERS = {
    ".agents": "agents",
    ".cursor": "cursor",
    ".claude": "claude",
}


@dataclass(frozen=True)
class SkillSpec:
    name: str
    source: Path
    category: str
    dependencies: tuple[str, ...]


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_bundle_skills(manifest: dict, bundle_names: list[str]) -> list[str]:
    skills = manifest["skills"]
    bundles = manifest["bundles"]
    ordered: list[str] = []
    seen: set[str] = set()

    def add_skill(skill_id: str) -> None:
        if skill_id in seen:
            return
        for dependency in skills[skill_id].get("dependencies", []):
            add_skill(dependency)
        seen.add(skill_id)
        ordered.append(skill_id)

    for bundle_name in bundle_names:
        if bundle_name not in bundles:
            raise KeyError(f"Unknown bundle: {bundle_name}")
        for root_skill in bundles[bundle_name]["roots"]:
            add_skill(root_skill)

    return ordered


def infer_repo_local_host(repo_root: Path) -> str | None:
    parent = repo_root.parent
    grandparent = parent.parent
    if parent.name != "skills":
        return None
    return LOCAL_HOST_MARKERS.get(grandparent.name)


def resolve_target_root(repo_root: Path, host: str, target_dir: str | None) -> Path:
    if target_dir:
        return Path(target_dir).expanduser()

    inferred_host = infer_repo_local_host(repo_root)
    if inferred_host:
        return repo_root.parent

    if host == "auto":
        host = "agents"

    return GLOBAL_TARGETS[host]


def backup_path(target: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.name}.backup-{stamp}")


def copy_skill_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=IGNORE_PATTERNS)


def symlink_skill_tree(source: Path, target: Path) -> None:
    target.symlink_to(source, target_is_directory=True)


def remove_target(target: Path) -> None:
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    shutil.rmtree(target)


def backup_existing_target(target: Path, backup: bool) -> None:
    if not backup or not (target.exists() or target.is_symlink()):
        return
    backup_target = backup_path(target)
    if target.is_symlink():
        source = target.resolve()
        if source.is_dir():
            copy_skill_tree(source, backup_target)
        else:
            backup_target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    elif target.is_dir():
        copy_skill_tree(target, backup_target)
    else:
        backup_target.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"backup: {backup_target}")


def build_skill_specs(manifest: dict, repo_root: Path) -> dict[str, SkillSpec]:
    specs: dict[str, SkillSpec] = {}
    for skill_id, data in manifest["skills"].items():
        specs[skill_id] = SkillSpec(
            name=skill_id,
            source=(repo_root / data["source"]).resolve(),
            category=data["category"],
            dependencies=tuple(data.get("dependencies", [])),
        )
    return specs


def install_skill(
    skill: SkillSpec,
    target_root: Path,
    *,
    write: bool,
    force: bool,
    backup: bool,
    mode: str,
) -> None:
    if not skill.source.exists():
        raise FileNotFoundError(f"Missing source for {skill.name}: {skill.source}")

    target = target_root / skill.name

    if target.exists() and not force:
        print(f"skip: {skill.name} already exists at {target} (use --force to overwrite)")
        return

    if not write:
        action = "overwrite" if target.exists() else "install"
        print(f"dry-run: would {action} {skill.name} ({skill.category}) to {target}")
        return

    target_root.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        backup_existing_target(target, backup)
        remove_target(target)

    try:
        if mode == "symlink":
            symlink_skill_tree(skill.source, target)
        else:
            copy_skill_tree(skill.source, target)
    except OSError:
        if mode != "symlink":
            raise
        copy_skill_tree(skill.source, target)
        print(f"written: {skill.name} -> {target} (fallback: copy)")
        return

    print(f"written: {skill.name} -> {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        choices=["auto", "agents", "cursor", "claude"],
        default="auto",
        help="Which host runtime to target when --target-dir is omitted.",
    )
    parser.add_argument(
        "--target-dir",
        help="Explicit skills root to install into. Overrides --host detection.",
    )
    parser.add_argument(
        "--bundle",
        action="append",
        default=[],
        help="Bundle to install. Repeatable. Defaults to workflow.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install every bundle declared in skills-manifest.json.",
    )
    parser.add_argument(
        "--mode",
        choices=["symlink", "copy"],
        default="symlink",
        help="Install as symlinks or copied directories.",
    )
    parser.add_argument("--write", action="store_true", help="Apply changes instead of dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed skills.")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a directory backup before overwriting an existing skill.",
    )
    parser.add_argument("--list", action="store_true", help="List bundles and skills, then exit.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the installation manifest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).expanduser().resolve()
    repo_root = manifest_path.parent
    manifest = load_manifest(manifest_path)

    if args.all:
        bundle_names = list(manifest["bundles"].keys())
    else:
        bundle_names = args.bundle or ["workflow"]

    skill_specs = build_skill_specs(manifest, repo_root)
    skill_ids = resolve_bundle_skills(manifest, bundle_names)
    target_root = resolve_target_root(repo_root, args.host, args.target_dir)

    if args.list:
        print("bundles:")
        for bundle_name, bundle in manifest["bundles"].items():
            print(f"- {bundle_name}: {', '.join(bundle['roots'])}")
        print()
        print("skills:")
        for skill_id in skill_ids:
            spec = skill_specs[skill_id]
            rel_source = spec.source.relative_to(repo_root)
            print(f"- {skill_id}\t{spec.category}\t{rel_source}")
        return 0

    print(f"target: {target_root}")
    print(f"mode: {args.mode}")
    print("bundles:")
    for bundle_name in bundle_names:
        print(f"- {bundle_name}")
    print("skills:")
    for skill_id in skill_ids:
        spec = skill_specs[skill_id]
        print(f"- {skill_id} ({spec.category})")

    print()
    for skill_id in skill_ids:
        install_skill(
            skill_specs[skill_id],
            target_root,
            write=args.write,
            force=args.force,
            backup=args.backup,
            mode=args.mode,
        )

    if not args.write:
        print()
        print("Install finished in dry-run mode.")
        print("Re-run with --write to materialize the selected bundles.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
