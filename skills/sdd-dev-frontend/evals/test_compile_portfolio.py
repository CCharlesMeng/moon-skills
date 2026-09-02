"""compile_portfolio.py：触发器 → 模块 → 角色 → 维度的映射由规则表决定，agent 只负责识别风险。

每条用例守一条会被「省事」侵蚀的边：lite 不能被默认授予、只能升不能降、
下限触发器不能悄悄收窄、被 diff 反驳的维度不能不分配。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compile_portfolio.py"
SPEC = importlib.util.spec_from_file_location("compile_portfolio", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
RULES = MODULE.load_rules(MODULE.DEFAULT_RULES)


def tasks_md(*, restore_tasks="", risk_triggers="interaction", required_states="", routes="/orders", claims=None) -> str:
    claims = claims if claims is not None else [("AT-US1-001", "点击刷新重新取数", "S1_COMPONENT", "test_case", "T1")]
    rows = "\n".join(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in claims)
    return f"""# demo / US1 — 单仓实现计划

**TaskPacket:** project=demo | codespec_path=x | story=US1 | verification_schema=v2 | test_framework= | component_test_status=available | component_test_framework=Vitest | browser_test_status=absent | browser_test_framework= | search_paths=src | project_type=frontend | frontend_design_path= | baseline_source=text_spec | prototype_dir= | reference_route= | affected_routes={routes} | required_states={required_states} | restore_tasks={restore_tasks} | risk_triggers={risk_triggers}

## 用例追溯

| AT | 标题 | 验证范围 | 验证方法 | Task |
| --- | --- | --- | --- | --- |
{rows}

## Task List
"""


def diff_facts(files, triggers=None, rebuttals=None):
    return {
        "schema_version": 1,
        "changed_files": [{"path": p, "status": "M"} for p in files],
        "risk_triggers": {t: [{"rule": "x", "evidence": ev} for ev in evs] for t, evs in (triggers or {}).items()},
        "skip_rebuttals": {d: [{"rule": "x", "evidence": "y"}] for d in (rebuttals or [])},
    }


QA_WITH_R = """# dev-baseline

## QA 基线

### R1
| 编号 | 判定对象 | 具体期望 | 取证方式 |
| --- | --- | --- | --- |
| R1-1 | 面板 | 三个区块 | 冻结契约 |

### R6
| 编号 | 视口宽度 | 判定对象 | 具体期望 | 取证方式 |
| --- | --- | --- | --- | --- |
| R6-1 | 1200 | 面板 | 不横向滚动 | 冻结契约 |

### F2
| 编号 | AC 锚点 | 页面与路由 | 操作 | 可观察结果 |
| --- | --- | --- | --- | --- |
| F2-1 | AC-1 | /orders | 点刷新 | 列表更新 |

### F3
| 编号 | 类别 | 判定对象 | 触发方式 | 期望表现 |
| --- | --- | --- | --- | --- |
| F3-1 | 错误 | 面板 | 接口 500 | 错误态 |
"""


class TierTests(unittest.TestCase):
    def test_lite_needs_all_three_criteria(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(), phase="initial", plan_file_count=3)
        self.assertEqual(p["tier"]["value"], "lite")

    def test_any_blocking_trigger_makes_standard(self):
        for trigger in RULES["tier"]["blocking_triggers"]:
            with self.subTest(trigger=trigger):
                p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers=f"interaction,{trigger}"), phase="initial", plan_file_count=2)
                self.assertEqual(p["tier"]["value"], "standard")
                self.assertIn(trigger, p["tier"]["blocking_triggers"])

    def test_restore_task_or_file_count_makes_standard(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(restore_tasks="T1"), phase="initial", plan_file_count=1)
        self.assertEqual(p["tier"]["value"], "standard")
        p = MODULE.compile_portfolio(RULES, tasks_md(), phase="initial", plan_file_count=6)
        self.assertEqual(p["tier"]["value"], "standard")

    def test_lite_is_never_granted_without_a_file_count(self):
        """没有 diff 也没有计划文件数时不能靠默认值滑进 lite。"""
        with self.assertRaisesRegex(MODULE.PortfolioError, "file count unknown"):
            MODULE.compile_portfolio(RULES, tasks_md(), phase="initial")

    def test_final_phase_counts_actual_diff_and_only_upgrades(self):
        initial = MODULE.compile_portfolio(RULES, tasks_md(), phase="initial", plan_file_count=2)
        final = MODULE.compile_portfolio(
            RULES, tasks_md(), phase="final",
            diff_facts=diff_facts(["src/a.ts", "src/lib/request.ts"], triggers={"shared-boundary": ["src/lib/request.ts"]}),
        )
        self.assertEqual(final["tier"]["value"], "standard")
        self.assertEqual(MODULE.check_monotonic(initial, final), [])
        self.assertTrue(MODULE.check_monotonic(final, initial))  # reverse direction is a violation


class TriggerTests(unittest.TestCase):
    def test_sources_are_recorded_per_trigger(self):
        p = MODULE.compile_portfolio(
            RULES, tasks_md(risk_triggers="interaction,visual"), phase="final",
            diff_facts=diff_facts(["src/a.module.css"], triggers={"visual": ["src/a.module.css"]}),
            agent_triggers=["async-state"],
        )
        self.assertEqual(p["trigger_sources"]["visual"], ["diff", "plan"])
        self.assertEqual(p["trigger_sources"]["async-state"], ["agent"])

    def test_unknown_trigger_is_rejected(self):
        with self.assertRaisesRegex(MODULE.PortfolioError, "unknown risk trigger"):
            MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual,typo"), phase="initial", plan_file_count=1)

    def test_only_floor_triggers_can_be_narrowed_and_only_with_a_reason(self):
        facts = diff_facts(["vite.config.ts"], triggers={"build-config": ["vite.config.ts"]})
        p = MODULE.compile_portfolio(RULES, tasks_md(), phase="final", diff_facts=facts, narrowed={"build-config": "只改 alias 注释"})
        self.assertNotIn("build-config", p["risk_triggers"])
        self.assertEqual(p["portfolio_narrowed"], [{"trigger": "build-config", "reason": "只改 alias 注释"}])
        with self.assertRaisesRegex(MODULE.PortfolioError, "only diff-derived"):
            MODULE.compile_portfolio(RULES, tasks_md(), phase="final", diff_facts=facts, narrowed={"interaction": "x"})

    def test_cannot_narrow_a_trigger_the_plan_also_asserts(self):
        facts = diff_facts(["src/routes/index.ts"], triggers={"navigation": ["src/routes/index.ts"]})
        with self.assertRaisesRegex(MODULE.PortfolioError, "also asserted"):
            MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="navigation"), phase="final", diff_facts=facts, narrowed={"navigation": "x"})


class ModuleTests(unittest.TestCase):
    def test_minimal_story_gets_only_causal_and_targeted_quality(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(), phase="initial", plan_file_count=1)
        self.assertEqual(p["modules"], ["causal", "targeted-quality"])
        self.assertEqual(p["review_roles"], [])
        self.assertEqual(p["review_dimensions"], {})

    def test_auth_or_write_or_navigation_always_selects_story_and_self_test(self):
        """这里没有「causal 证据足够就不跑」的裁量：接缝类触发器一律跑真实路径。"""
        for trigger in ("auth", "write", "navigation"):
            with self.subTest(trigger=trigger):
                p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers=trigger), phase="initial", plan_file_count=1)
                self.assertIn("story", p["modules"])
                self.assertIn("self-test", p["modules"])
                self.assertIn("regression", p["modules"])

    def test_s3_claim_selects_story_even_without_seam_trigger(self):
        claims = [("AT-1", "跨页导航", "S3_STORY", "test_case", "T1")]
        p = MODULE.compile_portfolio(RULES, tasks_md(claims=claims), phase="initial", plan_file_count=1)
        self.assertIn("story", p["modules"])
        self.assertIn("story", p["claims"][0]["modules"])

    def test_visual_without_frozen_r_selects_render_but_not_review_restore(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual"), phase="initial", plan_file_count=1)
        self.assertIn("render", p["modules"])
        self.assertNotIn("review-restore", p["modules"])
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual", restore_tasks="T1"), phase="initial", plan_file_count=1, qa_baseline_md=QA_WITH_R)
        self.assertIn("review-restore", p["modules"])
        self.assertEqual(p["review_dimensions"]["review-restore"], ["R1", "R6"])

    def test_review_layout_needs_a_cross_page_or_viewport_fact(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual"), phase="initial", plan_file_count=1)
        self.assertNotIn("review-layout", p["modules"])
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual", required_states="overflow"), phase="initial", plan_file_count=1)
        self.assertIn("review-layout", p["modules"])
        self.assertIn("L2", p["review_dimensions"]["review-layout"])
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual", routes="/a,/b"), phase="initial", plan_file_count=1)
        self.assertIn("L1", p["review_dimensions"]["review-layout"])


class DimensionTests(unittest.TestCase):
    def test_rebutted_dimension_is_always_assigned(self):
        facts = diff_facts(["src/a.ts"], rebuttals=["C6", "Q7"])
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="interaction,write"), phase="final", diff_facts=facts)
        self.assertIn("review-convention", p["modules"])
        self.assertIn("C6", p["review_dimensions"]["review-convention"])
        self.assertIn("Q7", p["review_dimensions"]["review-quality"])

    def test_agent_dimensions_extend_but_must_exist(self):
        p = MODULE.compile_portfolio(
            RULES, tasks_md(risk_triggers="write"), phase="initial", plan_file_count=1,
            agent_dimensions={"review-quality": {"Q1", "Q3"}},
        )
        self.assertEqual(p["review_dimensions"]["review-quality"], ["Q1", "Q3", "Q5", "Q6"])
        with self.assertRaisesRegex(MODULE.PortfolioError, "unknown dimensions"):
            MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="write"), phase="initial", plan_file_count=1, agent_dimensions={"review-quality": {"Q9"}})

    def test_self_test_takes_f_rows_and_selected_reg(self):
        p = MODULE.compile_portfolio(
            RULES, tasks_md(risk_triggers="write"), phase="initial", plan_file_count=1,
            qa_baseline_md=QA_WITH_R, reg_rows=["REG-1"],
        )
        self.assertEqual(p["review_dimensions"]["self-test"], ["F2-1", "F3-1", "REG-1"])
        self.assertIn("Q6", p["review_dimensions"]["review-quality"])  # has_f3


class ClaimTests(unittest.TestCase):
    def test_claims_carry_scope_method_and_attached_modules(self):
        claims = [
            ("AT-1", "点击", "S1_COMPONENT", "test_case", "T1"),
            ("AT-2", "区块", "S2_PAGE", "restore_contract", "T2"),
            ("AT-3", "滚动舒服", "S2_PAGE", "manual_acceptance", "T3"),
        ]
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="visual", restore_tasks="T2", claims=claims), phase="initial", plan_file_count=3)
        by_id = {c["id"]: c for c in p["claims"]}
        self.assertEqual(by_id["AT-1"]["modules"], ["causal", "targeted-quality"])
        self.assertEqual(by_id["AT-2"]["modules"], ["causal", "render"])
        self.assertEqual(by_id["AT-3"]["modules"], ["causal"])
        self.assertTrue(all(c["status"] == "UNVERIFIED" for c in p["claims"]))

    def test_malformed_claim_rows_stop_compilation(self):
        with self.assertRaisesRegex(MODULE.PortfolioError, "验证范围"):
            MODULE.compile_portfolio(RULES, tasks_md(claims=[("AT-1", "x", "S1_COMPONENT/S2_PAGE", "test_case", "T1")]), phase="initial", plan_file_count=1)
        with self.assertRaisesRegex(MODULE.PortfolioError, "quality_gate does not produce"):
            MODULE.compile_portfolio(RULES, tasks_md(claims=[("AT-1", "x", "S1_COMPONENT", "quality_gate", "T1")]), phase="initial", plan_file_count=1)


class ExecutionProfileTests(unittest.TestCase):
    """required_profile 是「mock 下通过」与「真实接缝通过」不再压进同一个 PROVEN 的那道闸。"""

    def _profiles(self, triggers, claims):
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers=triggers, claims=claims), phase="initial", plan_file_count=2)
        return {c["id"]: c["required_profile"] for c in p["claims"]}

    def test_scope_and_seam_triggers_derive_the_profile(self):
        claims = [
            ("AT-1", "组件", "S1_COMPONENT", "test_case", "T1"),
            ("AT-2", "页面", "S2_PAGE", "test_case", "T1"),
            ("AT-3", "跨页", "S3_STORY", "test_case", "T1"),
            ("AT-4", "区块", "S2_PAGE", "restore_contract", "T2"),
            ("AT-5", "体感", "S2_PAGE", "manual_acceptance", "T3"),
        ]
        self.assertEqual(self._profiles("interaction", claims), {"AT-1": "mock", "AT-2": "mock", "AT-3": "contract", "AT-4": "mock", "AT-5": "live"})
        self.assertEqual(self._profiles("interaction,write", claims)["AT-3"], "live")
        self.assertEqual(self._profiles("interaction,write", claims)["AT-1"], "mock")

    def test_agent_can_only_raise_a_profile(self):
        claims = [("AT-1", "组件", "S1_COMPONENT", "test_case", "T1"), ("AT-3", "跨页", "S3_STORY", "test_case", "T1")]
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="write", claims=claims), phase="initial", plan_file_count=1, raised_profiles={"AT-1": "contract"})
        self.assertEqual({c["id"]: c["required_profile"] for c in p["claims"]}, {"AT-1": "contract", "AT-3": "live"})
        with self.assertRaisesRegex(MODULE.PortfolioError, "can only be raised"):
            MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="write", claims=claims), phase="initial", plan_file_count=1, raised_profiles={"AT-3": "mock"})
        with self.assertRaisesRegex(MODULE.PortfolioError, "unknown claims"):
            MODULE.compile_portfolio(RULES, tasks_md(claims=claims), phase="initial", plan_file_count=1, raised_profiles={"AT-9": "live"})
        with self.assertRaisesRegex(MODULE.PortfolioError, "unknown execution profile"):
            MODULE.compile_portfolio(RULES, tasks_md(claims=claims), phase="initial", plan_file_count=1, raised_profiles={"AT-1": "real"})

    def test_previous_portfolio_pins_profiles_from_below(self):
        claims = [("AT-3", "跨页", "S3_STORY", "test_case", "T1")]
        initial = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="write", claims=claims), phase="initial", plan_file_count=1)
        final = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="interaction", claims=claims), phase="final", diff_facts=diff_facts(["src/a.ts"]))
        self.assertIn("AT-3 required_profile lowered live → contract", MODULE.check_monotonic(initial, final))


class CliTests(unittest.TestCase):
    def test_cli_writes_json_and_markdown_and_enforces_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tasks.md").write_text(tasks_md(), encoding="utf-8")
            (root / "diff.json").write_text(json.dumps(diff_facts(["src/a.ts", "src/lib/x.ts"], triggers={"shared-boundary": ["src/lib/x.ts"]})), encoding="utf-8")
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "initial", "--plan-files", "2", "--out", str(root / "p0.json")]), 0)
            self.assertEqual(json.loads((root / "p0.json").read_text())["tier"]["value"], "lite")
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "final", "--diff-facts", str(root / "diff.json"), "--previous", str(root / "p0.json"), "--out", str(root / "pc.json")]), 0)
            self.assertEqual(json.loads((root / "pc.json").read_text())["tier"]["value"], "standard")
            # going back is refused
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "initial", "--plan-files", "2", "--previous", str(root / "pc.json"), "--out", str(root / "bad.json")]), 3)
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "final"]), 2)

    def test_cli_overwrites_previous_in_place_and_keeps_snapshot(self):
        """Phase 0 and Phase C share one file: --previous and --out are the same path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tasks.md").write_text(tasks_md(), encoding="utf-8")
            (root / "diff.json").write_text(json.dumps(diff_facts(["src/a.ts", "src/lib/x.ts"], triggers={"shared-boundary": ["src/lib/x.ts"]})), encoding="utf-8")
            out = root / "portfolio.json"
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "initial", "--plan-files", "2", "--out", str(out)]), 0)
            initial = json.loads(out.read_text())
            self.assertIsNone(initial["previous"])
            self.assertEqual(MODULE.main(["--tasks", str(root / "tasks.md"), "--phase", "final", "--diff-facts", str(root / "diff.json"), "--previous", str(out), "--out", str(out)]), 0)
            final = json.loads(out.read_text())
            self.assertEqual(final["phase"], "final")
            self.assertEqual(final["previous"]["phase"], "initial")
            self.assertEqual(final["previous"]["tier"], "lite")
            self.assertEqual(final["previous"]["modules"], initial["modules"])
            self.assertEqual(final["previous"]["required_profiles"], {c["id"]: c["required_profile"] for c in initial["claims"]})
            self.assertNotIn("previous", final["previous"])

    def test_markdown_render_names_tier_and_table(self):
        p = MODULE.compile_portfolio(RULES, tasks_md(risk_triggers="write"), phase="initial", plan_file_count=1)
        text = MODULE.render_markdown(p)
        self.assertIn("执行档位：**standard**", text)
        self.assertIn("| 风险触发器 | 来源 | 模块 | 独立检视与维度 | 依赖声明 |", text)
        self.assertIn("self-test", text)


if __name__ == "__main__":
    unittest.main()
