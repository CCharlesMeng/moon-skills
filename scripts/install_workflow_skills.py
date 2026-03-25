#!/usr/bin/env python3
"""Backward-compatible wrapper around the new bundle setup engine."""

from __future__ import annotations

import argparse

import setup_skills


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dir",
        help="Install into a custom skill directory. Overrides --profile.",
    )
    parser.add_argument(
        "--profile",
        choices=["agents", "cursor", "claude"],
        default="agents",
        help="Default target profile when --target-dir is omitted.",
    )
    parser.add_argument(
        "--mode",
        choices=["symlink", "copy"],
        default="copy",
        help="Legacy installer defaults to copying directories.",
    )
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
    parser.set_defaults(prefer_official=True, allow_vendor_fallback=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    forwarded_args = [
        "--bundle",
        "workflow",
        "--host",
        args.profile,
        "--mode",
        args.mode,
        "--superpowers-source",
        args.superpowers_source,
    ]
    if args.target_dir:
        forwarded_args.extend(["--target-dir", args.target_dir])
    if args.write:
        forwarded_args.append("--write")
    if args.force:
        forwarded_args.append("--force")
    if args.backup:
        forwarded_args.append("--backup")
    if args.list:
        forwarded_args.append("--list")
    if not args.prefer_official:
        forwarded_args.append("--no-official")
    if not args.allow_vendor_fallback:
        forwarded_args.append("--no-vendor-fallback")

    return setup_skills.main(forwarded_args)


if __name__ == "__main__":
    raise SystemExit(main())
