#!/usr/bin/env python3
"""Regression tests for exact preflight reuse and compact telemetry."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = EVAL_DIR.parent / "scripts" / "manage_execution_evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("manage_execution_evidence", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本：{SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def run_git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(repo), *arguments], check=True, capture_output=True)


def initialized_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "eval@example.com")
    run_git(repo, "config", "user.name", "Eval")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", "tracked.txt")
    run_git(repo, "commit", "-m", "base")
    return repo


def snapshot(repo: Path, **overrides):
    values = {
        "quality_version": "3",
        "quality_commands": ["test::npm test", "check::npm run check"],
        "uncacheable_commands": [],
        "toolchains": {"node": "24.1.0", "npm": "11.0.0"},
        "runtime": {"ci_mode": "false", "os_arch": "darwin-arm64"},
    }
    values.update(overrides)
    return MODULE.build_snapshot(repo, **values)


def quality_result(specs=None):
    specs = specs or ["test::npm test", "check::npm run check"]
    return {
        "commands": [
            {"spec": spec, "exit_code": 0, "duration_ms": 12, "failures": []}
            for spec in specs
        ]
    }


class PreflightEvidenceTests(unittest.TestCase):
    def test_exact_state_records_and_hits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialized_repo(Path(directory))
            current = snapshot(repo)
            result = quality_result()
            result_path = Path(directory) / "quality.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            snapshot_path = Path(directory) / "snapshot.json"
            snapshot_path.write_text(json.dumps(current), encoding="utf-8")

            MODULE.command_record(
                argparse.Namespace(
                    snapshot=str(snapshot_path),
                    quality_result=str(result_path),
                    source="phase-d",
                )
            )
            hit = MODULE.probe_cache(snapshot(repo), 24)

            self.assertEqual(hit["status"], "HIT")
            self.assertEqual(hit["reason"], "exact-match")
            self.assertEqual(hit["source"], "phase-d")
            self.assertEqual(hit["quality_result"], result)

    def test_worktree_changes_each_invalidate_exact_match(self) -> None:
        mutations = {
            "unstaged-diff-changed": lambda repo: (repo / "tracked.txt").write_text(
                "unstaged\n", encoding="utf-8"
            ),
            "staged-diff-changed": lambda repo: (
                (repo / "tracked.txt").write_text("staged\n", encoding="utf-8"),
                run_git(repo, "add", "tracked.txt"),
            ),
            "untracked-changed": lambda repo: (repo / "new.txt").write_text(
                "new\n", encoding="utf-8"
            ),
        }
        for expected_reason, mutate in mutations.items():
            with self.subTest(reason=expected_reason), tempfile.TemporaryDirectory() as directory:
                repo = initialized_repo(Path(directory))
                original = snapshot(repo)
                cache = {
                    **original,
                    "recorded_at": MODULE.isoformat(MODULE.utc_now()),
                    "source": "phase-c",
                    "quality_result": quality_result(),
                }
                MODULE.atomic_write_json(MODULE.cache_path(repo), cache)
                mutate(repo)

                result = MODULE.probe_cache(snapshot(repo), 24)

                self.assertEqual(result["status"], "MISS")
                self.assertEqual(result["reason"], expected_reason)

    def test_contract_environment_and_ttl_changes_invalidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialized_repo(Path(directory))
            original = snapshot(repo)
            cache = {
                **original,
                "recorded_at": MODULE.isoformat(MODULE.utc_now()),
                "source": "phase-c",
                "quality_result": quality_result(),
            }
            path = MODULE.cache_path(repo)
            MODULE.atomic_write_json(path, cache)

            variants = [
                (snapshot(repo, quality_version="4"), "quality-version-changed"),
                (
                    snapshot(repo, quality_commands=["test::npm test -- --runInBand"]),
                    "quality-commands-changed",
                ),
                (snapshot(repo, toolchains={"node": "25.0.0"}), "toolchains-changed"),
                (snapshot(repo, runtime={"ci_mode": "true"}), "runtime-changed"),
            ]
            for current, expected_reason in variants:
                with self.subTest(fingerprint=current["state_fingerprint"]):
                    self.assertEqual(
                        MODULE.probe_cache(current, 24)["reason"],
                        expected_reason,
                    )

            cache["recorded_at"] = MODULE.isoformat(
                MODULE.utc_now() - dt.timedelta(hours=25)
            )
            MODULE.atomic_write_json(path, cache)
            self.assertEqual(MODULE.probe_cache(original, 24)["reason"], "ttl-expired")

    def test_uncacheable_command_never_hits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialized_repo(Path(directory))
            external = "e2e::npm run external-e2e"
            current = snapshot(
                repo,
                quality_commands=[*quality_result_specs(), external],
                uncacheable_commands=[external],
            )
            result = MODULE.probe_cache(current, 24)
            self.assertEqual(result, {
                "status": "MISS",
                "reason": "uncacheable-command",
                "cache_path": str(MODULE.cache_path(repo)),
                "state_fingerprint": current["state_fingerprint"],
            })

    def test_record_refuses_state_drift_and_command_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = initialized_repo(Path(directory))
            current = snapshot(repo)
            snapshot_path = Path(directory) / "snapshot.json"
            snapshot_path.write_text(json.dumps(current), encoding="utf-8")
            result_path = Path(directory) / "quality.json"
            result_path.write_text(json.dumps(quality_result()), encoding="utf-8")
            (repo / "new.txt").write_text("drift\n", encoding="utf-8")

            with self.assertRaisesRegex(MODULE.EvidenceError, "state changed"):
                MODULE.command_record(
                    argparse.Namespace(
                        snapshot=str(snapshot_path),
                        quality_result=str(result_path),
                        source="phase-0",
                    )
                )

            result_path.write_text(
                json.dumps(quality_result(["test::different"])), encoding="utf-8"
            )
            with self.assertRaisesRegex(MODULE.EvidenceError, "do not exactly match"):
                MODULE.normalize_quality_result(
                    json.loads(result_path.read_text(encoding="utf-8")),
                    current["quality_commands"],
                )

    def test_secret_runtime_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.EvidenceError, "forbidden"):
            MODULE.parse_key_values(["api_key=abc"], "runtime")


def quality_result_specs():
    return ["test::npm test", "check::npm run check"]


class TelemetryTests(unittest.TestCase):
    def test_appends_attempts_and_separates_human_wait(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution-telemetry.json"
            common = {
                "file": str(path),
                "story": "ST-1",
                "started_at": "2026-08-16T10:00:00+08:00",
                "ended_at": "2026-08-16T10:00:01.250+08:00",
                "count": ["commands=3"],
                "evidence": ["dev-baseline.md#起点质量"],
                "note": "cache HIT",
            }
            MODULE.command_telemetry(
                argparse.Namespace(
                    **common,
                    id="phase-0.quality-gate",
                    attempt=1,
                    kind="agent",
                    result="reuse",
                )
            )
            MODULE.command_telemetry(
                argparse.Namespace(
                    **{
                        **common,
                        "started_at": "2026-08-16T10:01:00+08:00",
                        "ended_at": "2026-08-16T10:02:00+08:00",
                        "count": [],
                        "evidence": [],
                        "note": "confirmed",
                    },
                    id="human.qa-confirmation",
                    attempt=1,
                    kind="human_wait",
                    result="run",
                )
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(len(payload["steps"]), 2)
            self.assertEqual(payload["steps"][0]["duration_ms"], 1250)
            self.assertEqual(payload["steps"][0]["result"], "reuse")
            self.assertEqual(payload["steps"][1]["kind"], "human_wait")

            with self.assertRaisesRegex(MODULE.EvidenceError, "duplicate telemetry"):
                MODULE.command_telemetry(
                    argparse.Namespace(
                        **common,
                        id="phase-0.quality-gate",
                        attempt=1,
                        kind="agent",
                        result="reuse",
                    )
                )

    def test_browser_kinds_are_recorded_separately(self) -> None:
        """浏览器动作不能并进 agent。

        连接、注入、截图的削减手段完全不同（批量 / 契约范围 / 盲区收窄），
        混成一个数就看不出该动哪一边。而在这三类落地之前，仓里一条浏览器耗时
        数据都没有——唯一的次数统计是从事故复盘里捞出来的。
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution-telemetry.json"
            kinds = ("browser_connect", "browser_inject", "browser_capture")
            for index, kind in enumerate(kinds):
                MODULE.command_telemetry(
                    argparse.Namespace(
                        file=str(path),
                        story="ST-1",
                        started_at="2026-08-16T10:00:00+08:00",
                        ended_at="2026-08-16T10:00:02+08:00",
                        count=[],
                        evidence=[],
                        note=None,
                        id=f"phase-c.{kind}",
                        attempt=1,
                        kind=kind,
                        result="run",
                    )
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([step["kind"] for step in payload["steps"]], list(kinds))
            # 三类都带耗时，Phase D 才能机械汇总出「浏览器占了多少」。
            self.assertTrue(all(step["duration_ms"] == 2000 for step in payload["steps"]))

    def test_cli_rejects_an_unregistered_kind(self) -> None:
        """--kind 是闭集：拼错或自造一类会让汇总静默漏掉那批动作。"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution-telemetry.json"
            with self.assertRaises(SystemExit):
                MODULE.main(
                    [
                        "telemetry",
                        "--file",
                        str(path),
                        "--story",
                        "ST-1",
                        "--id",
                        "phase-c.browser",
                        "--attempt",
                        "1",
                        "--kind",
                        "browser",
                        "--started-at",
                        "2026-08-16T10:00:00+08:00",
                        "--ended-at",
                        "2026-08-16T10:00:01+08:00",
                        "--result",
                        "run",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
