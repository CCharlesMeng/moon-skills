#!/usr/bin/env python3
"""Regression tests for the frozen restore-contract verifier.

判据只认冻结基线：契约编译后基线任一字节变化都要硬失败，三色汇总不得把 YELLOW
洗成 GREEN，静态层通过也不能替代 render 层。这些是脚本存在的理由，逐条钉在这里。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
VERIFIER_PATH = EVAL_DIR.parent / "scripts" / "verify_restore_contract.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_restore_contract", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_verifier()

def frozen_baseline(rules: list, *, frozen: bool = True) -> str:
    """按给定规则渲染一份基线。

    契约与基线要求一一映射，所以基线必须恰好含这批规则引用的编号——
    写死一份固定基线的话，每个只测一条规则的用例都会因「基线里还有别的条目没覆盖」而红。
    """
    ids = [rule if isinstance(rule, str) else str(rule["baseline_id"]) for rule in rules]
    rows = "\n".join(
        f"| {rule_id} | {rule_id.split('-')[0]} | {rule_id} 主体 | 见规则 |"
        for rule_id in dict.fromkeys(ids)
    )
    state = "已冻结 ✅" if frozen else "待确认 ⏳"
    return (
        "# Dev Baseline\n\n"
        f"冻结状态：{state}\n\n"
        "| 编号 | 维度 | 主体 | 期望 |\n"
        "| --- | --- | --- | --- |\n"
        f"{rows}\n"
    )


FROZEN_BASELINE = frozen_baseline(["R1-1", "R3-1"])

UNFROZEN_BASELINE = frozen_baseline(["R1-1", "R3-1"], frozen=False)


def make_rule(
    rule_id: str,
    dimension: str = "R1",
    *,
    expected=1,
    check_mode: str = "exact",
    baseline_id: str | None = None,
    layers: list[str] | None = None,
    tolerance: dict | None = None,
    static_check: dict | None = None,
    exemption: dict | None = None,
    drop: tuple[str, ...] = (),
) -> dict:
    rule = {
        "id": rule_id,
        "baseline_id": baseline_id or rule_id,
        "dimension": dimension,
        "block": "筛选栏",
        "subject": f"{rule_id} 主体",
        "expected": expected,
        "check_mode": check_mode,
        "state_scenario": {"name": "default"},
        "design_fact_source": {
            "path": "design-facts.json",
            "anchor": ".filters",
            "key": rule_id,
        },
        "required_layers": ["render"] if layers is None else layers,
    }
    if tolerance is not None:
        rule["tolerance"] = tolerance
    if static_check is not None:
        rule["static_check"] = static_check
    if exemption is not None:
        rule["frozen_exemption"] = exemption
    for field in drop:
        rule.pop(field, None)
    return rule


def default_adapter(rules: list[dict], source_files: list[str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "rules": {
            rule["id"]: {
                "locators": [
                    {"strategy": "role", "role": "button", "name": rule["id"]}
                ],
                "source_files": list(source_files or ["src/view.tsx"]),
                "collect": {"kind": "count"},
            }
            for rule in rules
            if not rule.get("frozen_exemption")
        },
    }


class Workspace:
    """在临时目录里搭一套完整的冻结工件：基线、规则草稿、契约、adapter。"""

    def __init__(
        self,
        root: Path,
        rules: list[dict],
        *,
        baseline_text: str | None = None,
        adapter_payload: dict | None = None,
        source_files: list[str] | None = None,
    ) -> None:
        self.root = Path(root)
        self.rules = rules
        self.baseline_path = self.root / "dev-baseline.md"
        self.baseline_path.write_text(
            frozen_baseline(rules) if baseline_text is None else baseline_text,
            encoding="utf-8",
        )
        self.draft_path = self.root / "rules-draft.json"
        self.draft_path.write_text(
            json.dumps({"rules": rules}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.contract = VERIFIER.compile_contract(
            self.baseline_path,
            self.draft_path,
            "dev-baseline.md",
        )
        self.contract_path = self.root / "restore-contract.json"
        VERIFIER.write_json(self.contract_path, self.contract)
        self.adapter_payload = (
            adapter_payload
            if adapter_payload is not None
            else default_adapter(rules, source_files)
        )
        self.adapter_path = self.root / "restore-adapter.json"
        VERIFIER.write_json(self.adapter_path, self.adapter_payload)
        self.adapter = VERIFIER.validate_adapter(self.adapter_payload, self.contract)

    def render(self, values: dict, **overrides) -> dict:
        payload = {
            "schema_version": 1,
            "contract_sha256": self.contract["contract_sha256"],
            "page_available": True,
            "rules": values,
        }
        payload.update(overrides)
        return payload

    def results(self, values: dict) -> dict:
        return {
            "schema_version": 1,
            "contract_sha256": self.contract["contract_sha256"],
            "rules": values,
        }

    def write(self, name: str, payload) -> Path:
        path = self.root / name
        VERIFIER.write_json(path, payload)
        return path

    def report(self, phase: str, *, static=None, render=None, visual=None) -> dict:
        return VERIFIER.build_report(
            self.contract,
            self.adapter,
            phase,
            static,
            render,
            visual,
        )

    def contract_args(self) -> list[str]:
        return [
            "--baseline",
            str(self.baseline_path),
            "--contract",
            str(self.contract_path),
            "--adapter",
            str(self.adapter_path),
        ]

    def tamper_baseline(self) -> None:
        self.baseline_path.write_text(
            self.baseline_path.read_text(encoding="utf-8") + "\n改了一个字节。\n",
            encoding="utf-8",
        )


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """跑 CLI 并吃掉输出，返回 (退出码, stdout, stderr)。"""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = VERIFIER.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def statuses(report: dict) -> dict:
    return {entry["rule_id"]: entry["status"] for entry in report["entries"]}


class BaselineFreezeTests(unittest.TestCase):
    """基线是唯一判据：改一个字节就不许再执行，脚本也不许自愈。"""

    def test_single_byte_baseline_change_fails_every_consuming_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            render_path = space.write(
                "render-results.json",
                space.render({"R1-1": {"status": "ok", "actual": 1}}),
            )
            self.assertEqual(run_cli(["validate", *space.contract_args()])[0], VERIFIER.EXIT_OK)

            frozen_bytes = space.contract_path.read_bytes()
            space.baseline_path.write_text(
                space.baseline_path.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )

            for argv in (
                ["validate", *space.contract_args()],
                [
                    "static",
                    *space.contract_args(),
                    "--repo-root",
                    str(root),
                    "--out",
                    str(root / "static-results.json"),
                ],
                [
                    "report",
                    "--phase",
                    "red",
                    *space.contract_args(),
                    "--render-results",
                    str(render_path),
                    "--out",
                    str(root / "restore-report-red.json"),
                ],
            ):
                with self.subTest(command=argv[0]):
                    code, _, stderr = run_cli(argv)
                    self.assertEqual(code, VERIFIER.EXIT_ERROR)
                    self.assertIn("哈希不一致", stderr)

            # 拒绝执行的同时不得回写契约，否则等于自动接受被改动的基线。
            self.assertEqual(space.contract_path.read_bytes(), frozen_bytes)
            self.assertFalse((root / "static-results.json").exists())
            self.assertFalse((root / "restore-report-red.json").exists())

    def test_baseline_hash_mismatch_names_both_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            frozen_sha256 = space.contract["baseline"]["sha256"]
            space.tamper_baseline()
            actual_sha256 = VERIFIER.sha256_file(space.baseline_path)

            with self.assertRaises(VERIFIER.ContractError) as caught:
                VERIFIER.validate_contract(space.contract, space.baseline_path)

        message = str(caught.exception)
        self.assertIn(frozen_sha256, message)
        self.assertIn(actual_sha256, message)
        self.assertNotEqual(frozen_sha256, actual_sha256)

    def test_recompiling_against_a_changed_baseline_yields_a_different_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            space.tamper_baseline()
            recompiled = VERIFIER.compile_contract(
                space.baseline_path,
                space.draft_path,
                "dev-baseline.md",
            )

        self.assertNotEqual(
            recompiled["baseline"]["sha256"],
            space.contract["baseline"]["sha256"],
        )
        self.assertNotEqual(
            recompiled["contract_sha256"],
            space.contract["contract_sha256"],
        )
        self.assertEqual(recompiled["rules"], space.contract["rules"])

    def test_unfrozen_baseline_blocks_compile_and_every_consuming_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            space.baseline_path.write_text(UNFROZEN_BASELINE, encoding="utf-8")
            draft = space.draft_path

            with self.assertRaisesRegex(VERIFIER.ContractError, "尚未标记为已冻结"):
                VERIFIER.compile_contract(space.baseline_path, draft)

            code, _, stderr = run_cli(["validate", *space.contract_args()])

        self.assertEqual(code, VERIFIER.EXIT_ERROR)
        self.assertIn("尚未标记为已冻结", stderr)

    def test_contract_self_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            tampered = json.loads(json.dumps(space.contract))
            tampered["rules"][0]["expected"] = 99

            with self.assertRaisesRegex(VERIFIER.ContractError, "自身哈希不一致"):
                VERIFIER.validate_contract(tampered, space.baseline_path)


class SummaryPrecedenceTests(unittest.TestCase):
    """有 RED 即 RED；无 RED 有 YELLOW 即 YELLOW；YELLOW 绝不能被汇总成 GREEN。"""

    def test_one_red_outranks_yellow_and_green(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=1),
            make_rule("R2-1", "R2", expected=["保存"]),
            make_rule("R5-1", "R5", expected={"empty": True}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "red",
                render=space.render(
                    {
                        "R1-1": {"status": "ok", "actual": 1},
                        "R2-1": {"status": "ok", "actual": ["提交"]},
                        "R5-1": {"status": "missing_fixture", "reason": "空态 fixture 未就绪"},
                    }
                ),
            )

        self.assertEqual(statuses(report), {"R1-1": "green", "R2-1": "red", "R5-1": "yellow"})
        self.assertEqual(report["overall"], "red")
        self.assertEqual(report["summary"], {"red": 1, "yellow": 1, "green": 1, "total": 3})

    def test_yellow_is_never_summarized_as_green(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=1),
            make_rule("R5-1", "R5", expected={"empty": True}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "green",
                render=space.render(
                    {
                        "R1-1": {"status": "ok", "actual": 1},
                        "R5-1": {"status": "unavailable", "reason": "空态无法构造"},
                    }
                ),
            )

        self.assertEqual(report["overall"], "yellow")
        self.assertEqual(report["summary"], {"red": 0, "yellow": 1, "green": 1, "total": 2})
        yellow = next(entry for entry in report["entries"] if entry["status"] == "yellow")
        self.assertEqual(yellow["reasons"], ["空态无法构造"])
        self.assertTrue(yellow["required_evidence"])

    def test_green_requires_every_required_layer_to_be_verified(self) -> None:
        rule = make_rule(
            "R3-1",
            "R3",
            expected={"static": "--space-md", "render": "16px"},
            check_mode="numeric",
            layers=["static", "render"],
            static_check={"kind": "token", "value": "--space-md"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "view.tsx").write_text(
                'const gap = "var(--space-md)";',
                encoding="utf-8",
            )
            space = Workspace(root, [rule])
            static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)
            report = space.report(
                "green",
                static=static,
                render=space.render({"R3-1": {"status": "ok", "actual": "16px"}}),
            )

        entry = report["entries"][0]
        self.assertEqual(report["overall"], "green")
        self.assertEqual(entry["status"], "green")
        self.assertEqual(entry["verified_layers"], ["static", "render"])

    def test_every_green_entry_lists_verified_layers_or_a_frozen_exemption(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=1),
            make_rule(
                "R2-1",
                "R2",
                expected="保存",
                exemption={"id": "EX-1", "frozen": True, "reason": "平台能力限制"},
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "green",
                render=space.render({"R1-1": {"status": "ok", "actual": 1}}),
            )

        self.assertEqual(report["overall"], "green")
        self.assertEqual(report["summary"], {"red": 0, "yellow": 0, "green": 2, "total": 2})
        for entry in report["entries"]:
            with self.subTest(rule_id=entry["rule_id"]):
                self.assertTrue(
                    entry.get("verified_layers") or entry.get("frozen_exemption"),
                )

    def test_red_and_yellow_entries_carry_the_evidence_the_contract_promises(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=2),
            make_rule("R5-1", "R5", expected={"empty": True}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "red",
                render=space.render(
                    {
                        "R1-1": {"status": "ok", "actual": 5},
                        "R5-1": {"status": "missing_fixture", "reason": "空态 fixture 未就绪"},
                    }
                ),
            )

        by_id = {entry["rule_id"]: entry for entry in report["entries"]}
        red = by_id["R1-1"]
        self.assertEqual(red["expected"], 2)
        self.assertEqual(red["actual"]["render"]["comparison"]["actual"], 5)
        self.assertEqual(red["contract_source"]["baseline_id"], "R1-1")
        self.assertIn("locators", red["implementation_locator"])
        self.assertTrue(red["reasons"])

        yellow = by_id["R5-1"]
        self.assertEqual(
            yellow["required_evidence"],
            ["提供冻结基线指定的状态 fixture，再注入 collect_restore_facts.js"],
        )

    def test_report_fingerprints_are_stable_and_cover_the_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
            render = space.render({"R1-1": {"status": "ok", "actual": 1}})
            first = space.report("red", render=render)
            second = space.report("red", render=render)
            different = space.report(
                "red",
                render=space.render({"R1-1": {"status": "ok", "actual": 2}}),
            )

        self.assertEqual(first["report_sha256"], second["report_sha256"])
        self.assertNotEqual(first["report_sha256"], different["report_sha256"])
        self.assertEqual(first["baseline_sha256"], space.contract["baseline"]["sha256"])
        self.assertEqual(first["contract_sha256"], space.contract["contract_sha256"])


class PhaseExitCodeTests(unittest.TestCase):
    """GREEN 阶段非 green 必须以退出码 3 机械阻断；RED 阶段出现 RED 是预期证据。"""

    def cli_report(self, space: Workspace, phase: str, render: dict, name: str):
        render_path = space.write("render-results.json", render)
        out_path = space.root / name
        code, stdout, _ = run_cli(
            [
                "report",
                "--phase",
                phase,
                *space.contract_args(),
                "--render-results",
                str(render_path),
                "--out",
                str(out_path),
            ]
        )
        return code, json.loads(stdout), out_path

    def test_green_phase_exits_three_for_red_and_yellow_but_still_writes_the_report(self) -> None:
        cases = {
            "red": {"status": "ok", "actual": 99},
            "yellow": {"status": "unavailable", "reason": "空态无法构造"},
        }
        for expected_overall, value in cases.items():
            with self.subTest(overall=expected_overall):
                with tempfile.TemporaryDirectory() as directory:
                    space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
                    code, summary, out_path = self.cli_report(
                        space,
                        "green",
                        space.render({"R1-1": value}),
                        "restore-report-green.json",
                    )
                    written = json.loads(out_path.read_text(encoding="utf-8"))

                self.assertEqual(code, VERIFIER.EXIT_NOT_GREEN)
                self.assertEqual(summary["status"], expected_overall)
                self.assertEqual(written["overall"], expected_overall)
                self.assertEqual(written["phase"], "green")

    def test_red_phase_returns_zero_even_when_the_report_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
            code, summary, out_path = self.cli_report(
                space,
                "red",
                space.render({"R1-1": {"status": "ok", "actual": 99}}),
                "restore-report-red.json",
            )
            written = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(code, VERIFIER.EXIT_OK)
        self.assertEqual(summary["status"], "red")
        self.assertEqual(written["overall"], "red")
        self.assertEqual(written["phase"], "red")

    def test_green_phase_returns_zero_only_when_everything_is_green(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
            code, summary, _ = self.cli_report(
                space,
                "green",
                space.render({"R1-1": {"status": "ok", "actual": 1}}),
                "restore-report-green.json",
            )

        self.assertEqual(code, VERIFIER.EXIT_OK)
        self.assertEqual(summary["status"], "green")
        self.assertEqual(summary["summary"], {"red": 0, "yellow": 0, "green": 1, "total": 1})


class LayerSubstitutionTests(unittest.TestCase):
    """层与层之间不可互相顶替：静态通过不证明渲染，页面不可用不等于失败。"""

    STATIC_RULE = dict(
        expected={"static": "--space-md", "render": "16px"},
        check_mode="numeric",
        layers=["static", "render"],
        static_check={"kind": "token", "value": "--space-md"},
    )

    def build_static_workspace(self, root: Path) -> tuple[Workspace, dict]:
        (root / "src").mkdir(exist_ok=True)
        (root / "src" / "view.tsx").write_text(
            'const gap = "var(--space-md)";',
            encoding="utf-8",
        )
        space = Workspace(root, [make_rule("R3-1", "R3", **self.STATIC_RULE)])
        static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)
        return space, static

    def test_static_pass_without_render_results_is_yellow_not_green(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space, static = self.build_static_workspace(root)
            report = space.report("green", static=static, render=None)

        entry = report["entries"][0]
        self.assertEqual(static["rules"]["R3-1"]["status"], "pass")
        self.assertEqual(entry["status"], "yellow")
        self.assertEqual(report["overall"], "yellow")
        self.assertEqual(entry["reasons"], ["未提供页面能力与结构化渲染结果"])
        self.assertEqual(
            entry["required_evidence"],
            ["启动页面并注入 collect_restore_facts.js，提供结构化渲染结果"],
        )

    def test_page_unavailable_is_yellow_and_capture_error_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space, static = self.build_static_workspace(root)
            unavailable = space.report(
                "red",
                static=static,
                render=space.render({}, page_available=False, reason="dev server 未启动"),
            )
            captured = space.report(
                "red",
                static=static,
                render=space.render({}, capture_error="getComputedStyle 注入失败"),
            )

        self.assertEqual(unavailable["overall"], "yellow")
        self.assertIn("dev server 未启动", unavailable["entries"][0]["reasons"][0])
        self.assertEqual(captured["overall"], "red")
        self.assertEqual(captured["entries"][0]["reasons"], ["结构化渲染已尝试但采集失败"])
        self.assertEqual(
            captured["entries"][0]["actual"]["render"],
            {"capture_error": "getComputedStyle 注入失败"},
        )

    def test_available_page_missing_a_rule_result_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
            available = space.report("red", render=space.render({}))
            # 只有显式 page_available: false 才算页面不可用；漏写字段按「页面可用」处理。
            silent = space.render({})
            silent.pop("page_available")
            unspecified = space.report("red", render=silent)

        self.assertEqual(available["overall"], "red")
        self.assertEqual(
            available["entries"][0]["reasons"],
            ["页面可用但结构化采集缺本规则结果"],
        )
        self.assertEqual(unspecified["overall"], "red")

    def test_visual_check_mode_cannot_also_require_a_render_layer(self) -> None:
        # visual 模式的判定只能来自 visual-results，render 层对它恒判不通过。
        # 这种组合无论视觉补证判什么都永远 RED，所以在编译期就要挡住。
        rule = make_rule(
            "R6-1",
            "R6",
            expected="视觉一致",
            check_mode="visual",
            layers=["render", "visual"],
        )
        with self.assertRaisesRegex(VERIFIER.ContractError, "不能同时要求 render 层"):
            VERIFIER.validate_rule(rule, 1)

    def test_visual_check_mode_without_a_render_layer_is_accepted(self) -> None:
        rule = make_rule(
            "R6-1",
            "R6",
            expected="视觉一致",
            check_mode="visual",
            layers=["visual"],
        )
        self.assertEqual(VERIFIER.validate_rule(rule, 1)["required_layers"], ["visual"])

    def test_expected_payload_named_after_a_layer_is_rejected_at_compile_time(self) -> None:
        # expected 里出现 static/render/visual 键就会被当成分层期望。字面值恰好长成这样时
        # render 层取不到期望值，旧行为是判 RED 而报告里仍显示整个对象，极难排查；
        # 现在编译期就以「render 层 expected 为空」挡下来。
        rule = make_rule(
            "R4-1",
            "R4",
            expected={"visual": "hidden"},
            check_mode="state",
            layers=["render"],
        )
        with self.assertRaisesRegex(VERIFIER.ContractError, "render 层 expected 为空"):
            VERIFIER.validate_rule(rule, 1)

    def test_layer_scoped_expected_still_resolves_per_layer(self) -> None:
        rule = VERIFIER.validate_rule(
            make_rule(
                "R4-1",
                "R4",
                expected={"render": "expanded", "visual": "hidden"},
                check_mode="state",
                layers=["render", "visual"],
            ),
            1,
        )

        self.assertEqual(VERIFIER.expected_for_layer(rule, "render"), "expanded")
        self.assertEqual(VERIFIER.expected_for_layer(rule, "visual"), "hidden")

    def test_missing_static_results_is_red_rather_than_yellow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space, _ = self.build_static_workspace(root)
            report = space.report(
                "red",
                static=None,
                render=space.render({"R3-1": {"status": "ok", "actual": "16px"}}),
            )

        self.assertEqual(report["overall"], "red")
        self.assertEqual(
            report["entries"][0]["reasons"],
            ["静态预检未运行或缺本规则结果"],
        )

    def test_static_only_rule_is_unaffected_by_an_unavailable_page(self) -> None:
        rule = make_rule(
            "R3-1",
            "R3",
            expected="--space-md",
            layers=["static"],
            static_check={"kind": "token", "value": "--space-md"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "view.tsx").write_text("var(--space-md)", encoding="utf-8")
            space = Workspace(root, [rule])
            static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)
            report = space.report(
                "green",
                static=static,
                render=space.render({}, page_available=False, reason="dev server 未启动"),
            )

        self.assertEqual(report["overall"], "green")
        self.assertEqual(report["entries"][0]["verified_layers"], ["static"])

    def test_render_pass_does_not_cover_a_required_visual_layer(self) -> None:
        rule = make_rule("R6-1", "R6", expected=1, layers=["render", "visual"])
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [rule])
            render = space.render({"R6-1": {"status": "ok", "actual": 1}})
            without_visual = space.report("green", render=render)
            with_visual = space.report(
                "green",
                render=render,
                visual=space.results({"R6-1": {"status": "green"}}),
            )

        self.assertEqual(without_visual["overall"], "yellow")
        self.assertEqual(
            without_visual["entries"][0]["required_evidence"],
            ["命中或生成原型视觉缓存，并提供同视口实现截图作选择性视觉补证"],
        )
        self.assertEqual(with_visual["overall"], "green")
        self.assertEqual(with_visual["entries"][0]["verified_layers"], ["render", "visual"])

    def test_visual_results_drive_visual_mode_rules(self) -> None:
        rule = make_rule("R6-1", "R6", expected="视觉一致", check_mode="visual", layers=["visual"])
        cases = {
            "yellow": None,
            "green": {"status": "green"},
            "red": {"status": "red", "reason": "阴影明显偏差"},
            "unknown": {"status": "不认识"},
        }
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [rule])
            for name, item in cases.items():
                visual = None if item is None else space.results({"R6-1": item})
                results[name] = space.report("red", visual=visual)

        self.assertEqual(results["yellow"]["entries"][0]["status"], "yellow")
        self.assertEqual(results["green"]["entries"][0]["status"], "green")
        self.assertEqual(results["red"]["entries"][0]["reasons"], ["阴影明显偏差"])
        self.assertEqual(results["unknown"]["entries"][0]["status"], "red")
        self.assertIn("未知状态", results["unknown"]["entries"][0]["reasons"][0])

    def test_unknown_render_status_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), [make_rule("R1-1", "R1", expected=1)])
            report = space.report(
                "red",
                render=space.render({"R1-1": {"status": "skipped", "actual": 1}}),
            )

        self.assertEqual(report["overall"], "red")
        self.assertIn("未知状态", report["entries"][0]["reasons"][0])

    def test_render_error_status_is_red_while_unavailable_status_is_yellow(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=1),
            make_rule("R2-1", "R2", expected=1),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "red",
                render=space.render(
                    {
                        "R1-1": {"status": "error", "reason": "locator 命中 0 个节点"},
                        "R2-1": {"status": "unavailable", "reason": "该能力当前不可采集"},
                    }
                ),
            )

        self.assertEqual(statuses(report), {"R1-1": "red", "R2-1": "yellow"})

    def test_layer_scoped_expected_values_are_picked_per_layer(self) -> None:
        rule = make_rule(
            "R3-1",
            "R3",
            expected={"static": "--space-md", "render": "16px"},
            check_mode="numeric",
            layers=["static", "render"],
            static_check={"kind": "token", "value": "--space-md"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "view.tsx").write_text("var(--space-md)", encoding="utf-8")
            space = Workspace(root, [rule])
            static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)
            report = space.report(
                "red",
                static=static,
                render=space.render({"R3-1": {"status": "ok", "actual": "24px"}}),
            )

        comparison = report["entries"][0]["actual"]["render"]["comparison"]
        self.assertEqual(VERIFIER.expected_for_layer(space.contract["rules"][0], "render"), "16px")
        self.assertEqual(comparison["differences"][0]["expected"], 16.0)
        self.assertEqual(comparison["differences"][0]["actual"], 24.0)


class ToleranceTests(unittest.TestCase):
    """容差是边界判定，必须钉住「等于容差通过、略超容差失败」。"""

    def compare(self, expected, actual, *, check_mode="numeric", tolerance=1.0):
        rule = {"check_mode": check_mode, "tolerance": {"css_px": tolerance}}
        return VERIFIER.compare_actual(rule, expected, actual)

    def test_default_tolerance_depends_on_check_mode(self) -> None:
        self.assertEqual(VERIFIER.default_tolerance("numeric"), {"css_px": 1.0})
        self.assertEqual(VERIFIER.default_tolerance("overflow"), {"css_px": 1.0})
        self.assertEqual(VERIFIER.default_tolerance("overlap"), {"css_px": 1.0})
        self.assertEqual(VERIFIER.default_tolerance("clip"), {"css_px": 1.0})
        self.assertEqual(VERIFIER.default_tolerance("exact"), {"css_px": 0.0})
        self.assertEqual(VERIFIER.default_tolerance("color"), {"css_px": 0.0})

    def test_rule_without_tolerance_inherits_the_mode_default(self) -> None:
        numeric = VERIFIER.validate_rule(make_rule("R3-1", "R3", expected="16px", check_mode="numeric"), 1)
        exact = VERIFIER.validate_rule(make_rule("R1-1", "R1", expected=1), 1)
        self.assertEqual(numeric["tolerance"], {"css_px": 1.0})
        self.assertEqual(exact["tolerance"], {"css_px": 0.0})

    def test_numeric_boundary_passes_at_tolerance_and_fails_just_above(self) -> None:
        for actual, expected_pass in (("17px", True), ("15px", True), ("17.01px", False), ("14.99px", False)):
            with self.subTest(actual=actual):
                passed, detail = self.compare("16px", actual)
                self.assertEqual(passed, expected_pass)
                self.assertEqual(detail["tolerance_css_px"], 1.0)

    def test_numeric_boundary_holds_inside_nested_structures(self) -> None:
        expected = {"gap": "16px", "padding": [8, 8]}
        passed, _ = self.compare(expected, {"gap": 17, "padding": ["9px", 7]})
        self.assertTrue(passed)
        failed, detail = self.compare(expected, {"gap": 17, "padding": ["9.5px", 7]})
        self.assertFalse(failed)
        self.assertEqual(
            [item["path"] for item in detail["differences"] if item["delta"] > 1.0],
            ["$.padding[0]"],
        )

    def test_missing_and_non_numeric_values_never_slip_through_tolerance(self) -> None:
        missing, detail = self.compare({"gap": "16px"}, {})
        self.assertFalse(missing)
        self.assertEqual(detail["differences"], [{"path": "$.gap", "reason": "missing"}])

        text, detail = self.compare("16px", "auto")
        self.assertFalse(text)
        self.assertEqual(detail["differences"][0]["reason"], "not-numeric")

        length, detail = self.compare([1, 2], [1])
        self.assertFalse(length)
        self.assertEqual(detail["differences"][0]["reason"], "length")

    def test_overflow_family_uses_tolerance_as_an_upper_threshold(self) -> None:
        for mode in ("overflow", "overlap", "clip"):
            with self.subTest(mode=mode):
                self.assertTrue(self.compare(0, 1.0, check_mode=mode)[0])
                self.assertTrue(self.compare(0, {"x": 0.4, "y": [1, 0.2]}, check_mode=mode)[0])
                self.assertFalse(self.compare(0, 1.0001, check_mode=mode)[0])
                self.assertFalse(self.compare(0, {"x": 0.4, "y": [1.5]}, check_mode=mode)[0])

    def test_empty_expectations_would_pass_trivially_if_they_got_this_far(self) -> None:
        # 比对层对空期望值无条件判通过：numeric 产生不出差异项，overflow 家族对空容器取 0。
        # 这是下一条测试为什么必须在编译期拦住空 expected——拦不住就是自动染绿。
        self.assertTrue(self.compare({}, {"gap": 999})[0])
        self.assertTrue(self.compare([], [])[0])
        self.assertTrue(self.compare(0, {}, check_mode="overflow")[0])

    def test_empty_render_expectations_are_rejected_at_compile_time(self) -> None:
        for expected in ({}, [], "", None):
            with self.subTest(expected=expected):
                rule = make_rule("R3-1", "R3", expected=expected, check_mode="numeric")
                with self.assertRaisesRegex(VERIFIER.ContractError, "render 层 expected 为空"):
                    VERIFIER.validate_rule(rule, 1)

    def test_zero_is_a_legal_expectation(self) -> None:
        # 间距 0px、计数 0 都是正当期望值，不能被空值检查误伤。
        rule = make_rule("R3-1", "R3", expected=0, check_mode="numeric")
        self.assertEqual(VERIFIER.validate_rule(rule, 1)["expected"], 0)

    def test_zero_tolerance_modes_require_exact_equality(self) -> None:
        self.assertTrue(self.compare(16, 16, check_mode="exact", tolerance=0.0)[0])
        self.assertFalse(self.compare(16, 16.5, check_mode="exact", tolerance=0.0)[0])
        self.assertFalse(self.compare("16px", 16, check_mode="exact", tolerance=0.0)[0])

    def test_color_mode_treats_equivalent_css_syntaxes_as_equal(self) -> None:
        # 同一红色的多种写法必须归一化后判 GREEN；否则采集端输出 rgb()、契约写 hex
        # 就会假红。
        equivalents = ("#ff0000", "#FF0000", "rgb(255, 0, 0)", "rgba(255,0,0,1)", "#f00")
        for expected in equivalents:
            for actual in equivalents:
                with self.subTest(expected=expected, actual=actual):
                    passed, detail = self.compare(expected, actual, check_mode="color", tolerance=0.0)
                    self.assertTrue(passed)
                    self.assertEqual(detail["expected"], detail["actual"])

    def test_color_mode_rejects_real_channel_or_alpha_differences(self) -> None:
        self.assertFalse(self.compare("#ff0000", "#ff0001", check_mode="color", tolerance=0.0)[0])
        self.assertFalse(
            self.compare("#ff0000", "rgba(255,0,0,0.9)", check_mode="color", tolerance=0.0)[0]
        )

    def test_unrecognized_color_strings_fail_deterministically(self) -> None:
        # 无法识别时回退到去空白后的原文比较：拼写错误名与合法色值必然不相等，且不得崩溃。
        passed, detail = self.compare("#ff0000", "reed", check_mode="color", tolerance=0.0)
        self.assertFalse(passed)
        self.assertEqual(detail["actual"], "reed")
        self.assertNotEqual(detail["expected"], detail["actual"])

    def test_boundary_decides_the_report_color(self) -> None:
        rules = [
            make_rule("R3-1", "R3", expected="16px", check_mode="numeric"),
            make_rule("R3-2", "R3", expected="16px", check_mode="numeric"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report(
                "green",
                render=space.render(
                    {
                        "R3-1": {"status": "ok", "actual": "17px"},
                        "R3-2": {"status": "ok", "actual": "17.5px"},
                    }
                ),
            )

        self.assertEqual(statuses(report), {"R3-1": "green", "R3-2": "red"})

    def test_negative_or_malformed_tolerance_is_rejected(self) -> None:
        with self.assertRaisesRegex(VERIFIER.ContractError, "tolerance.css_px 必须是非负数"):
            VERIFIER.validate_rule(make_rule("R3-1", "R3", tolerance={"css_px": -1}), 1)
        with self.assertRaisesRegex(VERIFIER.ContractError, "tolerance 必须是对象"):
            VERIFIER.validate_rule(make_rule("R3-1", "R3", tolerance=[1]), 1)


class ContractRuleMappingTests(unittest.TestCase):
    """契约、基线与 adapter 之间的对应关系。"""

    def test_every_contract_rule_needs_an_adapter_entry(self) -> None:
        rules = [make_rule("R1-1", "R1"), make_rule("R2-1", "R2")]
        adapter = default_adapter(rules)
        adapter["rules"].pop("R2-1")
        with tempfile.TemporaryDirectory() as directory:
            baseline, draft = self.build(Path(directory), rules, ["R1-1", "R2-1"])
            full = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            self.assertEqual(len(full["rules"]), 2)
            with self.assertRaisesRegex(VERIFIER.ContractError, "adapter 缺规则 R2-1"):
                VERIFIER.validate_adapter(adapter, full)

    def test_extra_adapter_entries_are_rejected(self) -> None:
        # 契约改了而 adapter 没跟着改时，多出来的条目静默消失会让人以为它还在生效。
        rules = [make_rule("R1-1", "R1")]
        adapter = default_adapter(rules)
        adapter["rules"]["R9-9"] = {
            "locators": [{"strategy": "testid", "testid": "ghost"}],
            "source_files": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": rules}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            with self.assertRaisesRegex(VERIFIER.ContractError, "R9-9"):
                VERIFIER.validate_adapter(adapter, contract)

    def test_adapter_entry_for_an_exempted_rule_is_tolerated(self) -> None:
        # 命中冻结豁免的规则不需要实现定位，但留着旧条目不算错配。
        exempted = make_rule("R1-1", "R1", exemption={"id": "EX-1", "frozen": True})
        adapter = {
            "schema_version": 1,
            "rules": {
                "R1-1": {
                    "locators": [{"strategy": "testid", "testid": "legacy"}],
                    "source_files": [],
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": [exempted]}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            self.assertEqual(VERIFIER.validate_adapter(adapter, contract)["rules"], {})

    def build(self, root: Path, rules: list[dict], baseline_ids: list[str]) -> tuple[Path, Path]:
        baseline = root / "dev-baseline.md"
        baseline.write_text(frozen_baseline(baseline_ids), encoding="utf-8")
        draft = root / "rules-draft.json"
        draft.write_text(json.dumps({"rules": rules}, ensure_ascii=False), encoding="utf-8")
        return baseline, draft

    def test_baseline_id_absent_from_the_baseline_is_rejected(self) -> None:
        # 基线哈希只锁住文档本身。不回查正文的话，指向一条根本不存在的基线行也算合法契约。
        rules = [make_rule("R1-1", "R1", baseline_id="R1-999")]
        with tempfile.TemporaryDirectory() as directory:
            baseline, draft = self.build(Path(directory), rules, ["R1-1"])
            with self.assertRaisesRegex(VERIFIER.ContractError, "R1-999"):
                VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

    def test_baseline_row_without_a_rule_is_rejected(self) -> None:
        # 漏覆盖比错引更隐蔽：契约全绿了，基线里那条却从没被判过。
        rules = [make_rule("R1-1", "R1")]
        with tempfile.TemporaryDirectory() as directory:
            baseline, draft = self.build(Path(directory), rules, ["R1-1", "R3-1"])
            with self.assertRaisesRegex(VERIFIER.ContractError, "R3-1"):
                VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

    def test_not_applicable_baseline_rows_need_no_rule(self) -> None:
        rules = [make_rule("R1-1", "R1")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, draft = self.build(root, rules, ["R1-1"])
            baseline.write_text(
                baseline.read_text(encoding="utf-8") + "| R4-1 | R4 | — | 不适用：文字规格未给状态样式 |\n",
                encoding="utf-8",
            )
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

        self.assertEqual([rule["baseline_id"] for rule in contract["rules"]], ["R1-1"])

    def test_baseline_mapping_is_rechecked_at_validate_time(self) -> None:
        # 契约与基线各自落盘，只在编译期查一次挡不住事后改基线。
        rules = [make_rule("R1-1", "R1")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, rules)
            widened = frozen_baseline(["R1-1", "R3-1"])
            space.baseline_path.write_text(widened, encoding="utf-8")
            rewritten = json.loads(json.dumps(space.contract))
            rewritten["baseline"]["sha256"] = VERIFIER.sha256_file(space.baseline_path)
            core = {
                "schema_version": rewritten["schema_version"],
                "baseline": rewritten["baseline"],
                "rules": rewritten["rules"],
            }
            rewritten["contract_sha256"] = VERIFIER.sha256_text(VERIFIER.canonical_json(core))

            with self.assertRaisesRegex(VERIFIER.ContractError, "R3-1"):
                VERIFIER.validate_contract(rewritten, space.baseline_path)

    def test_recompiling_over_a_changed_baseline_needs_reconfirmation(self) -> None:
        rules = [make_rule("R1-1", "R1")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, draft = self.build(root, rules, ["R1-1"])
            out_path = root / "restore-contract.json"
            argv = [
                "contract",
                "--baseline", str(baseline),
                "--baseline-ref", "dev-baseline.md",
                "--rules", str(draft),
                "--out", str(out_path),
            ]
            self.assertEqual(run_cli(argv)[0], VERIFIER.EXIT_OK)
            first = out_path.read_text(encoding="utf-8")

            baseline.write_text(
                baseline.read_text(encoding="utf-8").replace("见规则", "见规则（放宽）"),
                encoding="utf-8",
            )
            code, _, stderr = run_cli(argv)

            self.assertEqual(code, VERIFIER.EXIT_ERROR)
            self.assertIn("--after-reconfirmation", stderr)
            self.assertEqual(out_path.read_text(encoding="utf-8"), first)

            self.assertEqual(run_cli([*argv, "--after-reconfirmation"])[0], VERIFIER.EXIT_OK)
            self.assertNotEqual(out_path.read_text(encoding="utf-8"), first)

    def test_recompiling_an_unchanged_baseline_stays_idempotent(self) -> None:
        rules = [make_rule("R1-1", "R1")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, draft = self.build(root, rules, ["R1-1"])
            out_path = root / "restore-contract.json"
            argv = [
                "contract",
                "--baseline", str(baseline),
                "--baseline-ref", "dev-baseline.md",
                "--rules", str(draft),
                "--out", str(out_path),
            ]
            self.assertEqual(run_cli(argv)[0], VERIFIER.EXIT_OK)
            first = out_path.read_text(encoding="utf-8")
            self.assertEqual(run_cli(argv)[0], VERIFIER.EXIT_OK)

            self.assertEqual(out_path.read_text(encoding="utf-8"), first)

    def test_duplicate_rule_ids_are_rejected_even_with_a_recomputed_hash(self) -> None:
        # 契约是落盘文件，自哈希连同重算就绕过去了，所以 validate 必须自己再查一遍唯一性。
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            forged = json.loads(json.dumps(space.contract))
            forged["rules"].append(json.loads(json.dumps(forged["rules"][0])))
            core = {
                "schema_version": forged["schema_version"],
                "baseline": forged["baseline"],
                "rules": forged["rules"],
            }
            forged["contract_sha256"] = VERIFIER.sha256_text(VERIFIER.canonical_json(core))

            with self.assertRaisesRegex(VERIFIER.ContractError, "规则 id 必须唯一"):
                VERIFIER.validate_contract(forged, space.baseline_path)

    def test_duplicate_rule_ids_are_rejected_at_compile_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(
                json.dumps({"rules": [make_rule("R1-1", "R1"), make_rule("R1-1", "R1")]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VERIFIER.ContractError, "规则 id 必须唯一"):
                VERIFIER.compile_contract(baseline, draft)

    def test_denormalized_contract_rules_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            handwritten = json.loads(json.dumps(space.contract))
            handwritten["rules"][0].pop("state_scenario")
            core = {
                "schema_version": handwritten["schema_version"],
                "baseline": handwritten["baseline"],
                "rules": handwritten["rules"],
            }
            handwritten["contract_sha256"] = VERIFIER.sha256_text(VERIFIER.canonical_json(core))

            with self.assertRaisesRegex(VERIFIER.ContractError, "未规范化"):
                VERIFIER.validate_contract(handwritten, space.baseline_path)

    def test_adapter_locators_must_follow_the_priority_order(self) -> None:
        rules = [make_rule("R1-1", "R1")]
        adapter = default_adapter(rules)
        adapter["rules"]["R1-1"]["locators"] = [
            {"strategy": "css", "selector": ".filters"},
            {"strategy": "role", "role": "button", "name": "保存"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": rules}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            with self.assertRaisesRegex(VERIFIER.ContractError, "locator 优先级"):
                VERIFIER.validate_adapter(adapter, contract)

    def test_incomplete_locators_are_rejected(self) -> None:
        rules = [make_rule("R1-1", "R1")]
        broken = {
            "role 缺 name": {"strategy": "role", "role": "button"},
            "text 缺文案": {"strategy": "text"},
            "testid 缺 testid": {"strategy": "testid"},
            "css 缺 selector": {"strategy": "css"},
            "未知策略": {"strategy": "xpath", "value": "//div"},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": rules}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            for name, locator in broken.items():
                with self.subTest(case=name):
                    adapter = default_adapter(rules)
                    adapter["rules"]["R1-1"]["locators"] = [locator]
                    with self.assertRaises(VERIFIER.ContractError):
                        VERIFIER.validate_adapter(adapter, contract)

            empty = default_adapter(rules)
            empty["rules"]["R1-1"]["locators"] = []
            with self.assertRaisesRegex(VERIFIER.ContractError, "locators 必须是非空数组"):
                VERIFIER.validate_adapter(empty, contract)

    def test_nested_judgment_fields_inside_adapter_are_rejected(self) -> None:
        # 判定字段藏在 collect / locators 嵌套对象里时，浅层检查会漏掉——那正是实现方
        # 绕过冻结契约期望值的路径。
        rules = [make_rule("R3-1", "R3", expected="16px", check_mode="numeric")]
        cases = {
            "collect.expected": {
                "kind": "style",
                "properties": ["gap"],
                "expected": "16px",
            },
            "collect.tolerance": {
                "kind": "style",
                "properties": ["gap"],
                "tolerance": {"css_px": 0},
            },
            "locator.baseline_id": None,
            "locator.design_fact_source": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R3-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": rules}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            for name, collect in cases.items():
                with self.subTest(case=name):
                    adapter = default_adapter(rules)
                    if name.startswith("collect."):
                        adapter["rules"]["R3-1"]["collect"] = collect
                    elif name == "locator.baseline_id":
                        adapter["rules"]["R3-1"]["locators"][0]["baseline_id"] = "R3-1"
                    else:
                        adapter["rules"]["R3-1"]["locators"][0]["design_fact_source"] = {
                            "path": "design-facts.json"
                        }
                    with self.assertRaisesRegex(
                        VERIFIER.ContractError,
                        r"adapter 混入外部判定字段：.*(?:expected|tolerance|baseline_id|design_fact_source)",
                    ):
                        VERIFIER.validate_adapter(adapter, contract)

    def test_legal_adapter_fields_are_not_treated_as_judgment_keys(self) -> None:
        # 递归检查只认字典 key，不能误杀 properties 数组里碰巧含 "expected" 的字符串。
        rules = [make_rule("R3-1", "R3", expected="16px", check_mode="numeric")]
        adapter = default_adapter(rules)
        adapter["rules"]["R3-1"] = {
            "locators": [
                {
                    "strategy": "role",
                    "role": "button",
                    "name": "R3-1",
                },
                {
                    "strategy": "testid",
                    "testid": "filters-expected",
                },
                {
                    "strategy": "css",
                    "selector": ".filters",
                },
            ],
            "source_files": ["src/view.tsx"],
            "collect": {
                "kind": "style",
                "properties": ["gap", "expected-size", "tolerance-hint"],
                "attributes": ["data-state", "aria-expected"],
                "single": True,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R3-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps({"rules": rules}), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

            normalized = VERIFIER.validate_adapter(adapter, contract)

        self.assertEqual(
            normalized["rules"]["R3-1"]["collect"]["properties"],
            ["gap", "expected-size", "tolerance-hint"],
        )

    def test_dimension_check_mode_and_layer_vocabulary_are_closed(self) -> None:
        cases = {
            "R7": (make_rule("X-1", "R7"), "dimension 必须是 R1–R6"),
            "check_mode": (make_rule("X-1", "R1", check_mode="vibes"), "check_mode 不支持"),
            "layer": (make_rule("X-1", "R1", layers=["a11y"]), "未知检查层"),
            "empty_layers": (make_rule("X-1", "R1", layers=[]), "required_layers 必须是非空数组"),
            "visual_layer": (
                make_rule("X-1", "R1", check_mode="visual", layers=["render"]),
                "visual 模式必须要求 visual 层",
            ),
            "static_check": (
                make_rule("X-1", "R3", layers=["static"]),
                "要求 static 层但没有 static_check",
            ),
        }
        for name, (rule, message) in cases.items():
            with self.subTest(case=name):
                with self.assertRaisesRegex(VERIFIER.ContractError, message):
                    VERIFIER.validate_rule(rule, 1)

    def test_default_layers_apply_when_a_rule_omits_them(self) -> None:
        for dimension, layers in VERIFIER.DEFAULT_LAYERS.items():
            with self.subTest(dimension=dimension):
                rule = make_rule("X-1", dimension, static_check={"kind": "text", "value": "保存"})
                rule.pop("required_layers")
                self.assertEqual(VERIFIER.validate_rule(rule, 1)["required_layers"], layers)


class FrozenExemptionTests(unittest.TestCase):
    """只有冻结过的豁免才能顶替证据，其余一律照常判定。"""

    def test_frozen_exemption_is_green_without_any_evidence(self) -> None:
        rules = [
            make_rule(
                "R2-1",
                "R2",
                expected="保存",
                exemption={"id": "EX-2", "frozen": True, "reason": "平台能力限制"},
            )
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report("green")

        entry = report["entries"][0]
        self.assertEqual(report["overall"], "green")
        self.assertEqual(entry["status"], "green")
        self.assertEqual(entry["frozen_exemption"]["id"], "EX-2")
        self.assertEqual(entry["verified_layers"], [])
        self.assertEqual(entry["implementation_locator"], {"exempt": True})

    def test_unfrozen_or_unnamed_exemptions_cannot_enter_the_contract(self) -> None:
        cases = {
            "未冻结": ({"id": "EX-3", "frozen": False}, "豁免未冻结"),
            "缺 frozen": ({"id": "EX-3"}, "豁免未冻结"),
            "缺 id": ({"frozen": True}, "frozen_exemption 缺 id"),
            "不是对象": ("EX-3", "frozen_exemption 缺 id"),
        }
        for name, (exemption, message) in cases.items():
            with self.subTest(case=name):
                with self.assertRaisesRegex(VERIFIER.ContractError, message):
                    VERIFIER.validate_rule(
                        make_rule("R2-1", "R2", exemption=exemption),
                        1,
                    )

    def test_a_rule_without_an_exemption_still_needs_its_layers(self) -> None:
        rules = [
            make_rule("R1-1", "R1", expected=1),
            make_rule(
                "R2-1",
                "R2",
                expected="保存",
                exemption={"id": "EX-2", "frozen": True, "reason": "平台能力限制"},
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            space = Workspace(Path(directory), rules)
            report = space.report("green")

        self.assertEqual(statuses(report), {"R1-1": "yellow", "R2-1": "green"})
        self.assertEqual(report["overall"], "yellow")

    def test_exempt_rules_are_skipped_by_adapter_and_static_preflight(self) -> None:
        rules = [
            make_rule(
                "R3-1",
                "R3",
                expected="--space-md",
                layers=["static"],
                static_check={"kind": "token", "value": "--space-md"},
                exemption={"id": "EX-4", "frozen": True, "reason": "第三方组件"},
            ),
            make_rule(
                "R3-2",
                "R3",
                expected="--space-lg",
                layers=["static"],
                static_check={"kind": "token", "value": "--space-lg"},
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "view.tsx").write_text("var(--space-lg)", encoding="utf-8")
            space = Workspace(root, rules)
            static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)

        self.assertEqual(set(space.adapter["rules"]), {"R3-2"})
        self.assertEqual(set(static["rules"]), {"R3-2"})


class StaticPreflightTests(unittest.TestCase):
    """静态预检只回答「源码里在不在」，其余状态一律进 RED。"""

    def preflight(self, root: Path, rule: dict, source: str, source_files=None) -> dict:
        (root / "src").mkdir(exist_ok=True)
        (root / "src" / "view.tsx").write_text(source, encoding="utf-8")
        space = Workspace(root, [rule], source_files=source_files)
        return VERIFIER.run_static_preflight(space.contract, space.adapter, root)

    def test_value_kinds_pass_only_when_the_needle_is_present(self) -> None:
        for kind in ("text", "i18n_key", "token", "state_selector"):
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    rule = make_rule(
                        "R3-1",
                        "R3",
                        expected="保存",
                        layers=["static"],
                        static_check={"kind": kind, "value": "保存"},
                    )
                    hit = self.preflight(root, rule, '<button>保存</button>')
                    miss = self.preflight(root, rule, '<button>提交</button>')

                self.assertEqual(hit["rules"]["R3-1"]["status"], "pass")
                self.assertEqual(
                    hit["rules"]["R3-1"]["actual"]["matching_files"],
                    ["src/view.tsx"],
                )
                self.assertEqual(miss["rules"]["R3-1"]["status"], "fail")

    def test_regex_and_forbidden_literal_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regex_rule = make_rule(
                "R3-1",
                "R3",
                expected="pattern",
                layers=["static"],
                static_check={"kind": "regex", "pattern": r"data-state=\"loading\""},
            )
            matched = self.preflight(root, regex_rule, '<div data-state="loading" />')
            broken = self.preflight(
                root,
                make_rule(
                    "R3-1",
                    "R3",
                    expected="pattern",
                    layers=["static"],
                    static_check={"kind": "regex", "pattern": "["},
                ),
                "whatever",
            )
            forbidden = self.preflight(
                root,
                make_rule(
                    "R3-1",
                    "R3",
                    expected="none",
                    layers=["static"],
                    static_check={"kind": "forbidden_literals", "values": ["#ff0000"]},
                ),
                "color: #ff0000;",
            )
            unsupported = self.preflight(
                root,
                make_rule(
                    "R3-1",
                    "R3",
                    expected="none",
                    layers=["static"],
                    static_check={"kind": "screenshot"},
                ),
                "whatever",
            )

        self.assertEqual(matched["rules"]["R3-1"]["status"], "pass")
        self.assertEqual(broken["rules"]["R3-1"]["status"], "error")
        self.assertIn("regex 无效", broken["rules"]["R3-1"]["reason"])
        self.assertEqual(forbidden["rules"]["R3-1"]["status"], "fail")
        self.assertEqual(
            forbidden["rules"]["R3-1"]["actual"]["forbidden_hits"],
            [{"file": "src/view.tsx", "value": "#ff0000"}],
        )
        self.assertEqual(unsupported["rules"]["R3-1"]["status"], "error")
        self.assertIn("不支持的 static_check.kind", unsupported["rules"]["R3-1"]["reason"])

    def test_static_check_without_a_matching_source_file_is_an_error_then_red(self) -> None:
        rule = make_rule(
            "R3-1",
            "R3",
            expected="保存",
            layers=["static"],
            static_check={"kind": "text", "value": "保存"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [rule], source_files=["src/does-not-exist.tsx"])
            static = VERIFIER.run_static_preflight(space.contract, space.adapter, root)
            report = space.report("red", static=static)

        self.assertEqual(static["rules"]["R3-1"]["status"], "error")
        self.assertEqual(report["overall"], "red")
        self.assertEqual(
            report["entries"][0]["reasons"],
            ["没有命中任何 source_files"],
        )

    def test_source_files_cannot_escape_the_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "secret.env").write_text("TOKEN=1", encoding="utf-8")
            repo = root / "repo"
            repo.mkdir()
            with self.assertRaisesRegex(VERIFIER.ContractError, "越出 repo-root"):
                VERIFIER.resolve_source_files(repo, ["../secret.env"])

    def test_static_results_are_fingerprinted_against_the_contract(self) -> None:
        rule = make_rule(
            "R3-1",
            "R3",
            expected="保存",
            layers=["static"],
            static_check={"kind": "text", "value": "保存"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "view.tsx").write_text("保存", encoding="utf-8")
            space = Workspace(root, [rule])
            out_path = root / "static-results.json"
            code, stdout, _ = run_cli(
                [
                    "static",
                    *space.contract_args(),
                    "--repo-root",
                    str(root),
                    "--out",
                    str(out_path),
                ]
            )
            written = json.loads(out_path.read_text(encoding="utf-8"))
            foreign = dict(written, contract_sha256="0" * 64)
            foreign_path = space.write("foreign-static.json", foreign)
            mismatch_code, _, mismatch_err = run_cli(
                [
                    "report",
                    "--phase",
                    "red",
                    *space.contract_args(),
                    "--static-results",
                    str(foreign_path),
                    "--out",
                    str(root / "restore-report-red.json"),
                ]
            )

        self.assertEqual(code, VERIFIER.EXIT_OK)
        self.assertEqual(json.loads(stdout)["rules"], 1)
        self.assertEqual(written["contract_sha256"], space.contract["contract_sha256"])
        self.assertEqual(written["rules"]["R3-1"]["status"], "pass")
        self.assertEqual(mismatch_code, VERIFIER.EXIT_ERROR)
        self.assertIn("contract_sha256 与冻结契约不一致", mismatch_err)


class MalformedInputTests(unittest.TestCase):
    """畸形输入必须走报错路径，不能静默产出报告。"""

    def test_contract_command_writes_the_compiled_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(
                json.dumps({"rules": [make_rule("R1-1", "R1")]}, ensure_ascii=False),
                encoding="utf-8",
            )
            out_path = root / "restore-contract.json"
            code, stdout, _ = run_cli(
                [
                    "contract",
                    "--baseline",
                    str(baseline),
                    "--baseline-ref",
                    "dev-baseline.md",
                    "--rules",
                    str(draft),
                    "--out",
                    str(out_path),
                ]
            )
            written = json.loads(out_path.read_text(encoding="utf-8"))
            summary = json.loads(stdout)

        self.assertEqual(code, VERIFIER.EXIT_OK)
        self.assertEqual(summary["rules"], 1)
        self.assertEqual(summary["contract_sha256"], written["contract_sha256"])
        self.assertEqual(written["baseline"]["path"], "dev-baseline.md")
        self.assertEqual(written["schema_version"], VERIFIER.CONTRACT_SCHEMA_VERSION)

    def test_unparsable_json_is_reported_per_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            broken = root / "broken.json"
            broken.write_text("{不是 JSON", encoding="utf-8")

            commands = {
                "contract": [
                    "contract",
                    "--baseline",
                    str(space.baseline_path),
                    "--rules",
                    str(broken),
                    "--out",
                    str(root / "out.json"),
                ],
                "validate-contract": [
                    "validate",
                    "--baseline",
                    str(space.baseline_path),
                    "--contract",
                    str(broken),
                    "--adapter",
                    str(space.adapter_path),
                ],
                "validate-adapter": [
                    "validate",
                    "--baseline",
                    str(space.baseline_path),
                    "--contract",
                    str(space.contract_path),
                    "--adapter",
                    str(broken),
                ],
                "report-results": [
                    "report",
                    "--phase",
                    "red",
                    *space.contract_args(),
                    "--render-results",
                    str(broken),
                    "--out",
                    str(root / "report.json"),
                ],
            }
            for name, argv in commands.items():
                with self.subTest(command=name):
                    code, _, stderr = run_cli(argv)
                    self.assertEqual(code, VERIFIER.EXIT_ERROR)
                    self.assertIn("JSON 无法解析", stderr)
            self.assertFalse((root / "report.json").exists())

    def test_missing_files_are_reported_per_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])
            ghost = root / "ghost.json"

            commands = {
                "contract-baseline": (
                    [
                        "contract",
                        "--baseline",
                        str(root / "ghost.md"),
                        "--rules",
                        str(space.draft_path),
                        "--out",
                        str(root / "out.json"),
                    ],
                    "ghost.md",
                ),
                "contract-rules": (
                    [
                        "contract",
                        "--baseline",
                        str(space.baseline_path),
                        "--rules",
                        str(ghost),
                        "--out",
                        str(root / "out.json"),
                    ],
                    "文件不存在",
                ),
                "validate-contract": (
                    [
                        "validate",
                        "--baseline",
                        str(space.baseline_path),
                        "--contract",
                        str(ghost),
                        "--adapter",
                        str(space.adapter_path),
                    ],
                    "文件不存在",
                ),
                "report-render": (
                    [
                        "report",
                        "--phase",
                        "green",
                        *space.contract_args(),
                        "--render-results",
                        str(ghost),
                        "--out",
                        str(root / "report.json"),
                    ],
                    "文件不存在",
                ),
                "evidence-format": (
                    ["evidence-format", "--alpha-tests", str(root / "ghost.md")],
                    "ghost.md",
                ),
            }
            for name, (argv, fragment) in commands.items():
                with self.subTest(command=name):
                    code, _, stderr = run_cli(argv)
                    self.assertEqual(code, VERIFIER.EXIT_ERROR)
                    self.assertIn(fragment, stderr)

    def test_missing_required_rule_fields_are_named(self) -> None:
        rule = make_rule("R1-1", "R1", drop=("expected", "design_fact_source"))
        with self.assertRaises(VERIFIER.ContractError) as caught:
            VERIFIER.validate_rule(rule, 1)
        message = str(caught.exception)
        self.assertIn("expected", message)
        self.assertIn("design_fact_source", message)

        with self.assertRaisesRegex(VERIFIER.ContractError, "必须是对象"):
            VERIFIER.validate_rule(["R1-1"], 1)
        with self.assertRaisesRegex(VERIFIER.ContractError, "id 为空"):
            VERIFIER.validate_rule(make_rule(" ", "R1"), 1)

    def test_structurally_wrong_top_level_payloads_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            space = Workspace(root, [make_rule("R1-1", "R1")])

            with self.assertRaisesRegex(VERIFIER.ContractError, "非空数组"):
                VERIFIER.compile_contract(
                    space.baseline_path,
                    space.write("empty.json", {"rules": []}),
                )
            with self.assertRaisesRegex(VERIFIER.ContractError, "顶层必须是对象"):
                VERIFIER.validate_contract(["not", "a", "contract"], space.baseline_path)
            with self.assertRaisesRegex(VERIFIER.ContractError, "schema_version 必须为 2"):
                VERIFIER.validate_contract(
                    dict(space.contract, schema_version=1),
                    space.baseline_path,
                )
            with self.assertRaisesRegex(VERIFIER.ContractError, "缺 baseline.sha256"):
                VERIFIER.validate_contract(
                    dict(space.contract, baseline={}),
                    space.baseline_path,
                )
            with self.assertRaisesRegex(VERIFIER.ContractError, "adapter schema_version 必须为 1"):
                VERIFIER.validate_adapter({"schema_version": 2, "rules": {}}, space.contract)
            with self.assertRaisesRegex(VERIFIER.ContractError, "adapter.rules 必须是对象"):
                VERIFIER.validate_adapter({"schema_version": 1, "rules": []}, space.contract)
            with self.assertRaisesRegex(VERIFIER.ContractError, "顶层必须是对象"):
                VERIFIER.result_rules([], "render-results", space.contract["contract_sha256"])

    def test_rules_may_be_a_bare_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text(frozen_baseline(["R1-1"]), encoding="utf-8")
            draft = root / "rules-draft.json"
            draft.write_text(json.dumps([make_rule("R1-1", "R1")]), encoding="utf-8")
            contract = VERIFIER.compile_contract(baseline, draft, "dev-baseline.md")

        self.assertEqual(len(contract["rules"]), 1)

    def test_evidence_format_recognizes_all_three_shapes(self) -> None:
        legacy = "## 还原证据记录\n\n**RED 双方截图**\n\n**GREEN 复核**\n"
        machine = "## 还原证据记录\n\n路径：restore-report-green.json\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = {}
            for name, body in (
                ("legacy-screenshot-v1", legacy),
                ("machine-v2", machine),
                ("none", "## Alpha 测试\n\n还没有任何还原证据。\n"),
            ):
                path = root / f"{name}.md"
                path.write_text(body, encoding="utf-8")
                code, stdout, _ = run_cli(["evidence-format", "--alpha-tests", str(path)])
                outputs[name] = (code, json.loads(stdout))

        for name, (code, payload) in outputs.items():
            with self.subTest(case=name):
                self.assertEqual(code, VERIFIER.EXIT_OK)
                self.assertEqual(payload["format"], name)


if __name__ == "__main__":
    unittest.main()
