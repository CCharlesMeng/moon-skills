from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import setup_skills


class SetupSkillsTests(unittest.TestCase):
    def test_workflow_bundle_resolves_recursive_dependencies(self) -> None:
        manifest = setup_skills.load_manifest(REPO_ROOT / "skills-manifest.json")
        skill_ids = setup_skills.resolve_bundle_skills(manifest, ["workflow"])

        for skill_id in (
            "initialize",
            "sync-context",
            "immune-debug",
            "audit",
            "brainstorming",
            "systematic-debugging",
            "writing-plans",
            "test-driven-development",
            "verification-before-completion",
            "subagent-driven-development",
            "executing-plans",
            "using-git-worktrees",
            "requesting-code-review",
            "finishing-a-development-branch",
        ):
            self.assertIn(skill_id, skill_ids)

        self.assertNotIn("openclaw-feishu-multi-agent", skill_ids)

    def test_auto_host_detection_uses_repo_local_parent(self) -> None:
        fake_repo_root = Path("/tmp/example/.agents/skills/moon-skills")
        detected = setup_skills.resolve_target_root(
            repo_root=fake_repo_root,
            host="auto",
            target_dir=None,
        )
        self.assertEqual(detected, fake_repo_root.parent)

    def test_all_bundle_installs_workflow_and_standalone(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"
            exit_code = setup_skills.main(
                [
                    "--target-dir",
                    str(target_dir),
                    "--mode",
                    "copy",
                    "--all",
                    "--write",
                ]
            )

            self.assertEqual(exit_code, 0)

            for skill_id in (
                "initialize",
                "brainstorming",
                "writing-plans",
                "openclaw-feishu-multi-agent",
            ):
                self.assertTrue((target_dir / skill_id / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
