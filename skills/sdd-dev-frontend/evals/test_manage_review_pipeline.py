#!/usr/bin/env python3
"""Regression tests for shared scenario recording and review aggregation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "manage_review_pipeline.py"
SPEC = importlib.util.spec_from_file_location("manage_review_pipeline", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def code(a="a1", b="b1", unrelated="u2"):
    value = {
        "base_ref": "base",
        "head": "head",
        "files": [
            {"path": "src/a.tsx", "sha256": a},
            {"path": "src/b.tsx", "sha256": b},
            {"path": "src/unrelated.ts", "sha256": unrelated},
        ],
    }
    value["code_fingerprint"] = MODULE.sha256(value)
    return value


RUNTIME = {"browser": "Chromium 140", "dpr": 1, "font_fingerprint": "font", "account": "qa"}


def scenario(identifier, path, digest, page):
    return {
        "id": identifier,
        "consumers": ["review-layout", "self-test"],
        "page": page,
        "fixture": {"name": "default", "sha256": "fixture"},
        "viewport": {"width": 720, "height": 800},
        "steps": ["open", "click"],
        "observations": ["text=ready", "scrollWidth=720"],
        "artifacts": [f"/tmp/{identifier}.png"],
        "depends_on": [path],
        "captured_dependency_hashes": {path: digest},
        "captured_runtime": RUNTIME,
        "captured_at_code_fingerprint": "phase-b-old",
    }


def empty_package():
    return {"schema_version": 1, "evidence_epoch": "review-1", "scenarios": []}


def review(
    role, dimensions, *, findings=None, questions=None, deferred=None,
    status="executed", judged_files=None,
):
    return {
        "schema_version": 1,
        "role": role,
        "evidence_epoch": "review-1",
        "code_fingerprint": "fp",
        "judged_files": (
            (judged_files if judged_files is not None else ["src/a.tsx"])
            if status == "executed" else []
        ),
        "status": status,
        "coverage": [
            {"dimension": dimension, "scope": "scope", "evidence_ids": ["BE-1"], "result": "clear"}
            for dimension in dimensions
        ] if status == "executed" else [],
        "findings": findings or [],
        "open_questions": questions or [],
        "deferred_candidates": deferred or [],
        "evidence_reused": ["BE-1"] if status == "executed" else [],
        "evidence_added": [],
        "known_gaps": [] if status == "executed" else ["not applicable"],
    }


def finding(identifier, key, level="suggestion"):
    return {
        "id": identifier,
        "canonical_key": key,
        "dimension": identifier.split("-", 1)[0],
        "level": level,
        "summary": "same issue",
        "location": "src/a.tsx:L1-L2",
        "basis": f"basis {identifier}",
        "evidence_ids": ["BE-1"],
        "impact": "会让该分支的验收声明无法成立",
        "suggested_action": "按仓内既有写法改掉这一处",
    }


class ScenarioRecordingTests(unittest.TestCase):
    def test_unrelated_code_change_does_not_invalidate_exact_dependency(self):
        evidence, summary = MODULE.record_scenarios(
            empty_package(),
            code(unrelated="u9"),
            [scenario("PB-1", "src/a.tsx", "a1", "/a")],
            RUNTIME,
        )
        self.assertEqual(summary, {"recorded": ["BE-1"], "fresh": [], "stale": []})
        self.assertEqual(evidence["scenarios"][0]["captured_dependency_hashes"], {"src/a.tsx": "a1"})
        self.assertEqual(evidence["scenarios"][0]["source"], "phase-b")

    def test_only_changed_dependency_is_stale(self):
        evidence, summary = MODULE.record_scenarios(
            empty_package(),
            code(a="a2", b="b1"),
            [
                scenario("PB-A", "src/a.tsx", "a1", "/a"),
                scenario("PB-B", "src/b.tsx", "b1", "/b"),
            ],
            RUNTIME,
        )
        self.assertEqual(summary["recorded"], ["BE-1"])
        self.assertEqual(summary["stale"], [{"id": "PB-A", "reason": ["src/a.tsx"]}])
        self.assertEqual([item["page"] for item in evidence["scenarios"]], ["/b"])

    def test_raw_scenario_rejects_judgment(self):
        unsafe = scenario("PB-1", "src/a.tsx", "a1", "/a")
        unsafe["result"] = "pass"
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "judgment key"):
            MODULE.record_scenarios(empty_package(), code(), [unsafe], RUNTIME)

    def test_empty_additions_is_a_pure_freshness_check(self):
        package, _ = MODULE.record_scenarios(
            empty_package(),
            code(),
            [
                scenario("PB-A", "src/a.tsx", "a1", "/a"),
                scenario("PB-B", "src/b.tsx", "b1", "/b"),
            ],
            RUNTIME,
        )
        before = [dict(item) for item in package["scenarios"]]
        checked, summary = MODULE.record_scenarios(package, code(a="a2"), [], RUNTIME)
        self.assertEqual(summary["recorded"], [])
        self.assertEqual(summary["fresh"], ["BE-2"])
        self.assertEqual(summary["stale"], [{"id": "BE-1", "reason": ["src/a.tsx"]}])
        self.assertEqual(checked["scenarios"], before)

    def test_recapturing_a_stale_scenario_keeps_its_id(self):
        package, _ = MODULE.record_scenarios(
            empty_package(), code(), [scenario("PB-A", "src/a.tsx", "a1", "/a")], RUNTIME
        )
        recaptured = scenario("PB-A", "src/a.tsx", "a2", "/a")
        updated, summary = MODULE.record_scenarios(package, code(a="a2"), [recaptured], RUNTIME)
        self.assertEqual(summary["recorded"], ["BE-1"])
        self.assertEqual(summary["stale"], [])
        self.assertEqual(len(updated["scenarios"]), 1)
        self.assertEqual(
            updated["scenarios"][0]["captured_dependency_hashes"], {"src/a.tsx": "a2"}
        )

    def test_runtime_change_marks_every_scenario_stale(self):
        package, _ = MODULE.record_scenarios(
            empty_package(), code(), [scenario("PB-A", "src/a.tsx", "a1", "/a")], RUNTIME
        )
        _, summary = MODULE.record_scenarios(
            package, code(), [], {**RUNTIME, "browser": "Chromium 141"}
        )
        self.assertEqual(summary["fresh"], [])
        self.assertEqual(summary["stale"], [{"id": "BE-1", "reason": ["runtime-changed"]}])


class AggregateTests(unittest.TestCase):
    def base_results(self):
        return [
            review("review-layout", [f"L{i}" for i in range(1, 7)]),
            review("review-convention", [f"C{i}" for i in range(1, 8)]),
            review("review-quality", [f"Q{i}" for i in range(1, 9)]),
            review("self-test", ["F1-1", "F2-1", "F3-1", "F4-1", "REG-1"]),
            review("review-restore", [f"R{i}" for i in range(1, 7)]),
        ]

    def test_requires_assigned_coverage_and_same_epoch(self):
        results = self.base_results()
        results[0]["coverage"].pop()
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "coverage mismatch"):
            MODULE.aggregate_results(
                results,
                expected_dimensions={
                    "review-layout": [f"L{i}" for i in range(1, 7)],
                    "review-convention": [f"C{i}" for i in range(1, 8)],
                    "review-quality": [f"Q{i}" for i in range(1, 9)],
                    "self-test": ["F1-1", "F2-1", "F3-1", "F4-1", "REG-1"],
                    "review-restore": [f"R{i}" for i in range(1, 7)],
                },
            )
        results = self.base_results()
        results[3]["evidence_epoch"] = "review-2"
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "share evidence_epoch"):
            MODULE.aggregate_results(results)

    def test_deduplicates_takes_blocker_and_builds_exact_handoff(self):
        results = self.base_results()
        results[1]["findings"] = [finding("C5-1", "shared", "suggestion")]
        results[2]["findings"] = [finding("Q2-1", "shared", "blocker"), finding("Q8-1", "perf")]
        results[3]["open_questions"] = [{
            "id": "OQ-1", "canonical_key": "oq", "summary": "choose behavior",
            "needs_decision": True,
            "evidence_ids": ["BE-1"],
        }]
        results[3]["deferred_candidates"] = [{
            "id": "D-1", "canonical_key": "deferred", "ac": "AC-4", "reason": "backend missing",
            "resume_condition": "backend ready",
            "evidence_ids": ["BE-1"],
        }]
        aggregate = MODULE.aggregate_results(results)
        self.assertEqual(
            aggregate["counts"],
            {"blocker": 1, "suggestion": 1, "open_question": 1, "deferred": 1, "norm_candidate": 0, "unplanned_carry": 0, "manual_acceptance": 0, "manual_pending": 0, "decided": 0, "handoff": 3, "skipped": 0},
        )
        self.assertEqual(aggregate["findings"][0]["level"], "blocker")
        self.assertEqual(aggregate["findings"][0]["roles"], ["review-convention", "review-quality"])
        self.assertEqual(len(aggregate["handoff"]), 3)

    def test_zero_findings_markdown_is_compact_and_complete(self):
        aggregate = MODULE.aggregate_results(self.base_results())
        markdown = MODULE.render_markdown(aggregate)
        self.assertLess(len(markdown.splitlines()), 70)
        # 第一句必须是结论本身，不是计数——读的人先要知道能不能收。
        self.assertIn("**可验收**", markdown)
        # 全清时不摆「需要你处理」「你该知道」这些空节，也不摆空表。
        self.assertNotIn("## 需要你处理", markdown)
        self.assertNotIn("无。", markdown)
        self.assertIn("已判并通过：", markdown)

    def test_accepts_selected_roles_and_zero_role_portfolio(self):
        selected = [review("review-layout", ["L2", "L3"])]
        aggregate = MODULE.aggregate_results(
            selected,
            expected_roles=["review-layout"],
            expected_dimensions={"review-layout": ["L2", "L3"]},
            evidence_epoch="review-1",
            code_fingerprint="fp",
        )
        self.assertEqual(aggregate["roles"], {"review-layout": "executed"})
        empty = MODULE.aggregate_results(
            [], expected_roles=[], expected_dimensions={}, evidence_epoch="review-1", code_fingerprint="fp"
        )
        self.assertEqual(empty["roles"], {})
        self.assertEqual(empty["counts"]["blocker"], 0)

    def test_selected_role_can_report_unexecuted_without_fake_coverage(self):
        result = review(
            "review-layout",
            ["L2", "L3"],
            status="unexecuted",
        )
        result["known_gaps"] = ["browser driver unavailable after dispatch"]
        aggregate = MODULE.aggregate_results(
            [result],
            expected_roles=["review-layout"],
            expected_dimensions={"review-layout": ["L2", "L3"]},
            evidence_epoch="review-1",
            code_fingerprint="fp",
        )
        self.assertEqual(aggregate["roles"], {"review-layout": "unexecuted"})
        self.assertEqual(aggregate["coverage"], {"review-layout": []})
        self.assertEqual(
            aggregate["known_gaps"],
            {"review-layout": ["browser driver unavailable after dispatch"]},
        )

    def test_unexecuted_role_rejects_fake_evidence_and_invalid_assignment(self):
        result = review("review-layout", ["L2"], status="unexecuted")
        result["evidence_reused"] = ["BE-1"]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "only explain known_gaps"):
            MODULE.aggregate_results(
                [result],
                expected_roles=["review-layout"],
                expected_dimensions={"review-layout": ["L2"]},
            )

        result["evidence_reused"] = []
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "unknown dimensions"):
            MODULE.aggregate_results(
                [result],
                expected_roles=["review-layout"],
                expected_dimensions={"review-layout": ["L9"]},
            )

    def test_skipped_dimension_satisfies_assignment_and_reaches_the_report(self):
        result = review("review-layout", ["L2"])
        result["skipped"] = [{"dimension": "L3", "reason": "无 sticky / fixed 改动，命中 skip_when"}]
        aggregate = MODULE.aggregate_results(
            [result],
            expected_roles=["review-layout"],
            expected_dimensions={"review-layout": ["L2", "L3"]},
        )
        self.assertEqual(aggregate["counts"]["skipped"], 1)
        markdown = MODULE.render_markdown(aggregate)
        self.assertIn("判定不适用的检查项：", markdown)
        self.assertIn("命中 skip_when", markdown)
        self.assertIn("1 条判定不适用", markdown)

    def test_skipped_cannot_replace_a_reason_or_double_count_a_dimension(self):
        silent = review("review-layout", ["L2"])
        silent["skipped"] = [{"dimension": "L3"}]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, r"skipped\[0\].reason"):
            MODULE.aggregate_results([silent], expected_roles=["review-layout"])

        both = review("review-layout", ["L2", "L3"])
        both["skipped"] = [{"dimension": "L3", "reason": "命中 skip_when"}]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "both covered and skipped"):
            MODULE.aggregate_results([both], expected_roles=["review-layout"])

        unassigned = review("review-layout", ["L2"])
        unassigned["skipped"] = [{"dimension": "L4", "reason": "命中 skip_when"}]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "coverage mismatch"):
            MODULE.aggregate_results(
                [unassigned],
                expected_roles=["review-layout"],
                expected_dimensions={"review-layout": ["L2", "L3"]},
            )

    def test_restore_role_is_aggregated_and_bounded_to_its_dimensions(self):
        selected = [review("review-restore", ["R1", "R5"])]
        aggregate = MODULE.aggregate_results(
            selected,
            expected_roles=["review-restore"],
            expected_dimensions={"review-restore": ["R1", "R5"]},
        )
        # 线上值保持 review-restore / executed；只有渲染出来的报告用中文词。
        self.assertEqual(aggregate["roles"], {"review-restore": "executed"})
        self.assertIn("还原检视", MODULE.render_markdown(aggregate))

        # R 维度只有 R1–R6；越界必须被拒，否则 restore 格可以借编号扩张判据。
        out_of_range = review("review-restore", ["R7"])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "unknown dimensions"):
            MODULE.aggregate_results([out_of_range], expected_roles=["review-restore"])

        # 借用别格的维度号同样越界：restore 不得判 L/C/Q。
        borrowed = review("review-restore", ["L3"])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "unknown dimensions"):
            MODULE.aggregate_results([borrowed], expected_roles=["review-restore"])

    def test_restore_and_layout_reporting_one_issue_merge_into_one_finding(self):
        # 同一 canonical_key 出现在两格，说明跨格了；聚合取高级别并保留两个来源，
        # 让人能回原始证据判断该删掉哪一条，而不是在报告里出现两次。
        restore = review("review-restore", ["R6"])
        restore["findings"] = [finding("R6-1", "route:/orders|viewport:1280|overflow", "blocker")]
        layout = review("review-layout", ["L3"])
        layout["findings"] = [finding("L3-1", "route:/orders|viewport:1280|overflow")]
        aggregate = MODULE.aggregate_results(
            [restore, layout],
            expected_roles=["review-restore", "review-layout"],
            expected_dimensions={"review-restore": ["R6"], "review-layout": ["L3"]},
        )
        self.assertEqual(aggregate["counts"]["blocker"], 1)
        self.assertEqual(aggregate["counts"]["suggestion"], 0)
        self.assertEqual(aggregate["findings"][0]["roles"], ["review-layout", "review-restore"])

    def test_unexecuted_role_cannot_smuggle_skipped_dimensions(self):
        result = review("review-layout", ["L2"], status="unexecuted")
        result["skipped"] = [{"dimension": "L2", "reason": "命中 skip_when"}]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "only explain known_gaps"):
            MODULE.aggregate_results([result], expected_roles=["review-layout"])

    def test_raw_reviewer_addition_is_merged_and_references_are_rewritten(self):
        results = self.base_results()
        manifest = code()
        for result in results:
            result["code_fingerprint"] = manifest["code_fingerprint"]
        addition = scenario("layout-temp-1", "src/a.tsx", "a1", "/a")
        results[0]["evidence_added"] = [addition]
        results[0]["coverage"][0]["evidence_ids"] = ["layout-temp-1"]
        evidence, rewritten = MODULE.merge_evidence_additions(
            {"schema_version": 1, "evidence_epoch": "review-1", "code": manifest, "runtime": RUNTIME, "scenarios": []},
            results,
        )
        self.assertEqual(evidence["scenarios"][0]["id"], "BE-1")
        self.assertEqual(evidence["scenarios"][0]["source"], "review-layout")
        self.assertEqual(rewritten[0]["coverage"][0]["evidence_ids"], ["BE-1"])
        self.assertEqual(rewritten[0]["evidence_added"], [])
        self.assertIn("BE-1", rewritten[0]["evidence_reused"])


class FailureDirectionTests(unittest.TestCase):
    """每条新拒绝路径一对用例：拒绝一条、正当放行一条。"""

    def layout(self, **kwargs):
        return review("review-layout", ["L1"], **kwargs)

    def aggregate(self, results, **kwargs):
        return MODULE.aggregate_results(
            results,
            expected_roles=["review-layout"],
            expected_dimensions={"review-layout": ["L1"]},
            **kwargs,
        )

    def test_clear_without_evidence_is_rejected_but_unrun_is_allowed(self):
        blank = self.layout()
        blank["coverage"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "clear but cites no evidence"):
            MODULE.validate_review_result(blank)
        honest = self.layout()
        honest["coverage"][0].update({"result": "unrun", "evidence_ids": []})
        honest["known_gaps"] = ["browser driver unavailable"]
        self.assertEqual(MODULE.validate_review_result(honest)["role"], "review-layout")

    def test_unresolvable_evidence_is_rejected_and_static_forms_pass(self):
        index = MODULE.build_evidence_index(
            {"scenarios": [{"id": "BE-1"}], "quality_gate": {"commands": [{"name": "test"}]}}
        )
        ghost = self.layout()
        ghost["coverage"][0]["evidence_ids"] = ["BE-9"]
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "unresolvable evidence"):
            self.aggregate([ghost], evidence_index=index)
        for citation in ("BE-1", "test", "src/a.tsx:L1-L2", "PATTERN-3", "REQ-DEC-1"):
            good = self.layout()
            good["coverage"][0]["evidence_ids"] = [citation]
            self.assertEqual(len(self.aggregate([good], evidence_index=index)["roles"]), 1)

    def test_judged_files_must_be_present_and_inside_the_reviewed_state(self):
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "must list judged_files"):
            MODULE.validate_review_result(self.layout(judged_files=[]))
        outside = self.layout(judged_files=["src/ghost.tsx"])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "outside the reviewed code state"):
            self.aggregate([outside], code_files={"src/a.tsx"})
        inside = self.layout(judged_files=["src/a.tsx"])
        self.assertEqual(
            self.aggregate([inside], code_files={"src/a.tsx"})["judged_files"],
            {"review-layout": ["src/a.tsx"]},
        )

    def test_skipped_dimension_cannot_survive_a_diff_rebuttal(self):
        skipping = review("review-convention", [], status="executed")
        skipping["coverage"] = []
        skipping["skipped"] = [{"dimension": "C3", "reason": "diff 不涉及样式"}]
        rebuttal = {"C3": [{"rule": "style-or-token-file", "evidence": "src/a.module.css"}]}
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "but the diff touches it"):
            MODULE.aggregate_results(
                [skipping],
                expected_roles=["review-convention"],
                expected_dimensions={"review-convention": ["C3"]},
                skip_rebuttals=rebuttal,
            )
        # 同一份回传，diff 没有反驳时照常放行。
        self.assertEqual(
            len(MODULE.aggregate_results(
                [skipping],
                expected_roles=["review-convention"],
                expected_dimensions={"review-convention": ["C3"]},
                skip_rebuttals={"C6": [{"rule": "check-suppression", "evidence": "x"}]},
            )["skipped"]["review-convention"]),
            1,
        )

    def test_portfolio_must_carry_or_sign_every_derived_trigger(self):
        facts = {"risk_triggers": {"visual": [{"rule": "style-or-token-file", "evidence": "a.css"}]}}
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "without narrowing"):
            MODULE.check_portfolio_floor({"risk_triggers": ["interaction"]}, facts)
        carried = MODULE.check_portfolio_floor({"risk_triggers": ["visual"]}, facts)
        self.assertEqual(carried, [])
        signed = MODULE.check_portfolio_floor(
            {
                "risk_triggers": [],
                "portfolio_narrowed": [{"trigger": "visual", "reason": "样式文件只删注释"}],
            },
            facts,
        )
        self.assertEqual(signed, [{"trigger": "visual", "reason": "样式文件只删注释"}])

    def test_narrowing_cannot_double_book_a_carried_trigger(self):
        facts = {"risk_triggers": {"visual": [{"rule": "r", "evidence": "a.css"}]}}
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "also declared as a trigger"):
            MODULE.check_portfolio_floor(
                {
                    "risk_triggers": ["visual"],
                    "portfolio_narrowed": [{"trigger": "visual", "reason": "两头都占"}],
                },
                facts,
            )


class BlockerBlockRenderingTests(unittest.TestCase):
    """阻断级按「现象 / 影响 / 建议」三样分开渲染成块，不再是一格模板话。

    原先「要你做什么」那列统一填「先修掉，它挡住验收」——是模板话，没有任何可动手的
    信息；而真正的建议埋在 user_visible_text 里，那个字段同时装现象、影响和建议，
    结果放进表格就把现象说两遍。
    """

    ITEM = {
        "id": "Q6-1",
        "canonical_key": "component:HoldingsTable|empty-state",
        "dimension": "Q6",
        "level": "blocker",
        "summary": "没持仓时渲染的是只有表头的空表格，不是「暂无持仓」",
        "location": "HoldingsTable.tsx:47-55",
        "basis": "冻结基线 F3-3",
        "impact": "F3-3 与 AC-5.3 同时被证伪，且本 Story 无豁免",
        "suggested_action": "在 error 分支之后补一条空态分支，参照 PortfolioPanel 的三分支写法",
        "evidence_ids": ["BE-1"],
    }

    def _render(self):
        result = {
            "schema_version": 1, "role": "review-quality", "evidence_epoch": "e1",
            "code_fingerprint": "fp", "status": "executed", "judged_files": ["src/a.tsx"],
            "coverage": [{"id": "Q6-c", "dimension": "Q6", "scope": "s",
                          "evidence_ids": ["BE-1"], "result": "finding"}],
            "skipped": [], "findings": [self.ITEM], "open_questions": [],
            "deferred_candidates": [], "known_gaps": [],
            "evidence_reused": ["BE-1"], "evidence_added": [],
        }
        return MODULE.render_markdown(
            MODULE.aggregate_results(
                [result], expected_roles=["review-quality"],
                expected_dimensions={"review-quality": ["Q6"]},
            )
        )

    def test_all_three_facets_are_rendered_separately(self):
        body = self._render()
        self.assertIn(f"### 1. {self.ITEM['summary']}", body)
        self.assertIn(f"**影响**：{self.ITEM['impact']}", body)
        self.assertIn(f"**建议**：{self.ITEM['suggested_action']}", body)

    def test_the_old_boilerplate_action_is_gone(self):
        self.assertNotIn("先修掉，它挡住验收", self._render())

    def test_a_finding_without_an_action_is_rejected(self):
        """建议动作给不出时要写清为什么给不出；留空和「不需要建议」在输出上分不开。"""
        for field in ("impact", "suggested_action"):
            with self.subTest(field=field):
                broken = {k: v for k, v in self.ITEM.items() if k != field}
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, field):
                    MODULE.validate_review_result({
                        "schema_version": 1, "role": "review-quality",
                        "evidence_epoch": "e1", "code_fingerprint": "fp",
                        "status": "executed", "judged_files": ["src/a.tsx"],
                        "coverage": [{"id": "Q6-c", "dimension": "Q6", "scope": "s",
                                      "evidence_ids": ["BE-1"], "result": "finding"}],
                        "skipped": [], "findings": [broken], "open_questions": [],
                        "deferred_candidates": [], "known_gaps": [],
                        "evidence_reused": ["BE-1"], "evidence_added": [],
                    })


class DecisionRecordTests(unittest.TestCase):
    """待决项的答复就地记回报告，别让同一件事下一轮再被问一遍。

    原先待决项只被「报出来」：P7 说攒批上报，但答复没有任何落点——同一件事会重复问，
    而「当时为什么这么定」下个月没人说得清。Phase A2 的确认早就记进 dev-baseline 了，
    收口这侧一直缺同样的东西。
    """

    CANDIDATE = {
        "id": "NC-1", "kind": "broken", "target_id": "PATTERN-API-1",
        "claim": "出现第二个请求出口", "samples": ["src/a.ts:1"],
    }

    def _aggregate(self, decisions=None):
        return MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            norm_candidates=[self.CANDIDATE], decisions=decisions or [],
        )

    def test_unanswered_item_says_it_will_be_asked(self):
        body = MODULE.render_markdown(self._aggregate())
        self.assertIn("要你定", body)
        self.assertIn("回答后会记回本文件", body)

    def test_answer_is_recorded_in_place_with_its_time(self):
        body = MODULE.render_markdown(self._aggregate([{
            "item": "NC-1", "answer": "交 sdd-init-frontend 重新归纳",
            "decided_at": "2026-08-24 21:40", "rationale": "两处样本够了，不必再等",
        }]))
        self.assertIn("**你的决定**：交 sdd-init-frontend 重新归纳（2026-08-24 21:40）", body)
        self.assertIn("理由：两处样本够了，不必再等", body)
        self.assertNotIn("要你定", body)
        # 答完之后顶上那句必须翻过来，否则它还在催同一件事。
        self.assertIn("**可验收**", body)
        self.assertNotIn("需要你定", body)

    def test_item_answer_and_time_are_all_mandatory(self):
        for field in ("item", "answer", "decided_at"):
            with self.subTest(field=field):
                entry = {"item": "NC-1", "answer": "交给 init", "decided_at": "2026-08-24"}
                del entry[field]
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, field):
                    MODULE.validate_decisions([entry])

    def test_an_answer_with_no_matching_open_item_is_rejected(self):
        """挂不上任何待决项的答复不能静默收下——报告里会出现一条谁也对不上的决定。"""
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "not awaiting a decision"):
            self._aggregate([{
                "item": "NC-9", "answer": "随便", "decided_at": "2026-08-24",
            }])


class UnplannedCarryTests(unittest.TestCase):
    """计划外承接由聚合器渲染，而不是让人手写进一个会被覆盖的文件。

    原先共享执行契约要求「在 alpha-tests.md 与 acceptance.md 登记」，而 acceptance.md
    由聚合器整文件覆盖——Phase B 手写的登记会被 Phase C 冲掉，Phase D 再跑又冲一次。
    """

    ITEM = {
        "file": "src/lib/format.ts",
        "task": "T2",
        "reason": "改了金额口径，调用方的类型签名必须同步，否则 typecheck 不过",
    }

    def test_accepts_a_well_formed_entry(self):
        self.assertEqual(MODULE.validate_unplanned_carry([self.ITEM]), [self.ITEM])

    def test_file_task_and_reason_are_all_mandatory(self):
        """契约明写要登记「文件与原因」；缺任一项就不算登记过。"""
        for field in ("file", "task", "reason"):
            with self.subTest(field=field):
                item = {k: v for k, v in self.ITEM.items() if k != field}
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, field):
                    MODULE.validate_unplanned_carry([item])

    def test_it_reaches_the_report_and_survives_a_second_aggregate(self):
        """同一批数据再跑一次 aggregate，结果必须逐字节一致——这就是覆盖问题的反面。"""
        def build():
            agg = MODULE.aggregate_results(
                [], evidence_epoch="review-1", code_fingerprint="code-a",
                unplanned_carry=[self.ITEM],
            )
            return MODULE.render_markdown(agg)

        first = build()
        self.assertIn("顺带改到的文件（计划外承接）", first)
        self.assertIn("src/lib/format.ts", first)
        self.assertEqual(first, build())

    def test_absent_carry_adds_no_section(self):
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a"
        )
        self.assertEqual(aggregate["counts"]["unplanned_carry"], 0)
        self.assertNotIn("计划外承接", MODULE.render_markdown(aggregate))

    def test_no_placeholder_section_is_emitted_for_humans_to_fill(self):
        """聚合器不留「待 Phase D 填写」这类占位——它下一次重跑会把人写的内容冲掉。"""
        body = MODULE.render_markdown(
            MODULE.aggregate_results(
                [], evidence_epoch="review-1", code_fingerprint="code-a"
            )
        )
        self.assertNotIn("待 Phase D 填写", body)


class ManualAcceptanceTests(unittest.TestCase):
    """待人工验收项走 JSON 投影，权威登记仍在 alpha-tests.md。

    这条通道和 `--unplanned-carry` 同构：脚本不解析 Markdown。那份账本的表头归上游
    `schema_alpha_tests` 所有，建成「表头漂移即失败」的解析器只会让外部一次 schema
    调整打断整条流水线。

    人工验收是这条流水线里唯一没有可复算外部产物的证据——命令能重跑、契约能重判，
    「人看过了」不能。所以这里的 PROVEN 门比别处紧，而 `--decisions` 够不到人工项。
    """

    PENDING = {
        "id": "AT-US12-003",
        "trace": "SC-2",
        "verification_scope": "S2_PAGE",
        "manual_basis": "motion_judgment",
        "required_environment": "移动端 Safari，已登录的运营账号",
        "required_evidence": "滚动过程录屏",
        "manual_outcome": "NOT_RUN",
        "claim_status": "UNVERIFIED",
        "evidence_refs": [],
    }

    def _proven(self, **overrides):
        item = dict(
            self.PENDING,
            manual_outcome="PASSED",
            claim_status="PROVEN",
            manual_checked_by="qa-zhang",
            manual_checked_at="2026-08-31T14:20:00+08:00",
            evidence_refs=["artifacts/scroll.mp4"],
        )
        item.update(overrides)
        return item

    def test_accepts_a_well_formed_pending_entry(self):
        self.assertEqual(MODULE.validate_manual_acceptance([self.PENDING]), [self.PENDING])

    def test_planning_fields_are_all_mandatory(self):
        """没有环境和所需证据的人工项等于「人工看一下」，不算验收声明。"""
        for field in ("id", "trace", "verification_scope", "manual_basis",
                      "required_environment", "required_evidence"):
            with self.subTest(field=field):
                item = {k: v for k, v in self.PENDING.items() if k != field}
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, field):
                    MODULE.validate_manual_acceptance([item])

    def test_manual_basis_is_a_closed_enum(self):
        """自由文本会把例外无限扩大，所以依据只能从枚举里选。"""
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "manual_basis"):
            MODULE.validate_manual_acceptance([dict(self.PENDING, manual_basis="css")])

    def test_manual_status_is_not_a_claim_status(self):
        """`MANUAL` 不是第四种状态，两根轴也不能互相顶替。"""
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "claim_status"):
            MODULE.validate_manual_acceptance([dict(self.PENDING, claim_status="MANUAL")])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "manual_outcome"):
            MODULE.validate_manual_acceptance([dict(self.PENDING, manual_outcome="UNVERIFIED")])

    def test_illegal_pairings_are_rejected(self):
        """没跑过却说已验证、判失败却说已验证，都是这张表要挡的。"""
        for outcome, status in (("NOT_RUN", "PROVEN"), ("FAILED", "PROVEN"),
                                ("PASSED", "DEFERRED"), ("FAILED", "DEFERRED")):
            with self.subTest(pair=(outcome, status)):
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, "illegal pairing"):
                    MODULE.validate_manual_acceptance(
                        [dict(self.PENDING, manual_outcome=outcome, claim_status=status)]
                    )

    def test_proven_requires_signature_time_and_artifact(self):
        """四项缺一就退回 UNVERIFIED——签名不带产物不是证据。"""
        for field in ("manual_checked_by", "manual_checked_at"):
            with self.subTest(field=field):
                item = {k: v for k, v in self._proven().items() if k != field}
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, field):
                    MODULE.validate_manual_acceptance([item])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "no evidence_refs"):
            MODULE.validate_manual_acceptance([self._proven(evidence_refs=[])])

    def test_deferred_requires_a_resume_condition(self):
        item = dict(self.PENDING, claim_status="DEFERRED")
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "resume_condition"):
            MODULE.validate_manual_acceptance([item])
        MODULE.validate_manual_acceptance(
            [dict(item, resume_condition="待第三方账号开通")]
        )

    def _render(self, items):
        return MODULE.render_markdown(MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            manual_acceptance=items,
        ))

    def test_pending_item_blocks_an_unconditional_pass(self):
        """实现完成不等于验收通过，这份摘要不许把两件事说成一件。"""
        body = self._render([self.PENDING])
        self.assertIn("待 1 项人工验收", body)
        self.assertNotIn("**可验收**", body)
        self.assertIn("需要你处理", body)
        self.assertIn("AT-US12-003", body)

    def test_pending_item_is_an_action_not_a_heads_up(self):
        """待人工验收要人去做；落到「不用动」那节就自我矛盾了。"""
        body = self._render([self.PENDING])
        head, _, tail = body.partition("## 你该知道，但不用动")
        self.assertIn("AT-US12-003", head)
        self.assertNotIn("AT-US12-003", tail)

    def test_failed_manual_acceptance_blocks_acceptance(self):
        body = self._render([dict(self.PENDING, manual_outcome="FAILED")])
        self.assertIn("暂不可验收", body)
        self.assertIn("1 项人工验收未通过", body)

    def test_passed_without_evidence_asks_for_the_artifact_not_a_pass(self):
        """人判过了不能丢掉，但证据不齐也不能提前渲染成已证明。"""
        body = self._render([self._proven(claim_status="UNVERIFIED")])
        self.assertIn("补齐", body)
        self.assertNotIn("**可验收**", body)

    def test_settled_item_needs_no_action(self):
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            manual_acceptance=[self._proven()],
        )
        self.assertEqual(aggregate["counts"]["manual_pending"], 0)
        self.assertEqual(aggregate["counts"]["manual_acceptance"], 1)
        body = MODULE.render_markdown(aggregate)
        self.assertIn("**可验收**", body)
        self.assertIn("人工验收总表", body)

    def test_deferred_item_also_reaches_the_deferred_section(self):
        """找「什么被缓了」只该看一个地方。"""
        body = self._render([dict(
            self.PENDING, claim_status="DEFERRED", resume_condition="待第三方账号开通"
        )])
        self.assertIn("暂缓的验收项", body)
        self.assertIn("待第三方账号开通", body)

    def test_decisions_cannot_settle_a_manual_claim(self):
        """一句「可以了」不能顶替人工证据，所以答复够不到人工项。"""
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "not awaiting a decision"):
            MODULE.aggregate_results(
                [], evidence_epoch="review-1", code_fingerprint="code-a",
                manual_acceptance=[self.PENDING],
                decisions=[{
                    "item": "AT-US12-003", "answer": "可以了", "decided_at": "2026-08-31",
                }],
            )

    def test_absent_manual_items_keep_existing_output(self):
        """v1 Story 不传这个参数，输出必须与从前一致。"""
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a"
        )
        self.assertEqual(aggregate["counts"]["manual_acceptance"], 0)
        body = MODULE.render_markdown(aggregate)
        self.assertNotIn("人工验收", body)
        self.assertIn("**可验收**", body)

    def test_projection_is_stable_across_two_aggregates(self):
        first = self._render([self.PENDING])
        self.assertEqual(first, self._render([self.PENDING]))


class LedgerProjectionTests(unittest.TestCase):
    """聚合器直接读 alpha-tests.md / tasks.md，人手 JSON 投影这一步消失。

    表头按 story-artifacts.md 固定；漂移在这里报错，而不是在 agent 的手工投影里静默丢字段。
    """

    TASKS = """# demo

**TaskPacket:** project=demo | story=US1

## 用例追溯

| AT | 标题 | 验证范围 | 验证方法 | Task |
| --- | --- | --- | --- | --- |
| AT-US1-001 | 点击刷新 | S1_COMPONENT | test_case | T1 |
| AT-US1-002 | 滚动是否舒服 | S2_PAGE | manual_acceptance | T2 |
| AT-US1-003 | SSO 真实账号 | S3_STORY | manual_acceptance | T3 |
"""

    ALPHA = """# US1 · Alpha Tests

## 计划外承接
| 文件 | Task | 原因 |
| --- | --- | --- |
| src/types/order.ts | T1 | 字段类型对齐 |

## 人工验收记录
| 声明 | 追溯 | 依据 | 验收环境 | 需留下的证据 | 人工结果 | 声明状态 | 验收人 | 验收时间 | 证据引用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AT-US1-002 | SC-2 | motion_judgment | 移动端 Safari | 录屏 | PASSED | PROVEN | qa-li | 2026-08-30T10:00:00+08:00 | artifacts/a.mp4, artifacts/b.png |
| AT-US1-003 | SC-3 | external_dependency | 真实 SSO 账号 | 登录截图 | NOT_RUN | DEFERRED | — | — | — |

## AC ↔ 证据映射
| AT | 状态 | 证据记录 | 新鲜度 | 说明 |
| --- | --- | --- | --- | --- |
| AT-US1-001 | PROVEN | test:refresh | fresh | 无 |

## Deferred
| AT | 外部依赖 | 当前证据 | 解除条件 | 恢复入口 |
| --- | --- | --- | --- | --- |
| AT-US1-003 | SSO 测试租户 | 无 | 测试租户开通后 | Phase C 只重跑 story |
"""

    def test_projects_both_tables_and_pulls_scope_from_tasks(self):
        carry, manual = MODULE.project_alpha_tests(self.ALPHA, self.TASKS)
        self.assertEqual(carry, [{"file": "src/types/order.ts", "task": "T1", "reason": "字段类型对齐"}])
        by_id = {item["id"]: item for item in manual}
        proven = by_id["AT-US1-002"]
        self.assertEqual(proven["verification_scope"], "S2_PAGE")
        self.assertEqual(proven["evidence_refs"], ["artifacts/a.mp4", "artifacts/b.png"])
        self.assertEqual(proven["manual_checked_by"], "qa-li")
        deferred = by_id["AT-US1-003"]
        self.assertEqual(deferred["verification_scope"], "S3_STORY")
        self.assertEqual(deferred["resume_condition"], "测试租户开通后")
        self.assertNotIn("manual_checked_by", deferred)

    def test_manual_rows_need_tasks_for_scope(self):
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "--tasks not given"):
            MODULE.project_alpha_tests(self.ALPHA, None)
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "no such AT"):
            MODULE.project_alpha_tests(self.ALPHA, self.TASKS.replace("AT-US1-003", "AT-US1-009"))

    def test_header_drift_fails_loudly(self):
        drifted = self.ALPHA.replace("| 声明 | 追溯 |", "| 声明 | trace |")
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "lacks column '追溯'"):
            MODULE.project_alpha_tests(drifted, self.TASKS)

    def test_projection_goes_through_the_same_validators(self):
        """账本里写了 NOT_RUN + PROVEN，读出来一样被挡，不因为来源是 Markdown 就放过。"""
        bad = self.ALPHA.replace("| NOT_RUN | DEFERRED |", "| NOT_RUN | PROVEN |")
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "illegal pairing"):
            MODULE.project_alpha_tests(bad, self.TASKS)

    def test_ledger_without_those_sections_projects_nothing(self):
        carry, manual = MODULE.project_alpha_tests("# US1\n\n## AC ↔ 证据映射\n| AT | 状态 |\n| --- | --- |\n", None)
        self.assertEqual((carry, manual), ([], []))


class DisplayVocabularyTests(unittest.TestCase):
    """`acceptance.md` 里给人读的格子必须是中文，而线上值一个字不动。

    列头一直是中文，但单元格印的是生的枚举值（「结果」列 `clear`、「类型」列
    `norm_candidate`）。读的人不写 JSON、也不 grep 这份文件，英文形态对他没用。
    """

    def test_display_vocabulary_is_complete(self):
        """新增枚举值却忘了配词条时，这条会红。

        未登记的值会按原样印出英文——不会崩、也不会翻错，但读的人就得自己翻译。
        所以完整性要有人守，而这里是唯一守它的地方。
        """
        expected = (
            set(MODULE.ROLES)
            | {"executed", "not_applicable", "unexecuted"}
            | {"clear", "finding", "unrun", "skipped"}
            | {"blocker", "suggestion"}
            | {"open_question", "deferred", "norm_candidate", "manual_acceptance"}
            | MODULE.NORM_CANDIDATE_KINDS
            | set(MODULE.CLAIM_STATUSES)
            | set(MODULE.MANUAL_OUTCOMES)
            | set(MODULE.MANUAL_BASES)
        )
        missing = sorted(term for term in expected if term not in MODULE.DISPLAY)
        self.assertEqual(missing, [], f"缺中文词条：{missing}")

    def test_unmapped_value_falls_back_to_itself(self):
        """兜底必须可见：印英文原文，不吞掉也不猜。"""
        self.assertEqual(MODULE.display("brand-new-trigger"), "brand-new-trigger")

    def test_identifiers_and_free_text_are_never_translated(self):
        """维度号、证据 ID 与人写的句子不能被翻译碰到。"""
        rows = markdown_table_rows(
            [{"dimension": "Q4", "evidence_ids": ["BE-1"], "summary": "clear 这个词出现在句子里", "result": "clear"}],
            [("维度", "dimension"), ("证据", "evidence_ids"), ("发现", "summary"), ("结果", "result")],
        )
        self.assertIn("Q4", rows)
        self.assertIn("BE-1", rows)
        self.assertIn("clear 这个词出现在句子里", rows)
        self.assertIn("无发现", rows)

    def test_rendered_report_has_no_raw_enum_values(self):
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            norm_candidates=[{
                "id": "NC-1", "kind": "broken", "target_id": "PATTERN-API-1",
                "claim": "出现第二个请求出口", "samples": ["src/a.ts:1"],
            }],
        )
        aggregate["validation_portfolio"] = {
            "risk_triggers": ["visual", "shared-boundary"],
            "modules": ["render", "causal"],
        }
        aggregate["portfolio_narrowed"] = [
            {"trigger": "shared-boundary", "reason": "只删了注释"}
        ]
        body = MODULE.render_markdown(aggregate)
        for raw in ("norm_candidate", "shared-boundary", "broken", "blocker",
                    "Open Question", "Handoff"):
            self.assertNotIn(raw, body, f"`{raw}` 仍以英文原样出现在给人读的报告里")
        for zh in ("规范候选", "规范不再成立", "共享边界"):
            self.assertIn(zh, body)
        # 缓存失效键不该出现在给人看的文档里——人不会对它们做任何决定。
        self.assertNotIn(aggregate["code_fingerprint"], body)
        self.assertNotIn("证据纪元", body)


def markdown_table_rows(items, columns) -> str:
    return "\n".join(MODULE.markdown_table(items, columns))


class NormCandidateTests(unittest.TestCase):
    """规范候选是 Dev → init 的回流通道。

    此前这条通道只存在于散文里：`recon-codebase` 会回传「规范待确认」，规则说攒进
    `acceptance.md` 由 init 重新归纳，但 handoff 只有 suggestion / open_question /
    deferred 三类，装不下它——一句「攒进 handoff」到不了任何人手里。
    """

    BASE = {
        "id": "NC-1",
        "kind": "broken",
        "target_id": "PATTERN-API-1",
        "claim": "出现第二个请求出口，统一实例的约定已不成立",
        "samples": ["src/features/export/api.ts:12", "src/features/audit/api.ts:8"],
    }

    def test_accepts_a_well_formed_candidate(self):
        self.assertEqual(MODULE.validate_norm_candidates([self.BASE]), [self.BASE])

    def test_samples_are_mandatory(self):
        """没有依据样本，init 归纳规范就得从零重扫，这条回流就没有价值。"""
        for samples in ([], None):
            with self.subTest(samples=samples):
                item = {**self.BASE, "samples": samples}
                with self.assertRaises(MODULE.ReviewPipelineError):
                    MODULE.validate_norm_candidates([item])

    def test_broken_and_recurring_must_name_the_target(self):
        """说不出质疑哪一条，就分不清这是同一条的第 n 次复发还是新发现。"""
        for kind in ("broken", "exemption-recurring"):
            with self.subTest(kind=kind):
                item = {**self.BASE, "kind": kind}
                item.pop("target_id")
                with self.assertRaisesRegex(MODULE.ReviewPipelineError, "target_id"):
                    MODULE.validate_norm_candidates([item])

    def test_new_pattern_needs_no_target(self):
        item = {k: v for k, v in self.BASE.items() if k != "target_id"}
        item["kind"] = "new-pattern"
        self.assertEqual(MODULE.validate_norm_candidates([item])[0]["kind"], "new-pattern")

    def test_runtime_trap_requires_phenomenon(self):
        """门槛 1 次的补偿是可复现现象，不是样本数。"""
        item = {k: v for k, v in self.BASE.items() if k != "target_id"}
        item["kind"] = "runtime-trap"
        item["claim"] = "i18n 导入不能 as t"
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "phenomenon"):
            MODULE.validate_norm_candidates([item])
        item["phenomenon"] = "页面白屏，Console: TypeError: 'set' on proxy"
        validated = MODULE.validate_norm_candidates([item])[0]
        self.assertEqual(validated["kind"], "runtime-trap")
        self.assertEqual(validated["phenomenon"], item["phenomenon"])

    def test_runtime_trap_reaches_handoff_with_phenomenon(self):
        item = {
            "id": "NC-2",
            "kind": "runtime-trap",
            "claim": "抽屉不用 v-model",
            "phenomenon": "弹窗 display:none 不展示",
            "samples": ["src/features/risk/Drawer.vue:18"],
        }
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            norm_candidates=[item],
        )
        entry = next(
            row for row in aggregate["handoff"] if row["kind"] == "norm_candidate"
        )
        self.assertTrue(entry["needs_decision"])
        self.assertIn("运行时陷阱", entry["user_visible_text"])
        self.assertIn("弹窗 display:none 不展示", entry["user_visible_text"])
        body = MODULE.render_markdown(aggregate)
        self.assertIn("运行时陷阱", body)
        self.assertNotIn("runtime-trap", body)

    def test_single_sample_is_allowed(self):
        """跨 Story 的复发计数只有 init 能做；在这里卡样本数等于把计数依据吞掉。"""
        item = {**self.BASE, "samples": ["src/features/export/api.ts:12"]}
        self.assertEqual(len(MODULE.validate_norm_candidates([item])[0]["samples"]), 1)

    def test_unknown_kind_and_duplicate_id_are_rejected(self):
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "kind must be one of"):
            MODULE.validate_norm_candidates([{**self.BASE, "kind": "suggestion"}])
        with self.assertRaisesRegex(MODULE.ReviewPipelineError, "duplicate norm candidate"):
            MODULE.validate_norm_candidates([self.BASE, dict(self.BASE)])

    def test_candidate_reaches_handoff_and_always_needs_a_decision(self):
        """规范节只有 init 能改，所以 Story 侧无权自行采纳，必须由人裁决。"""
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a",
            norm_candidates=[self.BASE],
        )
        self.assertEqual(aggregate["counts"]["norm_candidate"], 1)
        entry = next(
            item for item in aggregate["handoff"] if item["kind"] == "norm_candidate"
        )
        self.assertTrue(entry["needs_decision"])
        self.assertIn("PATTERN-API-1", entry["user_visible_text"])
        self.assertIn("规范候选", MODULE.render_markdown(aggregate))

    def test_absent_candidates_add_no_section(self):
        aggregate = MODULE.aggregate_results(
            [], evidence_epoch="review-1", code_fingerprint="code-a"
        )
        self.assertEqual(aggregate["counts"]["norm_candidate"], 0)
        self.assertNotIn("## 规范候选", MODULE.render_markdown(aggregate))


if __name__ == "__main__":
    unittest.main()
