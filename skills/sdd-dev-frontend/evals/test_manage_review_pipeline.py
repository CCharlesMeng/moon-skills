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
            {"blocker": 1, "suggestion": 1, "open_question": 1, "deferred": 1, "handoff": 3, "skipped": 0},
        )
        self.assertEqual(aggregate["findings"][0]["level"], "blocker")
        self.assertEqual(aggregate["findings"][0]["roles"], ["review-convention", "review-quality"])
        self.assertEqual(len(aggregate["handoff"]), 3)

    def test_zero_findings_markdown_is_compact_and_complete(self):
        aggregate = MODULE.aggregate_results(self.base_results())
        markdown = MODULE.render_markdown(aggregate)
        self.assertLess(len(markdown.splitlines()), 70)
        self.assertIn("阻断级 0 条", markdown)
        self.assertIn("## Handoff 清单\n\n无。", markdown)

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
        self.assertIn("## 判定不适用", markdown)
        self.assertIn("命中 skip_when", markdown)
        self.assertIn("判定不适用 1 条", markdown)

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
        self.assertEqual(aggregate["roles"], {"review-restore": "executed"})
        self.assertIn("review-restore", MODULE.render_markdown(aggregate))

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


if __name__ == "__main__":
    unittest.main()
