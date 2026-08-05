import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "manage_repo_baseline.py"


def run_script(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode})\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def make_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "demo-web",
                "private": True,
                "packageManager": "pnpm@10.0.0",
                "engines": {"node": ">=20"},
                "scripts": {
                    "dev": "vite",
                    "test": "vitest run",
                    "check": "svelte-check && tsc --noEmit",
                    "lint": "eslint .",
                    "build": "vite build",
                },
                "dependencies": {
                    "react": "^19.0.0",
                    "axios": "^1.0.0",
                    "zustand": "^5.0.0",
                },
                "devDependencies": {"vite": "^7.0.0", "vitest": "^3.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (root / ".env.example").write_text(
        "VITE_API_BASE_URL=http://localhost:3000\nAPI_SECRET=\n",
        encoding="utf-8",
    )
    (root / "eslint.config.js").write_text("export default []\n", encoding="utf-8")
    (root / "src" / "router.ts").write_text("export const routes = []\n", encoding="utf-8")
    (root / "public").mkdir()
    (root / "public" / "latest-scene.webp").write_bytes(b"fake image")
    (root / "public" / "united-states.json").write_text("{}\n", encoding="utf-8")
    installed_skill = root / ".agents" / "skills" / "demo"
    installed_skill.mkdir(parents=True)
    (installed_skill / "README.md").write_text("internal skill\n", encoding="utf-8")


def scan(repo: Path, baseline: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run_script(
        "scan",
        "--repo-root",
        str(repo),
        "--target-app",
        ".",
        "--baseline-dir",
        str(baseline),
        "--repo-id",
        repo.name,
        *extra,
    )


def complete_report(baseline: Path, repo_id: str = "demo") -> None:
    (baseline / "onboarding-report.md").write_text(
        f"""# Frontend Onboarding Report — {repo_id}

## 结论

| 项 | 值 |
| --- | --- |
| 状态 | `DRAFT` |

## 本次准备动作

- dependencies verified

## 当前机器

- node 20

## 页面验证

- /health: ok

## 工程质量

- test: exit 0
""",
        encoding="utf-8",
    )


def add_repo3_pattern(baseline: Path, evidence_path: str = "src/components/Card.tsx") -> None:
    path = baseline / "repo-baseline.md"
    text = path.read_text(encoding="utf-8")
    pattern = f"""

### 人工维护（agent 维护）

#### `PATTERN-PANEL-1` · 页面面板

| 项 | 内容 |
| --- | --- |
| 适用场景 | 页面面板、详情容器 |
| 工程入口 | `{evidence_path}` |
| 标签 | `panel`、`layout` |

##### 证据

| 路径 | 支持的结论 |
| --- | --- |
| `{evidence_path}` | 面板入口与组件写法 |
"""
    text = text.replace("\n## 新鲜度账本", pattern + "\n## 新鲜度账本", 1)
    path.write_text(text, encoding="utf-8")


class ManageRepoBaselineTest(unittest.TestCase):
    def test_scan_writes_markdown_as_the_only_baseline_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "demo"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            make_repo(repo)

            result = scan(repo, baseline)

            self.assertIn("# Baseline Scan", result.stdout)
            self.assertEqual(
                {path.name for path in baseline.iterdir()},
                {"repo-baseline.md", "onboarding-report.md"},
            )
            document = (baseline / "repo-baseline.md").read_text(encoding="utf-8")
            self.assertIn("`schema_version` | `2`", document)
            self.assertIn("`pnpm`", document)
            self.assertIn("`>=20`", document)
            self.assertIn("`VITE_API_BASE_URL`", document)
            self.assertIn("`pnpm run check`", document)
            self.assertIn("## 新鲜度账本", document)
            self.assertNotIn("未见", document)
            self.assertNotIn("未声明", document)
            self.assertNotIn("0 个", document)
            self.assertNotIn("public/latest-scene.webp", document)
            self.assertNotIn(".agents/skills/demo/README.md", document)

    def test_finalize_status_report_tamper_and_section_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "demo"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            make_repo(repo)
            scan(repo, baseline)

            draft = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertEqual(draft.returncode, 3)
            self.assertIn("| readiness | `DRAFT` |", draft.stdout)

            complete_report(baseline)
            run_script(
                "finalize",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                "--status",
                "READY",
            )
            ready = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
            )
            self.assertIn("| usable | 是 |", ready.stdout)

            report = baseline / "onboarding-report.md"
            report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            tampered = run_script(
                "validate",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertEqual(tampered.returncode, 3)
            self.assertIn("onboarding report changed after finalize", tampered.stdout)

            run_script(
                "finalize",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                "--status",
                "READY",
            )
            (repo / "src" / "router.ts").write_text(
                "export const routes = ['/new']\n", encoding="utf-8"
            )
            stale = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertEqual(stale.returncode, 3)
            self.assertIn("- REPO-3", stale.stdout)

            refreshed = scan(repo, baseline, "--section", "REPO-3")
            self.assertNotIn("stale_sections", refreshed.stdout)
            after_refresh = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertIn("| readiness | `DRAFT` |", after_refresh.stdout)
            self.assertNotIn("## 失效 Section", after_refresh.stdout)

    def test_repository_pattern_is_preserved_and_its_evidence_participates_in_freshness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "demo"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            make_repo(repo)
            component = repo / "src" / "components" / "Card.tsx"
            component.parent.mkdir()
            component.write_text("export const Card = () => null\n", encoding="utf-8")
            scan(repo, baseline)
            add_repo3_pattern(baseline)

            newly_declared = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertIn("- REPO-3", newly_declared.stdout)

            scan(repo, baseline, "--section", "REPO-3")
            document = (baseline / "repo-baseline.md").read_text(encoding="utf-8")
            self.assertIn("`PATTERN-PANEL-1`", document)
            self.assertIn("`src/components/Card.tsx`", document)

            by_id = run_script(
                "show",
                "--baseline-dir",
                str(baseline),
                "--pattern-id",
                "PATTERN-PANEL-1",
            )
            self.assertIn("#### `PATTERN-PANEL-1`", by_id.stdout)
            by_tag = run_script(
                "show",
                "--baseline-dir",
                str(baseline),
                "--tag",
                "panel",
            )
            self.assertIn("页面面板", by_tag.stdout)

            component.write_text("export const Card = ({ children }) => children\n", encoding="utf-8")
            stale = run_script(
                "status",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertIn("- REPO-3", stale.stdout)

    def test_sparse_repository_omits_optional_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "sparse"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            (repo / "package.json").write_text(
                json.dumps(
                    {
                        "name": "sparse-web",
                        "private": True,
                        "scripts": {"dev": "vite"},
                        "dependencies": {"svelte": "^5.0.0"},
                    }
                ),
                encoding="utf-8",
            )

            scan(repo, baseline)
            document = (baseline / "repo-baseline.md").read_text(encoding="utf-8")
            self.assertNotIn("Node 约束", document)
            self.assertNotIn("环境变量契约", document)
            self.assertNotIn("未见", document)
            self.assertNotIn("未声明", document)
            self.assertNotIn("0 个", document)
            self.assertNotIn("## REPO-2 工程质量", document)
            self.assertNotIn("| ui |", document)
            self.assertNotIn("| state |", document)

    def test_required_missing_start_command_produces_one_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "missing-start"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            (repo / "package.json").write_text(
                json.dumps(
                    {
                        "name": "missing-start-web",
                        "scripts": {"build": "vite build"},
                        "dependencies": {"react": "^19.0.0"},
                    }
                ),
                encoding="utf-8",
            )

            scan(repo, baseline)
            document = (baseline / "repo-baseline.md").read_text(encoding="utf-8")
            self.assertIn("`ACTION-RUNTIME-1`", document)
            self.assertIn("补齐 package.json 中的 dev/start/serve/preview 脚本", document)
            self.assertNotIn("启动命令：未见", document)

    def test_finalize_inserts_only_actual_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "limited"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            make_repo(repo)
            scan(repo, baseline)
            complete_report(baseline, "limited")

            run_script(
                "finalize",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                "--status",
                "READY_WITH_LIMITS",
                "--limit",
                "缺少非必需视觉字体；安装字体后解除",
            )
            report = (baseline / "onboarding-report.md").read_text(encoding="utf-8")
            self.assertIn("## 限制", report)
            self.assertIn("缺少非必需视觉字体；安装字体后解除", report)
            self.assertNotIn("## 阻断", report)
            self.assertNotIn("## 进程交接", report)

    def test_duplicate_repository_pattern_ids_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "demo"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            make_repo(repo)
            component = repo / "src" / "components" / "Card.tsx"
            component.parent.mkdir()
            component.write_text("export const Card = () => null\n", encoding="utf-8")
            scan(repo, baseline)
            add_repo3_pattern(baseline)
            path = baseline / "repo-baseline.md"
            text = path.read_text(encoding="utf-8")
            duplicate = "\n#### `PATTERN-PANEL-1` · duplicate\n"
            path.write_text(text.replace("\n## 新鲜度账本", duplicate + "\n## 新鲜度账本"), encoding="utf-8")

            result = run_script(
                "validate",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            self.assertIn("duplicate REPO-3 pattern IDs", result.stdout)

    def test_scan_refuses_ambiguous_target_apps_with_markdown_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "mono"
            repo.mkdir()
            (repo / "package.json").write_text(
                json.dumps({"name": "mono", "private": True, "workspaces": ["apps/*"]}),
                encoding="utf-8",
            )
            for name in ("a", "b"):
                app = repo / "apps" / name
                app.mkdir(parents=True)
                (app / "package.json").write_text(
                    json.dumps(
                        {
                            "name": name,
                            "scripts": {"dev": "vite"},
                            "dependencies": {"react": "^19.0.0"},
                        }
                    ),
                    encoding="utf-8",
                )

            result = run_script(
                "scan",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(tmp_path / "baseline"),
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("# Baseline Error", result.stderr)
            self.assertIn("`apps/a`", result.stderr)
            self.assertIn("`apps/b`", result.stderr)

    def test_legacy_json_curated_facts_migrate_to_markdown_and_must_be_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            repo = tmp_path / "demo"
            baseline = tmp_path / "baseline"
            repo.mkdir()
            baseline.mkdir()
            make_repo(repo)
            (baseline / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repo_id": "demo",
                        "repo_root": str(repo),
                        "target_app": ".",
                        "sections": {
                            section: {"fingerprint": "old", "inputs": []}
                            for section in ("REPO-1", "REPO-2", "REPO-3")
                        },
                        "readiness": {"status": "DRAFT"},
                    }
                ),
                encoding="utf-8",
            )
            (baseline / "repo-baseline.json").write_text(
                json.dumps(
                    {
                        "repository": {"id": "demo", "root": str(repo), "target_app": "."},
                        "sections": {
                            "REPO-1": {"curated": {}},
                            "REPO-2": {"curated": {}},
                            "REPO-3": {
                                "curated": {
                                    "state_pattern": {
                                        "summary": "Use the shared store",
                                        "evidence": [{"path": "src/router.ts"}],
                                    }
                                }
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            migrated = scan(repo, baseline)
            self.assertIn("已把旧 baseline 人工事实迁入 Markdown", migrated.stdout)
            document = (baseline / "repo-baseline.md").read_text(encoding="utf-8")
            self.assertIn("`PATTERN-STATE-PATTERN`", document)
            self.assertIn("Use the shared store", document)

            invalid = run_script(
                "validate",
                "--repo-root",
                str(repo),
                "--baseline-dir",
                str(baseline),
                check=False,
            )
            self.assertEqual(invalid.returncode, 3)
            self.assertIn("legacy baseline JSON remains", invalid.stdout)


if __name__ == "__main__":
    unittest.main()
