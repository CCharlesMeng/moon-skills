from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import install_workflow_skills


class InstallWorkflowSkillsTests(unittest.TestCase):
    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = install_workflow_skills.main(
                    ["--target-dir", str(target_dir)]
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse(target_dir.exists())
            text = output.getvalue()
            self.assertIn("dry-run", text)
            self.assertIn("brainstorming", text)
            self.assertIn("systematic-debugging", text)

    def test_write_installs_expected_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"
            exit_code = install_workflow_skills.main(
                ["--target-dir", str(target_dir), "--write"]
            )

            self.assertEqual(exit_code, 0)

            for skill_name in (
                "initialize",
                "sync-context",
                "immune-debug",
                "audit",
                "brainstorming",
                "systematic-debugging",
            ):
                self.assertTrue((target_dir / skill_name / "SKILL.md").exists())

            self.assertFalse(any(target_dir.rglob("__pycache__")))

    def test_force_with_backup_keeps_previous_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"
            install_workflow_skills.main(["--target-dir", str(target_dir), "--write"])

            marker = target_dir / "initialize" / "marker.txt"
            marker.write_text("custom change", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = install_workflow_skills.main(
                    [
                        "--target-dir",
                        str(target_dir),
                        "--write",
                        "--force",
                        "--backup",
                    ]
                )

            self.assertEqual(exit_code, 0)
            backups = list(target_dir.glob("initialize.backup-*"))
            self.assertTrue(backups)
            self.assertTrue((backups[0] / "marker.txt").exists())
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
