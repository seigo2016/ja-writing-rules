import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(path.parent.name for path in (ROOT / "shared-skills").glob("*/SKILL.md"))


class InitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.home = base / "home"
        for name in SKILLS:
            (self.home / "shared-skills" / name).mkdir(parents=True)
            (self.home / "shared-skills" / name / "SKILL.md").write_text("x")
        self.target = base / "consumer"
        self.target.mkdir()
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)
        self.settings_path = self.target / ".claude/settings.json"

    def init(self, mode: str, *extra: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, JA_WRITING_RULES_HOME=str(self.home))
        return subprocess.run([sys.executable, str(ROOT / "init.py"), mode, "--root", str(self.target), *extra],
                              text=True, capture_output=True, env=env)

    def test_skills_are_the_expected_set(self) -> None:
        self.assertEqual(SKILLS, ["ja-lint-rules", "ja-naming", "ja-prose", "ja-report",
                                  "ja-writing-rules", "slop-removal"])

    def test_plan_writes_nothing(self) -> None:
        result = self.init("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("link     .agents/skills/ja-prose", result.stdout)
        self.assertEqual(list(self.target.iterdir()), [self.target / ".git"])

    def test_apply_registers_plugin_and_links_and_keeps_other_settings(self) -> None:
        self.settings_path.parent.mkdir()
        self.settings_path.write_text(json.dumps({"enabledPlugins": {"other@market": True}, "model": "x"}))
        result = self.init("apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads(self.settings_path.read_text())
        self.assertEqual(settings["extraKnownMarketplaces"]["ja-writing-rules"],
                         {"source": {"source": "directory", "path": str(self.home)}, "autoUpdate": False})
        self.assertEqual(settings["enabledPlugins"], {"other@market": True, "ja-writing-rules@ja-writing-rules": True})
        self.assertEqual(settings["model"], "x")
        for name in SKILLS:
            link = self.target / ".agents/skills" / name
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(self.home / "shared-skills" / name))
        self.assertEqual(os.readlink(self.target / ".claude/skills"), "../.agents/skills")
        self.assertTrue((self.target / ".claude/ja-lint/rules.jsonl").is_file())
        self.assertFalse((self.target / ".claude/hooks").exists())

    def test_apply_twice_changes_nothing(self) -> None:
        self.init("apply")
        before = self.settings_path.read_text()
        result = self.init("apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings_path.read_text(), before)
        self.assertIn("kept     .claude/settings.json", result.stdout)

    def test_no_lint_leaves_the_hook_off(self) -> None:
        self.init("apply", "--no-lint")
        self.assertFalse((self.target / ".claude/ja-lint").exists())

    def test_refuses_to_replace_a_real_directory(self) -> None:
        real = self.target / ".agents/skills/ja-prose"
        real.mkdir(parents=True)
        (real / "keep.txt").write_text("mine")
        result = self.init("apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("conflict", result.stderr)
        self.assertTrue((real / "keep.txt").is_file())
        self.assertFalse(self.settings_path.exists())

    def test_relinks_a_stale_symlink(self) -> None:
        link = self.target / ".agents/skills/ja-prose"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.target)
        self.assertEqual(self.init("apply").returncode, 0)
        self.assertEqual(os.readlink(link), str(self.home / "shared-skills/ja-prose"))

    def test_refuses_a_different_marketplace_entry(self) -> None:
        self.settings_path.parent.mkdir()
        original = json.dumps({"extraKnownMarketplaces": {"ja-writing-rules": {"source": {"source": "github"}}}})
        self.settings_path.write_text(original)
        result = self.init("apply")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.settings_path.read_text(), original)

    def test_missing_home_is_an_error(self) -> None:
        env = dict(os.environ, JA_WRITING_RULES_HOME=str(self.home / "absent"))
        result = subprocess.run([sys.executable, str(ROOT / "init.py"), "plan", "--root", str(self.target)],
                                text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
