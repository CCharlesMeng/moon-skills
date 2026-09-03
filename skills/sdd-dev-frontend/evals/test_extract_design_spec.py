#!/usr/bin/env python3
"""Regression tests for the deterministic design inventory extractor."""

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
MAX_INVENTORY_CHARS = 65_000
MAX_BLOCK_SLICE_CHARS = 12_000


def load_extractor():
    spec = importlib.util.spec_from_file_location("extract_design_spec", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXTRACTOR = load_extractor()


class SampleRegressionTests(unittest.TestCase):
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
                self.assertEqual({key: actual[key] for key in expected}, expected)

    def test_single_line_export_keeps_semantic_facts(self) -> None:
        source_path = EVAL_DIR / "原型-客户风险简报.html"
        collapsed = re.sub(r"\n\s*", "", source_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "single-line.html"
            path.write_text(collapsed, encoding="utf-8")
            actual = EXTRACTOR.stats(EXTRACTOR.extract(path, "auto", 80, 2, 2))
        expected = dict(self.CASES[source_path.name])
        self.assertFalse(actual["formatted"])
        self.assertEqual(actual["lines"], 1)
        for key in ("formatted", "lines", "chars"):
            expected.pop(key)
        self.assertEqual({key: actual[key] for key in expected}, expected)

    def test_one_human_inventory_is_bounded(self) -> None:
        self.assertEqual([name for name, _ in EXTRACTOR.ARTIFACTS], ["design-inventory.md"])
        for filename, result in self.results.items():
            with self.subTest(filename=filename):
                body = EXTRACTOR.render_design_inventory(result) + "\n"
                self.assertLessEqual(len(body), MAX_INVENTORY_CHARS)
                self.assertEqual(body.count("# Design Inventory"), 1)
                self.assertEqual(body.count("> 文档哈希："), 1)

    def test_every_block_slice_is_bounded(self) -> None:
        for filename, result in self.results.items():
            for record in result["blocks"]:
                with self.subTest(filename=filename, anchor=record["anchor"]):
                    rendered = EXTRACTOR.render_block_slice(result, record["anchor"]) + "\n"
                    self.assertLessEqual(len(rendered), MAX_BLOCK_SLICE_CHARS)

    def test_semantic_parent_anchor_groups_candidate_blocks(self) -> None:
        result = self.results["设计稿原型-标准版.html"]
        record = EXTRACTOR.find_block(result, ".section-box-93")
        self.assertEqual(record["nodes"], 220)
        self.assertIn("×9", EXTRACTOR.render_block_slice(result, record["anchor"]))


class ExtractorBehaviorTests(unittest.TestCase):
    def write_prototype(self, root: Path, *, text: str = "保存", gap: str = "8px", extra_style: str = "") -> Path:
        path = root / "prototype.html"
        path.write_text(
            "<!doctype html>\n<style>\n"
            f".card {{ display: flex; gap: {gap}; background-image: url('assets/icon.svg'); }}\n"
            ".label { color: #111; }\n"
            f"{extra_style}\n</style>\n<body><div class='card'><span class='label'>{text}</span></div></body>\n",
            encoding="utf-8",
        )
        return path

    def prepare(self, root: Path):
        (root / "assets").mkdir()
        (root / "assets" / "icon.svg").write_text("<svg/>", encoding="utf-8")
        return EXTRACTOR.extract(self.write_prototype(root), "auto", 80, 2, 2)

    def test_design_facts_are_stable_and_have_no_duplicate_block_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.prepare(Path(directory))
            first = EXTRACTOR.render_design_facts(result)
            self.assertEqual(first, EXTRACTOR.render_design_facts(result))
            payload = json.loads(first)
            self.assertEqual(payload["schema_version"], 2)
            self.assertRegex(payload["prototype_fingerprint"], r"^[0-9a-f]{64}$")
            self.assertRegex(payload["facts_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("content_sha256", payload["blocks"][0])
            self.assertNotIn("content_hash", payload["blocks"][0])
            self.assertEqual(
                set(payload["blocks"][0]["structure"]),
                {"tag", "classes", "texts", "children"},
            )

    def test_prototype_fingerprint_ignores_formatting_and_tracks_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = self.prepare(root)
            fingerprint = initial["prototype_fingerprint"]
            path = root / "prototype.html"
            path.write_text(path.read_text(encoding="utf-8").replace("\n", "\n\n"), encoding="utf-8")
            self.assertEqual(EXTRACTOR.extract(path, "auto", 80, 2, 2)["prototype_fingerprint"], fingerprint)
            self.write_prototype(root, text="提交")
            self.assertNotEqual(EXTRACTOR.extract(path, "auto", 80, 2, 2)["prototype_fingerprint"], fingerprint)
            self.write_prototype(root, gap="9px")
            self.assertNotEqual(EXTRACTOR.extract(path, "auto", 80, 2, 2)["prototype_fingerprint"], fingerprint)

    def test_unreadable_style_source_is_reported_and_blocks_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "assets" / "icon.svg").write_text("<svg/>", encoding="utf-8")
            path = self.write_prototype(root, extra_style="@import url('theme.css');")
            result = EXTRACTOR.extract(path, "auto", 80, 2, 2)
            self.assertTrue(result["coverage_gaps"])
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(EXTRACTOR.main(["extract", str(path)]), EXTRACTOR.EXIT_COVERAGE_GAPS)
                self.assertEqual(
                    EXTRACTOR.main(["extract", str(path), "--acknowledge-coverage-gaps"]),
                    EXTRACTOR.EXIT_OK,
                )


class ArtifactPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = EVAL_DIR / "设计稿原型-标准版.html"
        cls.result = EXTRACTOR.extract(cls.source_path, "auto", 80, 2, 2)

    def test_same_hash_preserves_human_amendment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory)
            EXTRACTOR.write_artifacts(self.result, out_dir)
            target = out_dir / "design-inventory.md"
            target.write_text(target.read_text(encoding="utf-8") + "\n人工审订标记\n", encoding="utf-8")
            messages = EXTRACTOR.write_artifacts(self.result, out_dir)
            self.assertIn("人工审订标记", target.read_text(encoding="utf-8"))
            self.assertIn("design-inventory.md（文档哈希一致，保留现有文件）", messages)

    def test_changed_hash_rewrites_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_dir = Path(directory)
            EXTRACTOR.write_artifacts(self.result, out_dir)
            target = out_dir / "design-inventory.md"
            target.write_text(target.read_text(encoding="utf-8") + "\n旧稿标记\n", encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
