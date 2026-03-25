#!/usr/bin/env python3
"""Install the workflow skill suite and its vendored dependencies."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORE_PATTERNS = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
DEFAULT_TARGETS = {
    "agents": Path("~/.agents/skills").expanduser(),
    "cursor": Path("~/.cursor/skills").expanduser(),
    "claude": Path("~/.claude/skills").expanduser(),
}


@dataclass(frozen=True)
class SkillInstall:
    name: str
    source: Path
    category: str


WORKFLOW_SKILLS = (
    SkillInstall("initialize", REPO_ROOT / "skills/initialize", "workflow"),
    SkillInstall("sync-context", REPO_ROOT / "skills/sync-context", "workflow"),
    SkillInstall("immune-debug", REPO_ROOT / "skills/immune-debug", "workflow"),
    SkillInstall("audit", REPO_ROOT / "skills/audit", "workflow"),
    SkillInstall("brainstorming", REPO_ROOT / "vendor/superpowers/brainstorming", "vendored"),
    SkillInstall(
        "systematic-debugging",
        REPO_ROOT / "vendor/superpowers/systematic-debugging",
        "vendored",
    ),
)


def backup_path(target: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.name}.backup-{stamp}")


def resolve_target_dir(target_dir: str | None, profile: str) -> Path:
    if target_dir:
        return Path(target_dir).expanduser()
    return DEFAULT_TARGETS[profile]


def copy_skill_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=IGNORE_PATTERNS)


def install_skill(
    skill: SkillInstall,
    target_root: Path,
    *,
    write: bool,
    force: bool,
    backup: bool,
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

    if target.exists():
        if backup:
            backup_target = backup_path(target)
            copy_skill_tree(target, backup_target)
            print(f"backup: {backup_target}")
        shutil.rmtree(target)

    copy_skill_tree(skill.source, target)
    print(f"written: {skill.name} -> {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dir",
        help="Install into a custom skill directory. Overrides --profile.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(DEFAULT_TARGETS),
        default="agents",
        help="Default target profile when --target-dir is omitted.",
    )
    parser.add_argument("--write", action="store_true", help="Apply changes instead of dry-run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed skills.")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a directory backup before overwriting an existing skill.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the bundled skills and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        for skill in WORKFLOW_SKILLS:
            print(f"{skill.name}\t{skill.category}\t{skill.source.relative_to(REPO_ROOT)}")
        return 0

    target_root = resolve_target_dir(args.target_dir, args.profile)

    print(f"target: {target_root}")
    print("bundle:")
    for skill in WORKFLOW_SKILLS:
        print(f"- {skill.name} ({skill.category})")

    print()
    for skill in WORKFLOW_SKILLS:
        install_skill(
            skill,
            target_root,
            write=args.write,
            force=args.force,
            backup=args.backup,
        )

    if not args.write:
        print()
        print("Install finished in dry-run mode.")
        print("Re-run with --write to install the workflow skill bundle.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
