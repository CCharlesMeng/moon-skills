#!/usr/bin/env python3
"""Regression tests for the minimal V3 restore contract and V2 reader."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT.parent / "scripts" / "verify_restore_contract.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_restore_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load_module()


def baseline(ids=("R1-1",), *, frozen=True):
    rows = "\n".join(f"| {item} | 主体 | 具体期望 | 取证 |" for item in ids)
    return (
        "# Dev Baseline\n\n"
        f"冻结状态：{'已冻结 ✅' if frozen else '待确认 ⏳'}\n\n"
        "| 编号 | 判定对象 | 具体期望 | 取证方式 |\n"
        "| --- | --- | --- | --- |\n"
        f"{rows}\n"
    )


def render_rule(rule_id="R1-1-count", baseline_id="R1-1", expected=1, mode="exact", **extra):
    return {
        "id": rule_id,
        "baseline_id": baseline_id,
        "subject": rule_id,
        "check_mode": mode,
        "expected": expected,
        **extra,
    }


def static_rule(rule_id="R2-1-copy", baseline_id="R2-1", **extra):
    return {
        "id": rule_id,
        "baseline_id": baseline_id,
        "subject": rule_id,
        "static_check": {"kind": "text", "value": "保存"},
        **extra,
    }


def exempt_rule(rule_id="R3-1-shadow", baseline_id="R3-1"):
    return {
        "id": rule_id,
        "baseline_id": baseline_id,
        "subject": rule_id,
        "frozen_exemption": {"id": "EX-1", "reason": "平台限制"},
    }


def adapter_for(rules):
    entries = {}
    for rule in rules:
        if rule.get("frozen_exemption"):
            continue
        if rule.get("static_check"):
            entries[rule["id"]] = {"source_files": ["src/view.tsx"]}
        else:
            entries[rule["id"]] = {
                "locators": [{"strategy": "css", "selector": f"[data-rule='{rule['id']}']"}],
                "collect": {"kind": "count"},
            }
    return {"schema_version": 2, "rules": entries}


class Workspace:
    def __init__(self, root: Path, rules, ids=None):
        self.root = root
        self.baseline = root / "dev-baseline.md"
        self.baseline.write_text(baseline(ids or tuple(dict.fromkeys(r["baseline_id"] for r in rules))), encoding="utf-8")
        self.rules = root / "rules.json"
        self.rules.write_text(json.dumps({"rules": rules}, ensure_ascii=False), encoding="utf-8")
        self.contract = V.compile_contract(self.baseline, self.rules)
        self.contract_path = root / "restore-contract.json"
        V.write_json(self.contract_path, self.contract)
        self.adapter = adapter_for(rules)
        self.adapter_path = root / "restore-adapter.json"
        V.write_json(self.adapter_path, self.adapter)
        self.adapter = V.validate_adapter(self.adapter, self.contract)

    def render(self, rules, **extra):
        return {
            "schema_version": 1,
            "contract_sha256": self.contract["contract_sha256"],
            "page_available": True,
            "observed": {"viewport": {"width": 1280, "height": 720}, "route": "/orders"},
            "rules": rules,
            **extra,
        }

    def results(self, rules):
        return {"schema_version": 1, "contract_sha256": self.contract["contract_sha256"], "rules": rules}

    def report(self, phase="green", static=None, render=None):
        return V.build_report(self.contract, self.adapter, phase, static, render)

    def args(self):
        return ["--baseline", str(self.baseline), "--contract", str(self.contract_path), "--adapter", str(self.adapter_path)]


def run_cli(argv, stdin=None):
    stdout, stderr = io.StringIO(), io.StringIO()
    old_stdin = V.sys.stdin
    try:
        V.sys.stdin = io.StringIO(stdin or "")
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = V.main(argv)
    finally:
        V.sys.stdin = old_stdin
    return code, stdout.getvalue(), stderr.getvalue()


class V3RuleTests(unittest.TestCase):
    def test_default_tolerance_stays_implicit(self):
        rule = V.validate_rule_v3(render_rule(), 1)
        self.assertNotIn("tolerance", rule)

    def test_numeric_default_tolerance_is_one(self):
        rule = V.validate_rule_v3(render_rule(expected="16px", mode="numeric"), 1)
        self.assertNotIn("tolerance", rule)
        self.assertEqual(V.normalized_tolerance(rule), {"css_px": 1.0})

    def test_zero_and_false_are_valid_expected_values(self):
        for value in (0, False):
            with self.subTest(value=value):
                self.assertEqual(V.validate_rule_v3(render_rule(expected=value), 1)["expected"], value)

    def test_empty_render_expectations_are_rejected(self):
        for value in (None, "", [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(V.ContractError, "expected 为空"):
                    V.validate_rule_v3(render_rule(expected=value), 1)

    def test_threshold_modes_omit_expected(self):
        for mode in ("overflow", "overlap", "clip"):
            rule = render_rule(mode=mode)
            rule.pop("expected")
            normalized = V.validate_rule_v3(rule, 1)
            self.assertNotIn("tolerance", normalized)
            self.assertEqual(V.normalized_tolerance(normalized), {"css_px": 1.0})

    def test_v3_exact_object_may_have_a_render_key(self):
        expected = {"render": "literal application data"}
        rule = V.validate_rule_v3(render_rule(expected=expected), 1)
        self.assertEqual(V.expected_for_layer(rule, "render"), expected)

    def test_threshold_mode_rejects_dummy_expected(self):
        with self.assertRaisesRegex(V.ContractError, "不写 expected"):
            V.validate_rule_v3(render_rule(mode="overflow", expected=0), 1)

    def test_static_rule_has_no_expected(self):
        self.assertNotIn("expected", V.validate_rule_v3(static_rule(), 1))

    def test_exempt_rule_needs_id_and_reason_only(self):
        self.assertEqual(V.validate_rule_v3(exempt_rule(), 1)["frozen_exemption"]["id"], "EX-1")

    def test_three_forms_are_mutually_exclusive(self):
        rule = static_rule(check_mode="exact", expected=True)
        with self.assertRaisesRegex(V.ContractError, "只能是"):
            V.validate_rule_v3(rule, 1)

    def test_stacking_requires_boolean_expected(self):
        for expected in ({}, {"subject_on_top": "yes"}):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(V.ContractError, "布尔值"):
                    V.validate_rule_v3(render_rule(mode="stacking", expected=expected), 1)

    def test_scenario_is_free_text_and_fixture_is_boolean(self):
        rule = V.validate_rule_v3(render_rule(scenario="展开筛选", fixture_required=True), 1)
        self.assertEqual(rule["scenario"], "展开筛选")
        with self.assertRaisesRegex(V.ContractError, "scenario 必须是字符串"):
            V.validate_rule_v3(render_rule(scenario={"name": "default"}), 1)

    def test_removed_v2_fields_are_rejected_in_v3(self):
        removed_blind_spot = "visual" + "_blind_spot"
        for field in ("required_layers", "design_fact_source", "dimension", "block", "state_scenario", removed_blind_spot):
            with self.subTest(field=field):
                with self.assertRaisesRegex(V.ContractError, "已删除字段"):
                    V.validate_rule_v3(render_rule(**{field: "legacy"}), 1)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(V.ContractError, "不支持"):
            V.validate_rule_v3(render_rule(mode="visual"), 1)


class ContractTests(unittest.TestCase):
    def test_compile_emits_v3_top_level_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
        self.assertEqual(space.contract["schema_version"], 3)
        self.assertIn("baseline_sha256", space.contract)
        self.assertNotIn("baseline", space.contract)

    def test_baseline_must_be_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(frozen=False), encoding="utf-8")
            rules = root / "rules.json"
            rules.write_text(json.dumps([render_rule()]), encoding="utf-8")
            with self.assertRaisesRegex(V.ContractError, "尚未标记"):
                V.compile_contract(path, rules)

    def test_every_baseline_row_must_be_covered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(("R1-1", "R2-1")), encoding="utf-8")
            rules = root / "rules.json"
            rules.write_text(json.dumps([render_rule()]), encoding="utf-8")
            with self.assertRaisesRegex(V.ContractError, "没有对应"):
                V.compile_contract(path, rules)

    def test_one_baseline_row_can_compile_to_many_rules(self):
        rules = [render_rule(), render_rule("R1-1-order", expected=["A", "B"])]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
        self.assertEqual(len(space.contract["rules"]), 2)

    def test_duplicate_rule_ids_are_rejected(self):
        rules = [render_rule(), render_rule()]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            draft = root / "rules.json"
            draft.write_text(json.dumps(rules), encoding="utf-8")
            with self.assertRaisesRegex(V.ContractError, "必须唯一"):
                V.compile_contract(path, draft)

    def test_unknown_baseline_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            draft = root / "rules.json"
            draft.write_text(json.dumps([render_rule(baseline_id="R1-9")]), encoding="utf-8")
            with self.assertRaisesRegex(V.ContractError, "不存在"):
                V.compile_contract(path, draft)

    def test_baseline_hash_change_blocks_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [render_rule()])
            space.baseline.write_text(space.baseline.read_text(encoding="utf-8") + "改", encoding="utf-8")
            with self.assertRaisesRegex(V.ContractError, "哈希不一致"):
                V.validate_contract(space.contract, space.baseline)

    def test_contract_self_hash_is_only_a_link_key(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            space.contract["rules"][0]["expected"] = 9
            validated = V.validate_contract(space.contract, space.baseline)
        self.assertEqual(validated["rules"][0]["expected"], 9)

    def test_cli_reads_rules_from_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            out = root / "restore-contract.json"
            code, stdout, _ = run_cli(
                ["contract", "--baseline", str(path), "--rules", "-", "--out", str(out)],
                json.dumps({"rules": [render_rule()]}),
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["rules"], 1)

    def test_reconfirmation_archives_active_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [render_rule()])
            old_sha = space.contract["contract_sha256"]
            (root / "restore-report-green.json").write_text("{}", encoding="utf-8")
            space.baseline.write_text(baseline() + "\n重新确认。\n", encoding="utf-8")
            code, stdout, _ = run_cli([
                "contract", "--baseline", str(space.baseline), "--rules", str(space.rules),
                "--out", str(space.contract_path), "--after-reconfirmation",
            ])
            archived = root / f"restore-report-green.stale-{old_sha[:8]}.json"
        self.assertEqual(code, 0)
        self.assertTrue(archived.exists() or json.loads(stdout)["archived_reports"])

    def test_recompile_without_reconfirmation_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [render_rule()])
            space.baseline.write_text(baseline() + "\n改过。\n", encoding="utf-8")
            code, _, stderr = run_cli([
                "contract", "--baseline", str(space.baseline), "--rules", str(space.rules),
                "--out", str(space.contract_path),
            ])
        self.assertEqual(code, V.EXIT_ERROR)
        self.assertIn("after-reconfirmation", stderr)


class V2CompatibilityTests(unittest.TestCase):
    def legacy_contract(self, baseline_path):
        rule = {
            "id": "R1-1", "baseline_id": "R1-1", "dimension": "R1", "block": "页面",
            "subject": "区块", "expected": 1, "check_mode": "structure",
            "state_scenario": {"name": "default"},
            "design_fact_source": {"path": "design-facts.json", "anchor": ".page", "key": "blocks[]"},
            "required_layers": ["render"],
        }
        return {
            "schema_version": 2,
            "baseline": {"path": "dev-baseline.md", "sha256": V.sha256_file(baseline_path)},
            "rules": [rule],
            "contract_sha256": "legacy-link",
        }

    def test_v2_contract_and_v1_adapter_still_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            contract = V.validate_contract(self.legacy_contract(path), path)
            adapter = V.validate_adapter({
                "schema_version": 1,
                "rules": {"R1-1": {"locators": [{"strategy": "css", "selector": ".page"}], "collect": {"kind": "count"}}},
            }, contract)
        self.assertEqual(adapter["schema_version"], 1)

    def test_v2_self_hash_is_not_recomputed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            contract = self.legacy_contract(path)
            contract["rules"][0]["expected"] = 4
            self.assertEqual(V.validate_contract(contract, path)["contract_sha256"], "legacy-link")

    def test_v2_visual_rule_stays_readable_and_reports_yellow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "dev-baseline.md"
            path.write_text(baseline(), encoding="utf-8")
            contract = self.legacy_contract(path)
            contract["rules"][0].update({"check_mode": "visual", "required_layers": ["visual"]})
            contract = V.validate_contract(contract, path)
            adapter = V.validate_adapter({"schema_version": 1, "rules": {"R1-1": {}}}, contract)
            report = V.build_report(contract, adapter, "green", None, None)
        self.assertEqual(report["overall"], "yellow")


class AdapterTests(unittest.TestCase):
    def test_locator_order_is_free(self):
        rule = render_rule()
        adapter = {
            "schema_version": 2,
            "rules": {rule["id"]: {
                "locators": [
                    {"strategy": "css", "selector": ".page"},
                    {"strategy": "role", "role": "main", "name": "订单"},
                ],
                "collect": {"kind": "count"},
            }},
        }
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [rule])
            self.assertEqual(len(V.validate_adapter(adapter, space.contract)["rules"][rule["id"]]["locators"]), 2)

    def test_adapter_judgment_like_fields_are_not_scanned(self):
        rule = render_rule()
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [rule])
            adapter = adapter_for([rule])
            adapter["rules"][rule["id"]]["collect"]["expected"] = "collector option"
            self.assertIn("expected", V.validate_adapter(adapter, space.contract)["rules"][rule["id"]]["collect"])

    def test_generated_class_only_warns(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            V.validate_locator({"strategy": "css", "selector": ".css-a1b2c3d4e5"}, "R1-1")
        self.assertEqual(len(caught), 1)

    def test_render_rule_requires_locator_and_collect(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            for entry in ({"collect": {}}, {"locators": [{"strategy": "css", "selector": ".x"}]}):
                with self.subTest(entry=entry):
                    with self.assertRaises(V.ContractError):
                        V.validate_adapter({"schema_version": 2, "rules": {"R1-1-count": entry}}, space.contract)

    def test_static_rule_only_needs_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [static_rule()], ids=("R2-1",))
        self.assertNotIn("locators", space.adapter["rules"]["R2-1-copy"])

    def test_extra_adapter_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            adapter = adapter_for([render_rule()])
            adapter["rules"]["R9-9"] = {}
            with self.assertRaisesRegex(V.ContractError, "不存在"):
                V.validate_adapter(adapter, space.contract)


class StaticAndCssTests(unittest.TestCase):
    def static_result(self, rule, body):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/view.tsx").write_text(body, encoding="utf-8")
            space = Workspace(root, [rule], ids=(rule["baseline_id"],))
            return V.run_static_preflight(space.contract, space.adapter, root)["rules"][rule["id"]]

    def test_text_is_exact(self):
        self.assertEqual(self.static_result(static_rule(), 'const x = "保存"')["status"], "pass")
        self.assertEqual(self.static_result(static_rule(), 'const x = "保存 "')["status"], "pass")

    def test_forbidden_literal(self):
        rule = static_rule(static_check={"kind": "forbidden_literals", "values": ["NaN"]})
        self.assertEqual(self.static_result(rule, "return 0")["status"], "pass")
        self.assertEqual(self.static_result(rule, "return NaN")["status"], "fail")

    def test_regex(self):
        rule = static_rule(static_check={"kind": "regex", "pattern": r"font-size:\s*14px"})
        self.assertEqual(self.static_result(rule, ".x { font-size: 14px; }")["status"], "pass")

    def test_css_colors_zero_and_shadow_order_are_equivalent(self):
        pairs = [
            ("#fff", "rgb(255, 255, 255)"),
            ("0px", "0"),
            ("0 1px 2px rgba(0,0,0,.08)", "rgba(0, 0, 0, 0.08) 0px 1px 2px"),
        ]
        for left, right in pairs:
            with self.subTest(pair=(left, right)):
                self.assertTrue(V.css_values_equivalent(left, right))

    def test_system_font_aliases_are_equivalent(self):
        self.assertTrue(V.css_values_equivalent("BlinkMacSystemFont", "system-ui"))
        self.assertTrue(V.css_values_equivalent("-apple-system", "system-ui"))
        self.assertTrue(V.css_values_equivalent(
            '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            '-apple-system, "system-ui", "Segoe UI", sans-serif',
        ))

    def test_numeric_nested_values_respect_tolerance(self):
        rule = V.validate_rule_v3(render_rule(expected={"gap": "16px"}, mode="numeric"), 1)
        self.assertTrue(V.compare_actual(rule, rule["expected"], {"gap": "17px"})[0])
        self.assertFalse(V.compare_actual(rule, rule["expected"], {"gap": "18px"})[0])


class ReportTests(unittest.TestCase):
    def test_green_report_is_slim_and_records_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            report = space.report(render=space.render({"R1-1-count": {"status": "ok", "actual": 1}}))
        self.assertEqual(report["overall"], "green")
        self.assertEqual(report["observed"]["route"], "/orders")
        self.assertEqual(set(report["entries"][0]), {"rule_id", "status", "actual"})
        self.assertNotIn("report_sha256", report)
        self.assertNotIn("baseline_sha256", report)

    def test_red_entry_keeps_local_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule(expected="保存")])
            entry = space.report(render=space.render({"R1-1-count": {"status": "ok", "actual": "提交"}}))["entries"][0]
        for key in ("expected", "actual", "comparison", "reasons", "hint"):
            self.assertIn(key, entry)

    def test_page_unavailable_is_yellow(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            report = space.report(render=space.render({}, page_available=False, reason="server down"))
        self.assertEqual(report["overall"], "yellow")

    def test_capture_error_and_missing_rule_are_red(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            capture = space.report(render=space.render({}, capture_error="boom"))
            missing = space.report(render=space.render({}))
        self.assertEqual(capture["overall"], "red")
        self.assertEqual(missing["overall"], "red")

    def test_missing_static_result_is_red(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [static_rule()], ids=("R2-1",))
            report = space.report(static=None)
        self.assertEqual(report["overall"], "red")

    def test_static_only_report_needs_no_render_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/view.tsx").write_text("保存", encoding="utf-8")
            space = Workspace(root, [static_rule()], ids=("R2-1",))
            static = V.run_static_preflight(space.contract, space.adapter, root)
            report = space.report(static=static)
        self.assertEqual(report["overall"], "green")

    def test_exemption_is_green_without_adapter_or_results(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [exempt_rule()], ids=("R3-1",))
            report = space.report()
        self.assertEqual(report["entries"][0]["frozen_exemption"], "EX-1")

    def test_red_outranks_yellow(self):
        rules = [render_rule(), render_rule("R2-1-copy", "R2-1", "保存")]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(render=space.render({
                "R1-1-count": {"status": "ok", "actual": 9},
                "R2-1-copy": {"status": "unavailable", "reason": "fixture"},
            }))
        self.assertEqual(report["summary"], {"red": 1, "yellow": 1, "green": 0, "total": 2})
        self.assertEqual(report["overall"], "red")

    def test_green_phase_exit_code(self):
        self.assertEqual(V.report_exit_code("green", "red"), 3)
        self.assertEqual(V.report_exit_code("green", "green"), 0)
        self.assertEqual(V.report_exit_code("red", "red"), 0)

    def test_result_contract_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [render_rule()])
            with self.assertRaisesRegex(V.ContractError, "不一致"):
                space.report(render={"contract_sha256": "other", "rules": {}})


class MergeTests(unittest.TestCase):
    def test_cross_page_merge_prefers_usable_fact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [render_rule()])
            first = root / "a.json"
            second = root / "b.json"
            V.write_json(first, space.render({"R1-1-count": {"status": "error", "reason": "missing"}}))
            V.write_json(second, space.render({"R1-1-count": {"status": "ok", "actual": 1}}))
            merged = V.merge_render_payloads([str(first), str(second)], space.contract["contract_sha256"])
        self.assertEqual(merged["rules"]["R1-1-count"]["status"], "ok")
        self.assertEqual(len(merged["observed"]["captures"]), 2)

    def test_all_pages_unavailable_stays_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [render_rule()])
            paths = []
            for name in ("a", "b"):
                path = root / f"{name}.json"
                V.write_json(path, space.render({}, page_available=False))
                paths.append(str(path))
            merged = V.merge_render_payloads(paths, space.contract["contract_sha256"])
        self.assertFalse(merged["page_available"])


class SizeTests(unittest.TestCase):
    def test_verifier_stays_within_budget(self):
        self.assertLessEqual(len(SCRIPT.read_text(encoding="utf-8").splitlines()), 750)


if __name__ == "__main__":
    unittest.main()
