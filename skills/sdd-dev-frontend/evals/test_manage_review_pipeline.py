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
        "user_visible_text": "这个问题会影响用户，建议后续处理。",
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
            "user_visible_text": "需要决定边界行为，否则该分支无法验收。", "needs_decision": True,
            "evidence_ids": ["BE-1"],
        }]
        results[3]["deferred_candidates"] = [{
            "id": "D-1", "canonical_key": "deferred", "ac": "AC-4", "reason": "backend missing",
            "resume_condition": "backend ready", "user_visible_text": "AC-4 等后端就绪后再验收。",
            "evidence_ids": ["BE-1"],
        }]
        aggregate = MODULE.aggregate_results(results)
        self.assertEqual(
            aggregate["counts"],
            {"blocker": 1, "suggestion": 1, "open_question": 1, "deferred": 1, "norm_candidate": 0, "unplanned_carry": 0, "handoff": 3, "skipped": 0},
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
            | {"open_question", "deferred", "norm_candidate"}
            | MODULE.NORM_CANDIDATE_KINDS
            | {"PROVEN", "UNVERIFIED", "DEFERRED"}
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
