#!/usr/bin/env python3
"""把冻结的 fixture 源料展开成一个可跑的现场。

现场里的东西全部是派生物，不进仓：目标业务仓、仓库 baseline、Story 产物、
design-spec 都由本脚本从仓内源料确定性重建。源料只有四样：
`repo/`、`baseline/repo-3-patterns.md`、`cases/<case>/`、以及 `evals/` 下的两份原型 HTML。

    python3 setup.py --case convention-01
    python3 setup.py --case convention-01 --work-dir /tmp/fx --with-design-spec

跑完会打印一张「路径变量取值」表，直接贴进子代理派发消息即可。
"""

from __future__ import annotations

import argparse
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
INIT_SKILL_DIR = SKILL_DIR.parent / "sdd-init-frontend"

REPO_ID = "risk-console"
# 现场必须逐字节可复现，所以时间戳取 fixture 的冻结日期，不取当前时间。
FREEZE_DATE = "2026-08-05"
LIMIT = "依赖未安装，质量命令与浏览器采集均未实跑；本现场只支持静态判据类模块的评测"
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


def build_baseline(repo: Path, work_dir: Path) -> tuple[Path, str]:
    """扫描 → 注入人工维护范式 → 重扫（把范式声明的文件并入输入）→ finalize。"""
    baseline_dir = work_dir / "frontend-baselines" / REPO_ID
    scanner = INIT_SKILL_DIR / "scripts" / "manage_repo_baseline.py"
    scan = [
        sys.executable, str(scanner), "scan",
        "--repo-root", str(repo),
        "--baseline-dir", str(baseline_dir),
        "--repo-id", REPO_ID,
    ]
    run(scan)

    baseline_file = baseline_dir / "repo-baseline.md"
    patterns = (FIXTURE_DIR / "baseline" / "repo-3-patterns.md").read_text(encoding="utf-8")
    body = baseline_file.read_text(encoding="utf-8")
    marker = "\n## 新鲜度账本"
    if marker not in body:
        raise SystemExit("baseline 缺少「新鲜度账本」节，无法定位人工维护段的插入点")
    head, tail = body.split(marker, 1)
    baseline_file.write_text(f"{head.rstrip()}\n\n{patterns.strip()}\n{marker}{tail}", encoding="utf-8")

    run(scan)
    write_onboarding_report(baseline_dir)
    run([
        sys.executable, str(scanner), "finalize",
        "--repo-root", str(repo),
        "--baseline-dir", str(baseline_dir),
        "--status", "READY_WITH_LIMITS",
        "--limit", LIMIT,
    ])

    fingerprint = read_repo3_fingerprint(baseline_file)
    return baseline_dir, fingerprint


def write_onboarding_report(baseline_dir: Path) -> None:
    """把 scan 生成的草稿报告改写成如实的实证记录，好让 finalize 能收口。

    仓库路径与 Section 指纹沿用草稿里机器生成的那几行，只替换执行时间与草稿正文。
    """
    report_path = baseline_dir / "onboarding-report.md"
    draft = report_path.read_text(encoding="utf-8")
    head = draft.split("\n## 下一步", 1)[0]
    head = head.replace("| 执行时间 | 待执行 |", f"| 执行时间 | `{FREEZE_DATE}` |")
    body = (FIXTURE_DIR / "baseline" / "onboarding-report-body.md").read_text(encoding="utf-8")
    report_path.write_text(f"{head.rstrip()}\n\n{body.strip()}\n", encoding="utf-8")


def read_repo3_fingerprint(baseline_file: Path) -> str:
    for line in baseline_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `REPO-3`"):
            cells = [cell.strip().strip("`") for cell in line.split("|")]
            return cells[3]
    raise SystemExit("baseline 的 Section 表里找不到 REPO-3 指纹")


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

    case_dir = FIXTURE_DIR / "cases" / args.case
    if not case_dir.is_dir():
        available = sorted(p.name for p in (FIXTURE_DIR / "cases").iterdir() if p.is_dir())
        raise SystemExit(f"没有这个用例：{args.case}；现有：{available}")

    work_dir = Path(args.work_dir).resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="sdd-fe-fixture-"))
    if work_dir.exists() and any(work_dir.iterdir()):
        raise SystemExit(f"现场目录非空，换一个或先清空：{work_dir}")
    work_dir.mkdir(parents=True, exist_ok=True)

    repo, base_ref = build_repo(work_dir)
    baseline_dir, fingerprint = build_baseline(repo, work_dir)
    story_dir = build_story(case_dir, work_dir, {
        "BASELINE_DIR": str(baseline_dir),
        "STORY_DIR": str(work_dir / "story"),
        "BASE_REF": base_ref,
        "REPO3_FINGERPRINT": fingerprint,
    })
    changed = apply_case(case_dir, repo)
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
    print(f"| `<base-ref>` | `{base_ref}` |")
    if design_spec is not None:
        print(f"| `<design-spec-dir>` | `{design_spec}/risk-brief` |")
    print(f"\nREPO-3 指纹：{fingerprint}")
    print(f"待检视改动（{len(changed)} 个文件）：")
    for item in dirty:
        print(f"  {item}")
    print(f"\nground truth：{case_dir / 'ground-truth.md'}（派发子代理时不要给它）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
