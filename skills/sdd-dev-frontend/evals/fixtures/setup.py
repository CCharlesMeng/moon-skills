#!/usr/bin/env python3
"""把冻结的 fixture 源料展开成一个可跑的现场。

现场里的东西全部是派生物，不进仓：目标业务仓、Story 产物、design-spec 都由本脚本
从仓内源料确定性重建。源料只有四样：`repo/`、`baseline/`（冻结的八份仓库 baseline，
原样拷贝）、`sdd-review-frontend/evals/cases/<case>/`，以及 `evals/` 下的两份原型 HTML。

    python3 setup.py --case convention-01
    python3 setup.py --case convention-01 --work-dir /tmp/fx --with-design-spec

跑完会打印一张「路径变量取值」表，直接贴进子代理派发消息即可。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent
EVAL_DIR = FIXTURE_DIR.parent
SKILL_DIR = EVAL_DIR.parent
REVIEW_PACK_DIR = SKILL_DIR.parent / "sdd-review-frontend"
# 用例测的是 review 包里的 checklist，所以跟 checklist 走；本脚本只负责把现场搭起来。
CASES_DIR = REVIEW_PACK_DIR / "evals" / "cases"

REPO_ID = "risk-console"
# 现场必须逐字节可复现，所以时间戳取 fixture 的冻结日期，不取当前时间。
FREEZE_DATE = "2026-08-05"
LIMIT = "依赖未安装，质量命令与浏览器采集均未实跑；本现场只支持静态判据类模块的评测"
BASELINE_FILES = (
    "index.md",
    "structure.md",
    "runtime.md",
    "components.md",
    "api.md",
    "data.md",
    "styling.md",
    "testing.md",
)
PROTOTYPES = {
    "standard": EVAL_DIR / "设计稿原型-标准版.html",
    "risk-brief": EVAL_DIR / "原型-客户风险简报.html",
}

GIT_CONFIG = [
    "-c", "user.name=fixture",
    "-c", "user.email=fixture@example.invalid",
    "-c", "commit.gpgsign=false",
]
# 固定作者与提交时间，让 base-ref 在任何机器上都落到同一个 SHA。
COMMIT_DATE = f"{FREEZE_DATE}T00:00:00+0000"


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        sys.stderr.write(f"命令失败：{' '.join(cmd)}\n{result.stdout}\n{result.stderr}\n")
        raise SystemExit(1)
    return result.stdout


def build_repo(work_dir: Path) -> tuple[Path, str]:
    repo = work_dir / "repo"
    shutil.copytree(FIXTURE_DIR / "repo", repo)
    run(["git", "init", "--quiet", "--initial-branch=main"], cwd=repo)
    run(["git", *GIT_CONFIG, "add", "-A"], cwd=repo)
    run(
        ["git", *GIT_CONFIG, "commit", "--quiet", "-m", "fixture: Story 起点"],
        cwd=repo,
        env={**os.environ, "GIT_AUTHOR_DATE": COMMIT_DATE, "GIT_COMMITTER_DATE": COMMIT_DATE},
    )
    base_ref = run(["git", "rev-parse", "HEAD"], cwd=repo).strip()
    return repo, base_ref


def build_baseline(work_dir: Path) -> Path:
    """把冻结的八份 baseline 原样拷进现场。

    这里没有扫描、没有注入、没有指纹回填：baseline 全部用仓内相对路径指路，
    不含绝对路径也不含哈希，所以源料本身就是最终产物，逐字节可复现。
    """
    baseline_dir = work_dir / "frontend-baselines" / REPO_ID
    baseline_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE_DIR / "baseline", baseline_dir)

    missing = [name for name in BASELINE_FILES if not (baseline_dir / name).is_file()]
    if missing:
        raise SystemExit(f"baseline 源料缺文件：{missing}")
    return baseline_dir


def build_story(case_dir: Path, work_dir: Path, replacements: dict[str, str]) -> Path:
    story_dir = work_dir / "story"
    shutil.copytree(case_dir / "story", story_dir)
    for path in sorted(story_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        remaining = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
        if remaining:
            raise SystemExit(f"{path} 仍有未替换的占位符：{sorted(set(remaining))}")
        path.write_text(text, encoding="utf-8")
    return story_dir


def apply_case(case_dir: Path, repo: Path) -> list[str]:
    after = case_dir / "after"
    changed: list[str] = []
    for source in sorted(after.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(after)
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        changed.append(str(relative))
    return changed


def build_review_evidence(repo: Path, story_dir: Path, base_ref: str, changed: list[str]) -> Path:
    """Build the minimal current-code evidence package required by static review fixtures."""
    files = []
    for relative in sorted(changed):
        digest = hashlib.sha256((repo / relative).read_bytes()).hexdigest()
        files.append({"path": relative, "sha256": digest})
    code = {
        "base_ref": base_ref,
        "head": base_ref,
        "files": files,
    }
    code["code_fingerprint"] = hashlib.sha256(
        json.dumps(code, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    path = story_dir / "review-evidence.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "evidence_epoch": "fixture-review-1",
        "validation_portfolio": {
            "risk_triggers": ["visual", "shared-boundary", "async-state"],
            "modules": ["review-layout", "review-convention", "review-quality"],
            "review_roles": ["review-layout", "review-convention", "review-quality"],
            "review_dimensions": {
                "review-layout": [f"L{index}" for index in range(1, 7)],
                "review-convention": [f"C{index}" for index in range(1, 8)],
                "review-quality": [f"Q{index}" for index in range(1, 9)],
            },
            "claims": [],
        },
        "code": code,
        "quality_gate": {"code_fingerprint": code["code_fingerprint"], "commands": []},
        "runtime": {"driver": "fixture-static-only", "browser": "unavailable"},
        "scenarios": [],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_design_spec(work_dir: Path) -> Path:
    out_root = work_dir / "design-spec"
    extractor = SKILL_DIR / "scripts" / "extract_design_spec.py"
    for name, prototype in PROTOTYPES.items():
        if not prototype.exists():
            raise SystemExit(f"缺少原型：{prototype}")
        run([
            sys.executable, str(extractor), "extract", str(prototype),
            "--out-dir", str(out_root / name),
        ])
    return out_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", default="convention-01")
    parser.add_argument("--work-dir", help="留空则在临时目录建，路径会打印出来")
    parser.add_argument("--with-design-spec", action="store_true", help="额外由两份原型生成 design-spec/")
    args = parser.parse_args()

    case_dir = CASES_DIR / args.case
    if not case_dir.is_dir():
        available = sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())
        raise SystemExit(f"没有这个用例：{args.case}；现有：{available}")

    work_dir = Path(args.work_dir).resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="sdd-fe-fixture-"))
    if work_dir.exists() and any(work_dir.iterdir()):
        raise SystemExit(f"现场目录非空，换一个或先清空：{work_dir}")
    work_dir.mkdir(parents=True, exist_ok=True)

    repo, base_ref = build_repo(work_dir)
    baseline_dir = build_baseline(work_dir)
    story_dir = build_story(case_dir, work_dir, {
        "BASELINE_DIR": str(baseline_dir),
        "STORY_DIR": str(work_dir / "story"),
        "BASE_REF": base_ref,
    })
    changed = apply_case(case_dir, repo)
    review_evidence = build_review_evidence(repo, story_dir, base_ref, changed)
    design_spec = build_design_spec(work_dir) if args.with_design_spec else None

    dirty = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo).strip().splitlines()
    if len(dirty) != len(changed):
        raise SystemExit(f"工作区改动数与用例文件数不符：git {len(dirty)} vs 用例 {len(changed)}")

    print(f"现场：{work_dir}\n")
    print("| 变量 | 取值 |")
    print("| --- | --- |")
    print(f"| `<repo-root>` | `{repo}` |")
    print(f"| `<repo-baseline-dir>` | `{baseline_dir}` |")
    print(f"| `<story-dir>` | `{story_dir}` |")
    print(f"| `<skill-dir>` | `{SKILL_DIR}` |")
    print(f"| `<review-pack-dir>` | `{REVIEW_PACK_DIR}` |")
    print(f"| `<base-ref>` | `{base_ref}` |")
    print(f"| `<review-evidence>` | `{review_evidence}` |")
    print("| `evidence_epoch` | `fixture-review-1` |")
    if design_spec is not None:
        print(f"| `<design-spec-dir>` | `{design_spec}/risk-brief` |")
    print(f"\n仓库 baseline：{len(BASELINE_FILES)} 份（{', '.join(BASELINE_FILES)}）")
    print(f"待检视改动（{len(changed)} 个文件）：")
    for item in dirty:
        print(f"  {item}")
    print(f"\nground truth：{case_dir / 'ground-truth.md'}（派发子代理时不要给它）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
