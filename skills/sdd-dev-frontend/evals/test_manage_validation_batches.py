#!/usr/bin/env python3
"""Regression tests for validation planning, batching, receipts, and reruns."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "manage_validation_batches.py"
SPEC = importlib.util.spec_from_file_location("manage_validation_batches", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def browser_execution():
    return {
        "driver": "in-app-browser",
        "page": "/workbench",
        "fixture": {"name": "workbench", "sha256": "fixture-v1"},
        "reset_strategy": "reset-fixture-without-reconnect",
        "runtime": {"browser": "Chromium 140", "dpr": 1, "account": "qa"},
    }


def browser_intent(
    identifier, dependency, viewport, state="empty", consumer="T1-r1/restore",
    cleanup_required=False,
):
    intent = {
        "id": identifier,
        "kind": "browser",
        "boundary": "workbench-local-state",
        "consumers": [consumer],
        "assertions": [f"AC-{identifier}", f"R-{identifier}"],
        "depends_on": [dependency],
        "execution": browser_execution(),
        "scenario": {
            "name": state,
            "viewport": {"width": viewport, "height": 800},
            "steps": ["reset fixture", f"enter {state}", "collect facts"],
        },
    }
    if cleanup_required:
        intent["barrier"] = True
        intent["cleanup_required"] = True
    return intent


def command_intent(identifier, dependency, scope, consumer, barrier=False):
    return {
        "id": identifier,
        "kind": "command",
        "boundary": "package-ui",
        "barrier": barrier,
        "consumers": [consumer],
        "assertions": [f"Q-{identifier}"],
        "depends_on": [dependency],
        "scope": [scope],
        "execution": {
            "package": "apps/ui",
            "commands": [
                {"name": "test", "argv": ["npm", "test", "--", "{scope}"]},
                {"name": "lint", "argv": ["npm", "run", "lint", "--", "{scope}"]},
            ],
            "toolchain": {"node": "24", "npm": "11"},
            "runtime": {"ci": "false"},
        },
    }


def result_for(batch, intent_ids=None, status="pass", browser_calls=0, commands=0):
    selected = [
        intent for intent in batch["intents"]
        if intent_ids is None or intent["id"] in intent_ids
    ]
    return {
        "batch_id": batch["id"],
        "executed_at": "2026-08-16T18:00:00+08:00",
        "metrics": {
            "browser_calls": browser_calls,
            "commands": commands,
            "retries": 0,
        },
        "items": [
            {
                "intent_id": intent["id"],
                "results": [
                    {
                        "assertion": assertion,
                        "status": status,
                        "evidence": [f"observed {assertion}"],
                    }
                    for assertion in intent["assertions"]
                ],
                **({
                    "cleanup": {
                        "status": "cleaned",
                        "evidence": ["removed test record id=fixture-1"],
                    }
                } if intent.get("cleanup_required") else {}),
            }
            for intent in selected
        ],
    }


class ValidationBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for name in ("view.tsx", "style.css", "test.ts"):
            (self.root / name).write_text(f"{name} v1\n", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def plan(self, intents):
        return MODULE.build_plan(
            {"schema_version": 1, "story": "ST-batch", "intents": intents},
            self.root,
        )

    def test_one_task_state_and_viewport_matrix_becomes_one_browser_batch(self):
        intents = [
            browser_intent("empty-1440", "view.tsx", 1440, "empty"),
            browser_intent("four-1280", "view.tsx", 1280, "four-lines"),
            browser_intent("five-900", "style.css", 900, "five-lines"),
            browser_intent("ime-900", "view.tsx", 900, "ime-composition"),
        ]

        plan = self.plan(intents)

        self.assertEqual(len(plan["batches"]), 1)
        batch = plan["batches"][0]
        self.assertEqual(batch["kind"], "browser")
        self.assertEqual(batch["execution"]["session_strategy"], "open-once-reset-between-intents")
        self.assertEqual(len(batch["execution"]["scenarios"]), 4)
        self.assertEqual(batch["consumers"], ["T1-r1/restore"])

    def test_compatible_tasks_share_commands_and_scope_union(self):
        plan = self.plan([
            command_intent("t1-quality", "view.tsx", "src/view.tsx", "T1-r1/logic"),
            command_intent("t2-quality", "test.ts", "src/test.ts", "T2-r1/logic"),
        ])

        self.assertEqual(len(plan["batches"]), 1)
        execution = plan["batches"][0]["execution"]
        self.assertEqual(execution["scope"], ["src/test.ts", "src/view.tsx"])
        self.assertEqual(
            execution["commands"][0]["argv"],
            ["npm", "test", "--", "src/test.ts", "src/view.tsx"],
        )

    def test_batch_id_is_stable_when_a_compatible_intent_is_added(self):
        one = self.plan([browser_intent("empty", "view.tsx", 1200)])
        two = self.plan([
            browser_intent("empty", "view.tsx", 1200),
            browser_intent("error", "style.css", 900),
        ])

        self.assertEqual(one["batches"][0]["id"], two["batches"][0]["id"])
        self.assertRegex(one["batches"][0]["id"], r"^VAL-B-[0-9a-f]{12}$")

    def test_barrier_intent_flushes_even_when_execution_matches(self):
        plan = self.plan([
            command_intent("safe", "view.tsx", "src/view.tsx", "T1-r1/logic"),
            command_intent("auth", "test.ts", "src/test.ts", "T2-r1/logic", barrier=True),
        ])

        self.assertEqual(len(plan["batches"]), 2)
        self.assertEqual(sorted(len(batch["intents"]) for batch in plan["batches"]), [1, 1])

    def test_record_rejects_summary_only_or_missing_assertion(self):
        plan = self.plan([browser_intent("empty", "view.tsx", 1200)])
        batch = plan["batches"][0]
        summary_only = {
            "batch_id": batch["id"],
            "executed_at": "2026-08-16T18:00:00+08:00",
            "metrics": {"browser_calls": 1},
            "items": [{"intent_id": "empty", "status": "pass"}],
        }
        with self.assertRaisesRegex(MODULE.ValidationBatchError, "results must be an array"):
            MODULE.append_receipt(plan, summary_only, None)

        missing = result_for(batch, browser_calls=1)
        missing["items"][0]["results"].pop()
        with self.assertRaisesRegex(MODULE.ValidationBatchError, "cover every assertion exactly once"):
            MODULE.append_receipt(plan, missing, None)

    def test_record_rejects_tampered_plan_fingerprint(self):
        plan = self.plan([browser_intent("empty", "view.tsx", 1200)])
        plan["batches"][0]["intents"][0]["assertions"].append("invented-after-plan")

        with self.assertRaisesRegex(MODULE.ValidationBatchError, "intent_fingerprint mismatch"):
            MODULE.append_receipt(
                plan,
                result_for(plan["batches"][0], browser_calls=1),
                None,
            )

    def test_real_data_intent_requires_cleanup_disclosure(self):
        plan = self.plan([
            browser_intent(
                "submit", "view.tsx", 1200, state="submit-real-data",
                cleanup_required=True,
            )
        ])
        batch = plan["batches"][0]
        result = result_for(batch, browser_calls=1)
        result["items"][0].pop("cleanup")

        with self.assertRaisesRegex(MODULE.ValidationBatchError, "cleanup must be an object"):
            MODULE.append_receipt(plan, result, None)

    def test_changed_dependency_stales_only_affected_intent_and_next_batch_is_filtered(self):
        original = self.plan([
            browser_intent("view-state", "view.tsx", 1200),
            browser_intent("style-state", "style.css", 900),
        ])
        batch = original["batches"][0]
        receipts = MODULE.append_receipt(
            original, result_for(batch, browser_calls=2), None
        )
        (self.root / "view.tsx").write_text("view.tsx v2\n", encoding="utf-8")
        current = self.plan([
            browser_intent("view-state", "view.tsx", 1200),
            browser_intent("style-state", "style.css", 900),
        ])

        status = MODULE.summarize_status(current, receipts)

        self.assertFalse(status["ready"])
        self.assertEqual(status["intents"]["view-state"]["status"], "stale")
        self.assertEqual(status["intents"]["style-state"]["status"], "passed")
        self.assertEqual(status["next_batches"][0]["intent_ids"], ["view-state"])
        self.assertEqual(
            [item["intent_id"] for item in status["next_batches"][0]["execution"]["scenarios"]],
            ["view-state"],
        )

    def test_partial_rerun_preserves_unaffected_result(self):
        original = self.plan([
            browser_intent("view-state", "view.tsx", 1200),
            browser_intent("style-state", "style.css", 900),
        ])
        receipts = MODULE.append_receipt(
            original, result_for(original["batches"][0], browser_calls=2), None
        )
        (self.root / "view.tsx").write_text("view.tsx v2\n", encoding="utf-8")
        current = self.plan([
            browser_intent("view-state", "view.tsx", 1200),
            browser_intent("style-state", "style.css", 900),
        ])
        receipts = MODULE.append_receipt(
            current,
            result_for(current["batches"][0], ["view-state"], browser_calls=1),
            receipts,
        )

        status = MODULE.summarize_status(current, receipts)

        self.assertTrue(status["ready"])
        self.assertEqual(status["counts"]["passed"], 2)
        self.assertEqual(status["counts"]["browser_calls"], 3)
        self.assertEqual(status["next_batches"], [])

    def test_exact_old_result_is_reused_after_code_reverts(self):
        original = self.plan([browser_intent("view-state", "view.tsx", 1200)])
        receipts = MODULE.append_receipt(
            original, result_for(original["batches"][0], browser_calls=1), None
        )
        (self.root / "view.tsx").write_text("view.tsx v2\n", encoding="utf-8")
        changed = self.plan([browser_intent("view-state", "view.tsx", 1200)])
        receipts = MODULE.append_receipt(
            changed,
            result_for(changed["batches"][0], status="fail", browser_calls=1),
            receipts,
        )
        (self.root / "view.tsx").write_text("view.tsx v1\n", encoding="utf-8")
        reverted = self.plan([browser_intent("view-state", "view.tsx", 1200)])

        status = MODULE.summarize_status(reverted, receipts)

        self.assertTrue(status["ready"])
        self.assertEqual(status["intents"]["view-state"]["status"], "passed")

    def test_failed_assertion_marks_only_its_consumer_failed(self):
        plan = self.plan([
            browser_intent("t1", "view.tsx", 1200, consumer="T1-r1/restore"),
            browser_intent("t2", "style.css", 900, consumer="T2-r1/restore"),
        ])
        batch = plan["batches"][0]
        receipts = MODULE.append_receipt(
            plan, result_for(batch, ["t1"], status="fail", browser_calls=1), None
        )
        receipts = MODULE.append_receipt(
            plan, result_for(batch, ["t2"], browser_calls=1), receipts
        )

        status = MODULE.summarize_status(plan, receipts)

        self.assertEqual(status["consumers"]["T1-r1/restore"]["status"], "failed")
        self.assertEqual(status["consumers"]["T2-r1/restore"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
