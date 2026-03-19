#!/usr/bin/env python3
"""Install GitHub context-check files into a target repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from context_common import backup_file, ensure_parent, repo_root


FILES_TO_INSTALL = {
    "workflow": (Path("../templates/context-check.yml"), Path(".github/workflows/context-check.yml")),
    "rules": (Path("../templates/impact-rules.yaml"), Path(".project-context/impact-rules.yaml")),
    "runtime": (Path("manage_context.py"), Path(".project-context/scripts/manage_context.py")),
    "runtime-common": (Path("context_common.py"), Path(".project-context/scripts/context_common.py")),
}


def install_file(source: Path, target: Path, write: bool, force: bool, backup: bool) -> None:
    if target.exists() and not force:
        print(f"skip: {target} already exists (use --force to overwrite)")
        return

    if not write:
        action = "overwrite" if target.exists() else "create"
        print(f"dry-run: would {action} {target}")
        return

    ensure_parent(target)
    if target.exists() and backup:
        backup_path = backup_file(target)
        print(f"backup: {backup_path}")
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"written: {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args(argv)

    repo = repo_root(args.repo_root)
    script_dir = Path(__file__).resolve().parent

    for _, (source_rel, target_rel) in FILES_TO_INSTALL.items():
        source = (script_dir / source_rel).resolve()
        target = repo / target_rel
        install_file(source, target, args.write, args.force, args.backup)

    if not args.write:
        print()
        print("Install finished in dry-run mode.")
        print("Re-run with --write to install GitHub context-check into the target repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
