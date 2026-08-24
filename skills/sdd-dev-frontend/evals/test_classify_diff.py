#!/usr/bin/env python3
"""Regression tests for the mechanical diff floor."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "classify_diff.py"
SPEC = importlib.util.spec_from_file_location("classify_diff", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def triggers(files, lines=(), shared=MODULE.DEFAULT_SHARED_PATHS):
    result = MODULE.classify(list(files), list(lines), shared)
    return {key: [item["evidence"] for item in value] for key, value in result["risk_triggers"].items()}


def rebuttals(files, lines=(), shared=MODULE.DEFAULT_SHARED_PATHS):
    result = MODULE.classify(list(files), list(lines), shared)
    return {key: [item["evidence"] for item in value] for key, value in result["skip_rebuttals"].items()}


def changed(path, status="M"):
    return {"path": path, "status": status}


class FloorTests(unittest.TestCase):
    def test_path_evidence_produces_the_four_derivable_triggers(self):
        found = triggers([
            changed("src/features/detail/panel.module.css"),
            changed("src/router/index.ts"),
            changed("src/shared/client.ts"),
            changed("package.json"),
        ])
        self.assertEqual(sorted(found), ["build-config", "navigation", "shared-boundary", "visual"])

    def test_semantic_triggers_are_never_invented(self):
        found = triggers([changed("src/features/detail/useDetail.ts")], [
            ("src/features/detail/useDetail.ts", "const controller = new AbortController();"),
        ])
        # async-state / performance / spec-gap 需要语义判断，下限里不出现。
        self.assertEqual(found, {})

    def test_prose_mentioning_a_library_is_not_a_code_fact(self):
        docs = [changed("docs/guide.md"), changed("README.md")]
        prose = [("docs/guide.md", "各处裸 axios、i18n 资源缺失，`@ts-ignore` 也不少。")]
        self.assertEqual(triggers(docs, prose), {})
        self.assertEqual(rebuttals(docs, prose), {})

    def test_content_rebuttals_cite_the_line_that_produced_them(self):
        found = MODULE.classify(
            [changed("src/a.tsx")],
            [("src/a.tsx", "// @ts-ignore"), ("src/a.tsx", "await fetch('/api');")],
            MODULE.DEFAULT_SHARED_PATHS,
        )["skip_rebuttals"]
        self.assertEqual([item["evidence"] for item in found["C6"]], ["src/a.tsx: // @ts-ignore"])
        self.assertEqual(found["C4"][0]["rule"], "request-or-cancellation")

    def test_added_and_renamed_files_rebut_the_naming_dimension(self):
        self.assertIn("C1", rebuttals([changed("src/a.tsx", "A")]))
        self.assertIn("C1", rebuttals([changed("src/a.tsx", "R")]))
        self.assertNotIn("C1", rebuttals([changed("src/a.tsx", "M")]))

    def test_shared_boundary_follows_the_repo_specific_globs(self):
        files = [changed("app/kit/button.tsx")]
        self.assertNotIn("shared-boundary", triggers(files))
        self.assertIn("shared-boundary", triggers(files, shared=("*/kit/*",)))


class EndToEndTests(unittest.TestCase):
    def test_reads_tracked_untracked_and_ignores_deletions(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)

            def run(*arguments):
                subprocess.run(["git", "-C", str(repo), *arguments], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            run("init", "-q")
            run("config", "user.email", "t@example.com")
            run("config", "user.name", "t")
            (repo / "src").mkdir()
            (repo / "src/old.css").write_text("a{}\n")
            (repo / "src/keep.ts").write_text("export const a = 1;\n")
            run("add", "-A")
            run("commit", "-qm", "base")
            (repo / "src/old.css").unlink()
            (repo / "src/keep.ts").write_text("export const a = 2;\n// @ts-ignore\n")
            (repo / "src/router").mkdir()
            (repo / "src/router/index.ts").write_text("export const routes = [];\n")

            payload = MODULE.build(repo, "HEAD", MODULE.DEFAULT_SHARED_PATHS)
            paths = {item["path"]: item["status"] for item in payload["changed_files"]}
            self.assertNotIn("src/old.css", paths)
            self.assertEqual(paths["src/router/index.ts"], "A")
            self.assertEqual(paths["src/keep.ts"], "M")
            self.assertIn("navigation", payload["risk_triggers"])
            self.assertIn("C6", payload["skip_rebuttals"])


if __name__ == "__main__":
    unittest.main()
