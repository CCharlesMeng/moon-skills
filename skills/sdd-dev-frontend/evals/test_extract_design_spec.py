#!/usr/bin/env python3
"""Regression tests for the deterministic prototype preprocessor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = EVAL_DIR.parent / "scripts" / "extract_design_spec.py"
VERIFIER_PATH = EVAL_DIR.parent / "scripts" / "verify_restore_contract.py"

MAX_TOTAL_ARTIFACT_CHARS = 65_000
MAX_SINGLE_ARTIFACT_CHARS = 45_000
MAX_BLOCK_SLICE_CHARS = 12_000


def load_extractor():
    spec = importlib.util.spec_from_file_location("extract_design_spec", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXTRACTOR = load_extractor()


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_restore_contract", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_verifier()


class SampleRegressionTests(unittest.TestCase):
    maxDiff = None

    # `element_nodes` 只数 body 内参与结构签名的非 void 元素，不含 html/body；
    # `patterns` 使用精确 tag+class 签名，变体族只提示归并候选，不混入覆盖率。
    CASES = {
        "设计稿原型-标准版.html": {
            "chars": 55_697,
            "lines": 1_316,
            "formatted": True,
            "doc_hash": "1d4be3ff",
            "css_rules": 164,
            "class_rules": 162,
            "token_mode": "shared-class",
            "token_classes": 20,
            "layout_classes": 142,
            "colors": 15,
            "font_sizes": 6,
            "assets": 33,
            "assets_missing": 33,
            "element_nodes": 374,
            "void_nodes": 0,
            "text_nodes": 226,
            "text_unique": 78,
            "blocks": 21,
            "block_max_nodes": 39,
            "patterns": 3,
            "pattern_covered_nodes": 192,
            "pattern_coverage_pct": 51.3,
        },
        "原型-客户风险简报.html": {
            "chars": 415_398,
            "lines": 5_391,
            "formatted": True,
            "doc_hash": "a3e5504f",
            "css_rules": 365,
            "class_rules": 363,
            "token_mode": "shared-class",
            "token_classes": 46,
            "layout_classes": 317,
            "colors": 29,
            "font_sizes": 9,
            "assets": 53,
            "assets_missing": 53,
            "element_nodes": 2_851,
            "void_nodes": 86,
            "text_nodes": 1_922,
            "text_unique": 122,
            "blocks": 150,
            "block_max_nodes": 109,
            "patterns": 15,
            "pattern_covered_nodes": 1_883,
            "pattern_coverage_pct": 66.0,
        },
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.results = {
            filename: EXTRACTOR.extract(EVAL_DIR / filename, "auto", 80, 2, 2)
            for filename in cls.CASES
        }

    def test_sample_metrics_are_stable(self) -> None:
        for filename, expected in self.CASES.items():
            with self.subTest(filename=filename):
                actual = EXTRACTOR.stats(self.results[filename])
                self.assertEqual(
                    {key: actual[key] for key in expected},
                    expected,
                )

    def test_unformatted_single_line_export_yields_identical_facts(self) -> None:
        # 设计工具常导出成一整行的巨型 HTML。压平只应改变 `formatted`/`lines`，
        # 其余事实与文档哈希必须逐项相同，否则同一份稿子会因导出选项判出两套基线。
        source_path = EVAL_DIR / "原型-客户风险简报.html"
        collapsed = re.sub(r"\n\s*", "", source_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "single-line.html"
            path.write_text(collapsed, encoding="utf-8")
            actual = EXTRACTOR.stats(EXTRACTOR.extract(path, "auto", 80, 2, 2))

        expected = dict(self.CASES["原型-客户风险简报.html"])
        self.assertFalse(actual["formatted"])
        self.assertEqual(actual["lines"], 1)
        for key in ("formatted", "lines", "chars"):
            expected.pop(key)
        self.assertEqual({key: actual[key] for key in expected}, expected)

    def test_generated_artifacts_have_bounded_size(self) -> None:
        for filename, result in self.results.items():
            with self.subTest(filename=filename):
                sizes = [
                    len(renderer(result) + "\n")
                    for _, renderer in EXTRACTOR.ARTIFACTS
                ]
                self.assertLessEqual(max(sizes), MAX_SINGLE_ARTIFACT_CHARS)
                self.assertLessEqual(sum(sizes), MAX_TOTAL_ARTIFACT_CHARS)

    def test_every_block_slice_has_bounded_size(self) -> None:
        for filename, result in self.results.items():
            for record in result["blocks"]:
                with self.subTest(filename=filename, anchor=record["anchor"]):
                    rendered = EXTRACTOR.render_block_slice(result, record["anchor"]) + "\n"
                    self.assertLessEqual(len(rendered), MAX_BLOCK_SLICE_CHARS)

    def test_semantic_parent_anchor_can_group_candidate_blocks(self) -> None:
        result = self.results["设计稿原型-标准版.html"]
        record = EXTRACTOR.find_block(result, ".section-box-93")
        rendered = EXTRACTOR.render_block_slice(result, record["anchor"]) + "\n"

        self.assertEqual(record["anchor"], ".section-box-93")
        self.assertEqual(record["nodes"], 220)
        self.assertLessEqual(len(rendered), MAX_BLOCK_SLICE_CHARS)
        self.assertIn("×9", rendered)

    def test_block_hashes_and_line_coordinates_are_well_formed(self) -> None:
        for filename, result in self.results.items():
            formatted = result["document"].formatted
            for record in result["blocks"]:
                with self.subTest(filename=filename, anchor=record["anchor"]):
                    self.assertRegex(record["hash"], r"^[0-9a-f]{8}$")
                    if formatted:
                        self.assertRegex(record["lines"], r"^L\d+–L\d+$")
                    else:
                        self.assertEqual(record["lines"], "-")


class FallbackRegressionTests(unittest.TestCase):
    def test_root_without_named_class_uses_class_structure_anchor(self) -> None:
        source = """<!doctype html>
<style>
.display_common1 { display: flex; }
.child { width: 1rem; }
</style>
<body>
  <section class="display_common1">
    <div class="display_common1 child">内容</div>
  </section>
</body>
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prototype.html"
            path.write_text(source, encoding="utf-8")
            result = EXTRACTOR.extract(path, "shared", 80, 2, 2)

        anchor = result["blocks"][0]["anchor"]
        self.assertEqual(anchor, "@ancestor(1,.child)")
        self.assertNotIn("<section>", anchor)
        rendered = EXTRACTOR.render_block_slice(result, anchor)
        self.assertIn(f"# 区块切片 `{anchor}`", rendered)

    def test_auto_mode_falls_back_to_literal_frequency(self) -> None:
        source = """<!doctype html>
<style>
.first { color: #111; }
.second { color: #111; }
</style>
<body><div class="first"><span class="second">内容</span></div></body>
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prototype.html"
            path.write_text(source, encoding="utf-8")
            result = EXTRACTOR.extract(path, "auto", 80, 2, 2)

        self.assertEqual(result["tokens"].mode, "literal-frequency")
        self.assertEqual(len(result["tokens"].tokens), 1)
        self.assertEqual(result["tokens"].tokens[0]["value"], "#111")


class CoverageGapTests(unittest.TestCase):
    """抽取器读不到的样式来源必须显式出现，不能静默退化成区块规格里的 `未见`。"""

    DIRTY = """<!doctype html><html><head>
<link rel="stylesheet" href="style.css">
<script src="https://cdn.tailwindcss.com"></script>
<style>
.card { padding: 16px; }
@media (max-width: 768px) { .card { padding: 8px; } }
.list > .item:hover { color: red; }
</style></head>
<body><div class="page"><section class="card">
<ul class="list"><li class="item" style="margin:4px">A</li></ul>
</section></div></body></html>
"""

    def extract_source(self, source: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prototype.html"
            path.write_text(source, encoding="utf-8")
            return EXTRACTOR.extract(path, "auto", 80, 2, 2)

    @staticmethod
    def run_cli(argv: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return EXTRACTOR.main(argv)

    def test_every_unreadable_style_source_is_reported(self) -> None:
        gaps = {gap["kind"]: gap for gap in self.extract_source(self.DIRTY)["coverage_gaps"]}
        self.assertEqual(
            set(gaps),
            {"外链样式表", "at 规则", "行内 style 属性", "非单类选择器", "外部脚本"},
        )
        self.assertEqual(gaps["外链样式表"]["detail"], ["style.css"])
        self.assertEqual(gaps["非单类选择器"]["detail"], [".list > .item:hover"])
        self.assertEqual(gaps["行内 style 属性"]["count"], 1)

    def test_real_prototypes_report_no_gap(self) -> None:
        # 误报会让调用方习惯性忽略缺口，所以 reset 型选择器与无害 at 规则不得计入。
        for name in ("设计稿原型-标准版.html", "原型-客户风险简报.html"):
            with self.subTest(name=name):
                result = EXTRACTOR.extract(EVAL_DIR / name, "auto", 80, 2, 2)
                self.assertEqual(result["coverage_gaps"], [])

    def test_reset_selectors_and_harmless_at_rules_are_not_gaps(self) -> None:
        source = """<!doctype html>
<style>
@charset "utf-8";
@font-face { font-family: X; src: url(x.woff2); }
* { box-sizing: border-box; }
body { margin: 0; }
.card { padding: 16px; }
</style>
<body><div class="card">内容</div></body>
"""
        self.assertEqual(self.extract_source(source)["coverage_gaps"], [])

    def test_gaps_reach_design_facts_and_the_human_artifact(self) -> None:
        result = self.extract_source(self.DIRTY)
        facts = json.loads(EXTRACTOR.render_design_facts(result))
        self.assertEqual(facts["coverage_gaps"], result["coverage_gaps"])
        tokens_markdown = EXTRACTOR.render_design_tokens(result)
        self.assertIn("## 抽取覆盖", tokens_markdown)
        self.assertIn("**本表不完整。**", tokens_markdown)
        self.assertIn("style.css", tokens_markdown)

    def test_unacknowledged_gaps_block_with_a_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prototype.html"
            path.write_text(self.DIRTY, encoding="utf-8")
            out_dir = Path(directory) / "design-spec"
            argv = ["extract", str(path), "--out-dir", str(out_dir)]
            self.assertEqual(self.run_cli(argv), EXTRACTOR.EXIT_COVERAGE_GAPS)
            # 阻断的是流程，不是落盘：产物照常写出，供登记「已知缺口」时引用。
            self.assertTrue((out_dir / "design-facts.json").exists())
            self.assertEqual(
                self.run_cli(argv + ["--acknowledge-coverage-gaps"]),
                EXTRACTOR.EXIT_OK,
            )

    def test_clean_prototype_exits_zero_without_acknowledgement(self) -> None:
        argv = ["extract", str(EVAL_DIR / "设计稿原型-标准版.html")]
        self.assertEqual(self.run_cli(argv), EXTRACTOR.EXIT_OK)


class ArtifactPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = EVAL_DIR / "设计稿原型-标准版.html"
        cls.result = EXTRACTOR.extract(cls.source_path, "auto", 80, 2, 2)

    def test_same_document_hash_preserves_existing_global_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory)
            EXTRACTOR.write_artifacts(self.result, out_dir)
            target = out_dir / "interface-inventory.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n人工审订标记\n",
                encoding="utf-8",
            )

            messages = EXTRACTOR.write_artifacts(self.result, out_dir)

            self.assertIn("人工审订标记", target.read_text(encoding="utf-8"))
            self.assertIn(
                "interface-inventory.md（文档哈希一致，保留现有文件）",
                messages,
            )

    def test_changed_document_hash_rewrites_global_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory)
            EXTRACTOR.write_artifacts(self.result, out_dir)
            target = out_dir / "content-inventory.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n旧稿标记\n",
                encoding="utf-8",
            )

            changed_path = out_dir / "changed.html"
            changed_path.write_text(
                self.source_path.read_text(encoding="utf-8").replace("案例中心", "案例中心（新）", 1),
                encoding="utf-8",
            )
            changed = EXTRACTOR.extract(changed_path, "auto", 80, 2, 2)
            EXTRACTOR.write_artifacts(changed, out_dir)

            body = target.read_text(encoding="utf-8")
            self.assertNotIn("旧稿标记", body)
            self.assertIn(f"> 文档哈希：`{changed['document'].doc_hash}`", body)


class DesignFactsAndVisualCacheTests(unittest.TestCase):
    def write_prototype(self, root: Path, *, text: str = "保存", gap: str = "8px") -> Path:
        source = f"""<!doctype html>
<style>
.card {{ display: flex; gap: {gap}; background-image: url("assets/icon.svg"); }}
.label {{ color: #111; }}
</style>
<body>
  <div class="card">
    <span class="label">{text}</span>
  </div>
</body>
"""
        path = root / "prototype.html"
        path.write_text(source, encoding="utf-8")
        return path

    def test_prototype_fingerprint_ignores_formatting_but_tracks_all_fact_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            asset = assets / "icon.svg"
            asset.write_text("<svg>A</svg>", encoding="utf-8")
            path = self.write_prototype(root)

            initial = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            initial_fingerprint = initial["prototype_fingerprint"]

            source = path.read_text(encoding="utf-8")
            path.write_text(
                source.replace("\n", "\n\n").replace("  <div", "      <div"),
                encoding="utf-8",
            )
            reformatted = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertEqual(reformatted["prototype_fingerprint"], initial_fingerprint)

            self.write_prototype(root, text="提交")
            html_changed = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(html_changed["prototype_fingerprint"], initial_fingerprint)

            self.write_prototype(root, gap="9px")
            css_changed = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(css_changed["prototype_fingerprint"], initial_fingerprint)

            self.write_prototype(root)
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    '<span class="label">',
                    '<span class="label" aria-label="保存" style="opacity: .9">',
                ),
                encoding="utf-8",
            )
            attribute_changed = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(
                attribute_changed["prototype_fingerprint"],
                initial_fingerprint,
            )

            self.write_prototype(root)
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "</style>",
                    "@media (max-width: 800px) { .card { gap: 4px; } }\n</style>",
                ),
                encoding="utf-8",
            )
            media_changed = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(
                media_changed["prototype_fingerprint"],
                initial_fingerprint,
            )

            self.write_prototype(root)
            asset.write_text("<svg>B</svg>", encoding="utf-8")
            asset_changed = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(asset_changed["prototype_fingerprint"], initial_fingerprint)

            asset.unlink()
            missing = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertNotEqual(
                missing["prototype_fingerprint"],
                asset_changed["prototype_fingerprint"],
            )
            self.assertEqual(missing["assets"][0]["status"], "missing")

    def test_design_facts_are_stable_and_include_machine_contract_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "assets" / "icon.svg").write_text("<svg/>", encoding="utf-8")
            result = EXTRACTOR.extract(self.write_prototype(root), "auto", 80, 2, 2)
            first = EXTRACTOR.render_design_facts(result)
            second = EXTRACTOR.render_design_facts(result)
            payload = json.loads(first)

            self.assertEqual(first, second)
            self.assertRegex(payload["prototype_fingerprint"], r"^[0-9a-f]{64}$")
            self.assertRegex(payload["facts_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(payload["blocks"])
            self.assertIn("structure", payload["blocks"][0])
            self.assertEqual(
                set(payload["blocks"][0]["structure"]),
                {"tag", "classes", "texts", "children"},
            )
            self.assertIn("layout_declarations", payload)
            self.assertIn("static_texts", payload)
            self.assertEqual(payload["resources"][0]["status"], "present")

    def test_visual_cache_is_lazy_immutable_and_keys_every_environment_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "assets" / "icon.svg").write_text("<svg/>", encoding="utf-8")
            result = EXTRACTOR.extract(self.write_prototype(root), "auto", 80, 2, 2)
            facts_path = root / "design-facts.json"
            facts_path.write_text(EXTRACTOR.render_design_facts(result), encoding="utf-8")
            design_spec_dir = root / "design-spec"
            anchor = result["blocks"][0]["anchor"]

            not_needed = EXTRACTOR.visual_cache_status(
                facts_path,
                design_spec_dir,
                anchor,
                "1440x900",
                2,
                "chromium",
                "126",
                "fonts-A",
                0,
                None,
            )
            self.assertEqual(not_needed["status"], "not-needed")
            self.assertFalse((design_spec_dir / "visual-baseline").exists())

            miss = EXTRACTOR.visual_cache_status(
                facts_path,
                design_spec_dir,
                anchor,
                "1440x900",
                2,
                "chromium",
                "126",
                "fonts-A",
                1,
                None,
            )
            self.assertEqual(miss["status"], "needs-capture")

            png = root / "prototype.png"
            png.write_bytes(EXTRACTOR.PNG_SIGNATURE + b"fixture")
            created = EXTRACTOR.visual_cache_status(
                facts_path,
                design_spec_dir,
                anchor,
                "1440x900",
                2,
                "chromium",
                "126",
                "fonts-A",
                1,
                png,
            )
            hit = EXTRACTOR.visual_cache_status(
                facts_path,
                design_spec_dir,
                anchor,
                "1440x900",
                2,
                "chromium",
                "126",
                "fonts-A",
                1,
                None,
            )
            self.assertEqual(created["status"], "created")
            self.assertEqual(hit["status"], "hit")
            self.assertEqual(created["cache_fingerprint"], hit["cache_fingerprint"])

            cached_png = Path(hit["path"]) / "prototype.png"
            cached_png.write_bytes(EXTRACTOR.PNG_SIGNATURE + b"tampered")
            with self.assertRaisesRegex(ValueError, "manifest 哈希不一致"):
                EXTRACTOR.visual_cache_status(
                    facts_path,
                    design_spec_dir,
                    anchor,
                    "1440x900",
                    2,
                    "chromium",
                    "126",
                    "fonts-A",
                    1,
                    None,
                )

            base = EXTRACTOR.visual_cache_identity(
                result["prototype_fingerprint"],
                anchor,
                {"width": 1440, "height": 900},
                2,
                "chromium",
                "126",
                "fonts-A",
            )
            fingerprints = {EXTRACTOR.visual_cache_fingerprint(base)}
            variations = [
                {**base, "viewport": {"width": 1280, "height": 900}},
                {**base, "dpr": 1.0},
                {**base, "browser": {"engine": "webkit", "version": "126"}},
                {**base, "browser": {"engine": "chromium", "version": "127"}},
                {**base, "font_fingerprint": "fonts-B"},
                {**base, "block_anchor": ".other"},
                {**base, "prototype_fingerprint": "f" * 64},
            ]
            fingerprints.update(
                EXTRACTOR.visual_cache_fingerprint(identity)
                for identity in variations
            )
            self.assertEqual(len(fingerprints), 1 + len(variations))

    def test_visual_cache_counts_only_visual_yellow_for_the_same_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "restore-report-red.json"
            report_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "status": "yellow",
                                "required_layers": ["render"],
                                "contract_source": {
                                    "design_fact_source": {"anchor": ".card"}
                                },
                            },
                            {
                                "status": "yellow",
                                "required_layers": ["visual"],
                                "contract_source": {
                                    "design_fact_source": {"anchor": ".other"}
                                },
                            },
                            {
                                "status": "yellow",
                                "required_layers": ["render", "visual"],
                                "contract_source": {
                                    "design_fact_source": {"anchor": ".card"}
                                },
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                EXTRACTOR.visual_yellow_count(report_path, ".card"),
                1,
            )


def restore_rule(
    rule_id: str,
    dimension: str,
    expected,
    *,
    check_mode: str = "exact",
    layers: list[str] | None = None,
    static_check: dict | None = None,
    exemption: dict | None = None,
) -> dict:
    rule = {
        "id": rule_id,
        "baseline_id": rule_id,
        "dimension": dimension,
        "block": "筛选栏",
        "subject": f"{rule_id} subject",
        "expected": expected,
        "check_mode": check_mode,
        "tolerance": {"css_px": 1},
        "state_scenario": {"name": "default"},
        "design_fact_source": {
            "path": "design-facts.json",
            "anchor": ".filters",
            "key": rule_id,
        },
        "required_layers": layers or ["render"],
    }
    if static_check is not None:
        rule["static_check"] = static_check
    if exemption is not None:
        rule["frozen_exemption"] = exemption
    return rule


class RestoreContractVerificationTests(unittest.TestCase):
    def compile(self, root: Path, rules: list[dict]):
        baseline = root / "dev-baseline.md"
        # 契约要求与基线一一映射，所以基线要恰好列出这批规则引用的编号。
        rows = "\n".join(
            f"| {rule['baseline_id']} | {rule['dimension']} | {rule['id']} 主体 | 见规则 |"
            for rule in rules
        )
        baseline.write_text(
            "# Dev Baseline\n\n冻结状态：已冻结 ✅\n\n"
            "| 编号 | 维度 | 主体 | 期望 |\n| --- | --- | --- | --- |\n"
            f"{rows}\n",
            encoding="utf-8",
        )
        rules_path = root / "rules.json"
        rules_path.write_text(json.dumps({"rules": rules}, ensure_ascii=False), encoding="utf-8")
        contract = VERIFIER.compile_contract(baseline, rules_path, "dev-baseline.md")
        adapter_raw = {
            "schema_version": 1,
            "rules": {
                rule["id"]: {
                    "locators": [
                        {
                            "strategy": "role",
                            "role": "button",
                            "name": rule["id"],
                        }
                    ],
                    "source_files": ["src/view.tsx"],
                    "collect": {"kind": "count"},
                }
                for rule in rules
                if not rule.get("frozen_exemption")
            },
        }
        adapter = VERIFIER.validate_adapter(adapter_raw, contract)
        return baseline, contract, adapter

    @staticmethod
    def render_payload(contract, values: dict) -> dict:
        return {
            "schema_version": 1,
            "contract_sha256": contract["contract_sha256"],
            "page_available": True,
            "rules": values,
        }

    def test_r1_to_r6_rules_produce_expected_red_yellow_green(self) -> None:
        rules = [
            restore_rule("R1-1", "R1", 2, check_mode="structure"),
            restore_rule("R2-1", "R2", ["保存"]),
            restore_rule("R3-1", "R3", "16px", check_mode="numeric"),
            restore_rule("R3-2", "R3", "16px", check_mode="numeric"),
            restore_rule("R4-1", "R4", {"color": "#f00"}, check_mode="state"),
            restore_rule("R5-1", "R5", {"empty": True}),
            restore_rule("R6-1", "R6", 0, check_mode="overflow"),
            restore_rule("R6-2", "R6", 0, check_mode="overlap"),
            restore_rule("R6-3", "R6", 0, check_mode="clip"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, adapter = self.compile(root, rules)
            render = self.render_payload(
                contract,
                {
                    "R1-1": {"status": "ok", "actual": 1},
                    "R2-1": {"status": "ok", "actual": ["提交"]},
                    "R3-1": {"status": "ok", "actual": "17px"},
                    "R3-2": {"status": "ok", "actual": "17.1px"},
                    "R4-1": {"status": "ok", "actual": {"color": "#00f"}},
                    "R5-1": {
                        "status": "missing_fixture",
                        "reason": "empty fixture unavailable",
                    },
                    "R6-1": {"status": "ok", "actual": 1.1},
                    "R6-2": {"status": "ok", "actual": 0.5},
                    "R6-3": {"status": "ok", "actual": 1.1},
                },
            )
            report = VERIFIER.build_report(
                contract,
                adapter,
                "red",
                None,
                render,
                None,
            )

        by_id = {entry["rule_id"]: entry for entry in report["entries"]}
        self.assertEqual(report["overall"], "red")
        self.assertEqual(by_id["R1-1"]["status"], "red")
        self.assertEqual(by_id["R2-1"]["status"], "red")
        self.assertEqual(by_id["R3-1"]["status"], "green")
        self.assertEqual(by_id["R3-2"]["status"], "red")
        self.assertEqual(by_id["R4-1"]["status"], "red")
        self.assertEqual(by_id["R5-1"]["status"], "yellow")
        self.assertIn("required_evidence", by_id["R5-1"])
        self.assertEqual(by_id["R6-1"]["status"], "red")
        self.assertEqual(by_id["R6-2"]["status"], "green")
        self.assertEqual(by_id["R6-3"]["status"], "red")
        self.assertIn("expected", by_id["R1-1"])
        self.assertIn("actual", by_id["R1-1"])
        self.assertIn("contract_source", by_id["R1-1"])
        self.assertIn("implementation_locator", by_id["R1-1"])

    def test_summary_precedence_and_frozen_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rules = [restore_rule("R1-1", "R1", 1)]
            _, contract, adapter = self.compile(root, rules)
            unavailable = {
                "contract_sha256": contract["contract_sha256"],
                "page_available": False,
                "reason": "dev server unavailable",
                "rules": {},
            }
            yellow = VERIFIER.build_report(
                contract,
                adapter,
                "red",
                None,
                unavailable,
                None,
            )
            self.assertEqual(yellow["overall"], "yellow")
            self.assertEqual(yellow["summary"]["red"], 0)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rules = [
                restore_rule("R1-1", "R1", 1),
                restore_rule(
                    "R2-1",
                    "R2",
                    "保存",
                    exemption={"id": "EX-1", "frozen": True, "reason": "平台限制"},
                ),
            ]
            _, contract, adapter = self.compile(root, rules)
            render = self.render_payload(
                contract,
                {"R1-1": {"status": "ok", "actual": 1}},
            )
            green = VERIFIER.build_report(
                contract,
                adapter,
                "green",
                None,
                render,
                None,
            )
            self.assertEqual(green["overall"], "green")
            self.assertEqual(green["summary"]["green"], 2)

    def test_static_pass_does_not_hide_structured_render_failure(self) -> None:
        rule = restore_rule(
            "R3-1",
            "R3",
            {"static": "--space-md", "render": "16px"},
            check_mode="numeric",
            layers=["static", "render"],
            static_check={"kind": "token", "value": "--space-md"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            source.mkdir()
            (source / "view.tsx").write_text(
                'const style = "var(--space-md)";',
                encoding="utf-8",
            )
            _, contract, adapter = self.compile(root, [rule])
            static = VERIFIER.run_static_preflight(contract, adapter, root)
            render = {
                "contract_sha256": contract["contract_sha256"],
                "page_available": True,
                "capture_error": "getComputedStyle injection failed",
                "rules": {},
            }
            report = VERIFIER.build_report(
                contract,
                adapter,
                "red",
                static,
                render,
                None,
            )

        self.assertEqual(static["rules"]["R3-1"]["status"], "pass")
        self.assertEqual(report["overall"], "red")
        self.assertEqual(report["entries"][0]["status"], "red")

    def test_no_screenshot_does_not_affect_machine_decidable_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, adapter = self.compile(
                root,
                [restore_rule("R1-1", "R1", 1)],
            )
            render = self.render_payload(
                contract,
                {"R1-1": {"status": "ok", "actual": 1}},
            )
            report = VERIFIER.build_report(
                contract,
                adapter,
                "green",
                None,
                render,
                None,
            )

        self.assertEqual(report["overall"], "green")
        self.assertEqual(report["summary"], {"red": 0, "yellow": 0, "green": 1, "total": 1})

    def test_color_syntaxes_normalize_to_the_same_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, adapter = self.compile(
                root,
                [restore_rule("R3-1", "R3", "#fff", check_mode="color")],
            )
            render = self.render_payload(
                contract,
                {"R3-1": {"status": "ok", "actual": "rgb(255, 255, 255)"}},
            )
            report = VERIFIER.build_report(
                contract,
                adapter,
                "green",
                None,
                render,
                None,
            )

        self.assertEqual(report["overall"], "green")
        self.assertEqual(report["entries"][0]["status"], "green")

    def test_result_payload_must_name_the_frozen_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, adapter = self.compile(
                root,
                [restore_rule("R1-1", "R1", 1)],
            )
            render = {
                "page_available": True,
                "rules": {"R1-1": {"status": "ok", "actual": 1}},
            }
            with self.assertRaisesRegex(VERIFIER.ContractError, "冻结契约不一致"):
                VERIFIER.build_report(
                    contract,
                    adapter,
                    "green",
                    None,
                    render,
                    None,
                )

    def test_baseline_hash_mismatch_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, contract, _ = self.compile(
                root,
                [restore_rule("R1-1", "R1", 1)],
            )
            baseline.write_text(
                "# changed after freeze\n\n冻结状态：已冻结 ✅\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VERIFIER.ContractError, "哈希不一致"):
                VERIFIER.validate_contract(contract, baseline)

    def test_unconfirmed_baseline_cannot_compile_a_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "dev-baseline.md"
            baseline.write_text("冻结状态：待确认 ⏳\n", encoding="utf-8")
            rules = root / "rules.json"
            rules.write_text(
                json.dumps(
                    {"rules": [restore_rule("R1-1", "R1", 1)]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VERIFIER.ContractError, "尚未标记为已冻结"):
                VERIFIER.compile_contract(baseline, rules)

    def test_legacy_screenshot_evidence_remains_recognizable(self) -> None:
        legacy = """## 还原证据记录

**RED 双方截图**

**GREEN 复核**
"""
        machine = """## 还原证据记录

报告指纹：`abc`
路径：restore-report-green.json
"""
        self.assertEqual(
            VERIFIER.detect_restore_evidence_format(legacy),
            "legacy-screenshot-v1",
        )
        self.assertEqual(
            VERIFIER.detect_restore_evidence_format(machine),
            "machine-v2",
        )

    def test_generated_css_locator_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, _ = self.compile(
                root,
                [restore_rule("R1-1", "R1", 1)],
            )
            adapter = {
                "schema_version": 1,
                "rules": {
                    "R1-1": {
                        "locators": [
                            {
                                "strategy": "css",
                                "selector": ".button_a8f41c92",
                            }
                        ],
                        "source_files": ["src/view.tsx"],
                    }
                },
            }
            with self.assertRaisesRegex(VERIFIER.ContractError, "随机 class"):
                VERIFIER.validate_adapter(adapter, contract)

    def test_adapter_cannot_mix_in_external_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, contract, _ = self.compile(
                root,
                [restore_rule("R1-1", "R1", 1)],
            )
            adapter = {
                "schema_version": 1,
                "rules": {
                    "R1-1": {
                        "expected": 1,
                        "locators": [
                            {
                                "strategy": "role",
                                "role": "button",
                                "name": "保存",
                            }
                        ],
                    }
                },
            }
            with self.assertRaisesRegex(VERIFIER.ContractError, "混入外部判定字段"):
                VERIFIER.validate_adapter(adapter, contract)

    def test_green_phase_uses_nonzero_exit_for_a_non_green_report(self) -> None:
        self.assertEqual(VERIFIER.report_exit_code("green", "red"), 3)
        self.assertEqual(VERIFIER.report_exit_code("green", "yellow"), 3)
        self.assertEqual(VERIFIER.report_exit_code("green", "green"), 0)
        self.assertEqual(VERIFIER.report_exit_code("red", "red"), 0)


if __name__ == "__main__":
    unittest.main()
