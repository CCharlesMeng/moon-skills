from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
            "analysis-spec",
            "slice-plan",
            "spec-check",
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
                    "--no-official",
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

    def test_reuses_local_official_skill_before_vendor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target-skills"
            official_root = Path(temp_dir) / "official-skills"
            official_skill = official_root / "brainstorming"
            official_skill.mkdir(parents=True)
            (official_skill / "SKILL.md").write_text("official", encoding="utf-8")
            (official_skill / "marker.txt").write_text("official-source", encoding="utf-8")

            with mock.patch.object(
                setup_skills,
                "build_search_roots",
                return_value=[target_dir, official_root],
            ), mock.patch.object(
                setup_skills,
                "stage_official_superpowers_install",
                side_effect=RuntimeError("official install not needed for this test"),
            ):
                exit_code = setup_skills.main(
                    [
                        "--target-dir",
                        str(target_dir),
                        "--mode",
                        "copy",
                        "--bundle",
                        "workflow",
                        "--write",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target_dir / "brainstorming" / "marker.txt").exists())

    def test_official_install_success_avoids_vendor_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"
            staging_root = Path(temp_dir) / "staging" / ".agents" / "skills"
            official_skill = staging_root / "brainstorming"
            official_skill.mkdir(parents=True)
            (official_skill / "SKILL.md").write_text("official", encoding="utf-8")
            (official_skill / "marker.txt").write_text("official-remote", encoding="utf-8")

            with (
                mock.patch.object(
                    setup_skills,
                    "build_search_roots",
                    return_value=[target_dir],
                ),
                mock.patch.object(
                    setup_skills,
                    "stage_official_superpowers_install",
                    return_value=staging_root,
                ) as install_mock,
            ):
                exit_code = setup_skills.main(
                    [
                        "--target-dir",
                        str(target_dir),
                        "--mode",
                        "copy",
                        "--bundle",
                        "workflow",
                        "--write",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target_dir / "brainstorming" / "marker.txt").exists())
            install_mock.assert_called_once()

    def test_official_install_failure_falls_back_to_vendor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"

            with (
                mock.patch.object(
                    setup_skills,
                    "build_search_roots",
                    return_value=[target_dir],
                ),
                mock.patch.object(
                    setup_skills,
                    "stage_official_superpowers_install",
                    side_effect=RuntimeError("official install failed"),
                ),
            ):
                exit_code = setup_skills.main(
                    [
                        "--target-dir",
                        str(target_dir),
                        "--mode",
                        "copy",
                        "--bundle",
                        "workflow",
                        "--write",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target_dir / "brainstorming" / "SKILL.md").exists())
            self.assertFalse((target_dir / "brainstorming" / "marker.txt").exists())

    def test_no_official_uses_vendor_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "skills"

            with mock.patch.object(
                setup_skills,
                "stage_official_superpowers_install",
            ) as install_mock:
                exit_code = setup_skills.main(
                    [
                        "--target-dir",
                        str(target_dir),
                        "--mode",
                        "copy",
                        "--bundle",
                        "workflow",
                        "--write",
                        "--no-official",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target_dir / "brainstorming" / "SKILL.md").exists())
            install_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
