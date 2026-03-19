#!/usr/bin/env python3
"""Detect context impact and verify whether project context was synced."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from context_common import (
    changed_files,
    classify_impact,
    load_impact_rules,
    optional_assets_for_impact,
    repo_root,
    required_assets_for_impact,
)


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NEEDS_SYNC = 2


def print_detect_output(impact: str, reasons: list[str], fmt: str) -> int:
    required_assets = ",".join(required_assets_for_impact(impact))
    if fmt == "json":
        print(
            json.dumps(
                {
                    "impact": impact,
                    "required_assets": required_assets_for_impact(impact),
                    "reasons": reasons,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return EXIT_OK
    if fmt == "github-output":
        print(f"impact={impact}")
        print(f"required_assets={required_assets}")
        print("reasons<<EOF")
        for reason in reasons:
            print(reason)
        print("EOF")
        return EXIT_OK

    print(f"impact: {impact}")
    if required_assets:
        print(f"required assets: {required_assets}")
    if reasons:
        print("reasons:")
        for reason in reasons:
            print(f"- {reason}")
    return EXIT_OK


def command_detect_impact(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo_root)
    rules = load_impact_rules(repo / args.rules)
    files = changed_files(repo, args.base, args.head)
    impact, reasons = classify_impact(files, rules)
    return print_detect_output(impact, reasons, args.format)


def command_sync(args: argparse.Namespace) -> int:
    if not args.check:
        raise SystemExit("当前版本只支持 `sync --check`。真正的同步更新仍由 `sync-context` skill 或 AI 交互式执行。")

    repo = repo_root(args.repo_root)
    rules = load_impact_rules(repo / args.rules)
    files = changed_files(repo, args.base, args.head)
    impact = args.impact
    reasons: list[str] = []
    if impact is None:
        impact, reasons = classify_impact(files, rules)

    if impact == "none":
        print("No context impact detected.")
        return EXIT_OK

    profile_path = repo / ".project-context/profile.yaml"
    if not profile_path.exists():
        print("`.project-context/profile.yaml` 不存在，请先运行 `initialize`。")
        return EXIT_NEEDS_SYNC

    changed_set = set(files)
    required_assets = required_assets_for_impact(impact)
    optional_assets = optional_assets_for_impact(impact)
    missing_required = [asset for asset in required_assets if asset not in changed_set]

    if missing_required:
        print("本次改动命中了 context 影响，但相关 context 资产尚未同步。")
        print(f"impact: {impact}")
        if reasons:
            print("reasons:")
            for reason in reasons:
                print(f"- {reason}")
        print("missing required assets:")
        for asset in missing_required:
            print(f"- {asset}")
        if optional_assets:
            print("recommended optional assets:")
            for asset in optional_assets:
                print(f"- {asset}")
        print("建议在 Cursor 中运行 `sync-context`，完成上下文同步后重新推送。")
        return EXIT_NEEDS_SYNC

    print("Context assets look synchronized for this impact level.")
    if optional_assets:
        print("optional assets to review:")
        for asset in optional_assets:
            if asset not in changed_set:
                print(f"- {asset}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect-impact", help="Classify context impact for a git diff")
    detect_parser.add_argument("--base", required=True)
    detect_parser.add_argument("--head", required=True)
    detect_parser.add_argument("--rules", default=".project-context/impact-rules.yaml")
    detect_parser.add_argument("--format", choices=["text", "json", "github-output"], default="text")

    sync_parser = subparsers.add_parser("sync", help="Check whether context assets were updated for a git diff")
    sync_parser.add_argument("--base", required=True)
    sync_parser.add_argument("--head", required=True)
    sync_parser.add_argument("--rules", default=".project-context/impact-rules.yaml")
    sync_parser.add_argument("--impact", choices=["none", "feature", "reference", "structure"])
    sync_parser.add_argument("--check", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "detect-impact":
        return command_detect_impact(args)
    if args.command == "sync":
        return command_sync(args)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
