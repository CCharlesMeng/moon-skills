#!/usr/bin/env python3
"""Install moon-skills bundles into a host skills directory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
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
    source: Path | None
    category: str
    dependencies: tuple[str, ...]
    official_package: str | None = None
    official_skill: str | None = None
    vendor_fallback: Path | None = None


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_skills_subdir_ids(repo_root: Path) -> list[str]:
    """Directories under skills/ that contain SKILL.md, sorted by name."""
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(
        p.name
        for p in skills_dir.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    )


def hydrate_workflow_bundle_from_skills_dir(manifest: dict, repo_root: Path) -> None:
    """Ensure workflow bundle installs every first-party skill under skills/ (see SKILL.md)."""
    discovered = discover_skills_subdir_ids(repo_root)
    if not discovered:
        return

    skills = manifest["skills"]
    for name in discovered:
        if name not in skills:
            skills[name] = {
                "source": f"skills/{name}",
                "category": "workflow",
                "dependencies": [],
            }

    wf = manifest["bundles"].get("workflow")
    if wf is None:
        return

    old_roots = list(wf["roots"])
    extra = [r for r in old_roots if r not in discovered]
    wf["roots"] = list(discovered) + extra


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
        source = data.get("source")
        vendor_fallback = data.get("vendorFallback") or source
        specs[skill_id] = SkillSpec(
            name=skill_id,
            source=(repo_root / source).resolve() if source else None,
            category=data["category"],
            dependencies=tuple(data.get("dependencies", [])),
            official_package=data.get("officialPackage"),
            official_skill=data.get("officialSkill"),
            vendor_fallback=(repo_root / vendor_fallback).resolve() if vendor_fallback else None,
        )
    return specs


def materialize_skill(
    name: str,
    source: Path,
    category: str,
    target_root: Path,
    *,
    write: bool,
    force: bool,
    backup: bool,
    mode: str,
) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing source for {name}: {source}")

    target = target_root / name

    if target.exists() and not force:
        print(f"skip: {name} already exists at {target} (use --force to overwrite)")
        return

    if not write:
        action = "overwrite" if target.exists() else "install"
        print(f"dry-run: would {action} {name} ({category}) to {target}")
        return

    target_root.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        backup_existing_target(target, backup)
        remove_target(target)

    try:
        if mode == "symlink":
            symlink_skill_tree(source, target)
        else:
            copy_skill_tree(source, target)
    except OSError:
        if mode != "symlink":
            raise
        copy_skill_tree(source, target)
        print(f"written: {name} -> {target} (fallback: copy)")
        return

    print(f"written: {name} -> {target}")


def build_search_roots(target_root: Path) -> list[Path]:
    roots = [target_root]
    for candidate in GLOBAL_TARGETS.values():
        if candidate != target_root:
            roots.append(candidate)
    return roots


def locate_skill_directory(skill_name: str, roots: list[Path]) -> Path | None:
    for root in roots:
        direct = root / skill_name
        if (direct / "SKILL.md").exists():
            return direct
    return None


def locate_skill_in_tree(root: Path, skill_name: str) -> Path | None:
    if not root.exists():
        return None
    direct = root / skill_name
    if (direct / "SKILL.md").exists():
        return direct
    for skill_file in root.rglob("SKILL.md"):
        if skill_file.parent.name == skill_name:
            return skill_file.parent
    return None


def stage_official_superpowers_install(
    package: str,
    *,
    requested_skills: list[str],
) -> Path:
    if shutil.which("npx") is None:
        raise RuntimeError("npx is required for official superpowers installation")

    temp_workspace = Path(tempfile.mkdtemp(prefix="moon-skills-superpowers-"))
    command = ["npx", "skills", "add", package]
    if len(requested_skills) == 1:
        command.extend(["--skill", requested_skills[0]])

    subprocess.run(
        command,
        cwd=temp_workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    return temp_workspace / ".agents" / "skills"


def resolve_superpowers_source(skill: SkillSpec) -> Path:
    if skill.vendor_fallback is None:
        raise FileNotFoundError(f"Missing vendor fallback for {skill.name}")
    return skill.vendor_fallback


def install_superpowers_skills(
    skill_ids: list[str],
    skill_specs: dict[str, SkillSpec],
    target_root: Path,
    *,
    write: bool,
    force: bool,
    backup: bool,
    mode: str,
    prefer_official: bool,
    superpowers_source: str,
    allow_vendor_fallback: bool,
) -> None:
    search_roots = build_search_roots(target_root)
    missing_for_official: list[str] = []

    for skill_id in skill_ids:
        skill = skill_specs[skill_id]
        target = target_root / skill_id
        if target.exists() and not force:
            print(f"skip: {skill_id} already exists at {target} (use --force to overwrite)")
            continue

        if prefer_official:
            existing = locate_skill_directory(skill_id, search_roots)
            if existing is not None and existing.parent != target_root:
                materialize_skill(
                    skill.name,
                    existing,
                    "official-installed",
                    target_root,
                    write=write,
                    force=force,
                    backup=backup,
                    mode=mode,
                )
                continue
            missing_for_official.append(skill_id)
            if not write:
                print(
                    f"dry-run: would install {skill_id} via official superpowers source "
                    f"({superpowers_source}) into {target}"
                )
            continue

        materialize_skill(
            skill.name,
            resolve_superpowers_source(skill),
            "vendor-fallback",
            target_root,
            write=write,
            force=force,
            backup=backup,
            mode=mode,
        )

    if not prefer_official or not missing_for_official or not write:
        return

    staged_root: Path | None = None
    official_error: Exception | None = None
    try:
        staged_root = stage_official_superpowers_install(
            superpowers_source,
            requested_skills=missing_for_official,
        )
    except Exception as exc:  # noqa: BLE001
        official_error = exc

    unresolved: list[str] = []
    if staged_root is not None:
        for skill_id in missing_for_official:
            staged_skill = locate_skill_in_tree(staged_root, skill_id)
            if staged_skill is None:
                unresolved.append(skill_id)
                continue
            materialize_skill(
                skill_id,
                staged_skill,
                "official-remote",
                target_root,
                write=write,
                force=force,
                backup=backup,
                mode=mode,
            )
    else:
        unresolved = missing_for_official[:]

    if not unresolved:
        return

    if not allow_vendor_fallback:
        reason = str(official_error) if official_error is not None else "missing staged official skills"
        raise RuntimeError(
            f"Official superpowers install did not provide required skills: {', '.join(unresolved)} ({reason})"
        )

    if official_error is not None:
        print(f"warn: official superpowers install failed ({official_error}); using vendor fallback")
    else:
        print(f"warn: official superpowers install missing {', '.join(unresolved)}; using vendor fallback")

    for skill_id in unresolved:
        skill = skill_specs[skill_id]
        materialize_skill(
            skill.name,
            resolve_superpowers_source(skill),
            "vendor-fallback",
            target_root,
            write=write,
            force=force,
            backup=backup,
            mode=mode,
        )


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
        "--superpowers-source",
        default="obra/superpowers",
        help="Official superpowers package/repository source used by `npx skills add`.",
    )
    parser.add_argument(
        "--prefer-official",
        dest="prefer_official",
        action="store_true",
        help="Prefer existing or official-installed superpowers skills before vendor fallback.",
    )
    parser.add_argument(
        "--no-official",
        dest="prefer_official",
        action="store_false",
        help="Disable official superpowers resolution and use vendor fallback directly.",
    )
    parser.add_argument(
        "--allow-vendor-fallback",
        dest="allow_vendor_fallback",
        action="store_true",
        help="Allow vendored superpowers skills when official install is unavailable.",
    )
    parser.add_argument(
        "--no-vendor-fallback",
        dest="allow_vendor_fallback",
        action="store_false",
        help="Fail instead of falling back to vendored superpowers skills.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the installation manifest.",
    )
    parser.set_defaults(prefer_official=True, allow_vendor_fallback=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest).expanduser().resolve()
    repo_root = manifest_path.parent
    manifest = load_manifest(manifest_path)
    hydrate_workflow_bundle_from_skills_dir(manifest, repo_root)

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
        if spec.official_package:
            print(f"- {skill_id} ({spec.category}, official={spec.official_package})")
        else:
            print(f"- {skill_id} ({spec.category})")

    print()
    official_skill_ids = [
        skill_id for skill_id in skill_ids if skill_specs[skill_id].official_package is not None
    ]
    regular_skill_ids = [skill_id for skill_id in skill_ids if skill_id not in official_skill_ids]

    for skill_id in regular_skill_ids:
        skill = skill_specs[skill_id]
        if skill.source is None:
            raise FileNotFoundError(f"Missing source for {skill.name}")
        materialize_skill(
            skill.name,
            skill.source,
            skill.category,
            target_root,
            write=args.write,
            force=args.force,
            backup=args.backup,
            mode=args.mode,
        )

    install_superpowers_skills(
        official_skill_ids,
        skill_specs,
        target_root,
        write=args.write,
        force=args.force,
        backup=args.backup,
        mode=args.mode,
        prefer_official=args.prefer_official,
        superpowers_source=args.superpowers_source,
        allow_vendor_fallback=args.allow_vendor_fallback,
    )

    if not args.write:
        print()
        print("Install finished in dry-run mode.")
        print("Re-run with --write to materialize the selected bundles.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
