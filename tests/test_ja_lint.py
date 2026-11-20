"""Tests for the ja-lint PostToolUse hook (opt-in, exclusions, rules)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "ja_lint" / "post_hook.py"
CORE = ROOT / "hooks" / "ja_lint" / "core.py"

# 30+ Japanese characters, with an unverified hedge that PR-014 flags.
BAD = "この変更は性能を大きく改善すると思われる。原因は設定の読み込みにあるだろう。確認はしていない。さらに詳しい調査が必要である。\n"
CLEAN = "設定ファイルを読み込み、結果をログに出力する。失敗したときは終了コードを返す。手順は三つある。\n"


def run_hook(project: Path, file_path: Path | str, extra_env: dict | None = None):
    env = {k: v for k, v in os.environ.items() if k not in ("JA_LINT", "CLAUDE_JA_LINT_RULES")}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra_env or {})
    payload = json.dumps({"tool_input": {"file_path": str(file_path)}})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, text=True, capture_output=True, env=env, cwd=project
    )


class PostHookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name: str, text: str) -> Path:
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def opt_in(self):
        (self.project / ".claude" / "ja-lint").mkdir(parents=True)

    def test_without_opt_in_is_silent_and_writes_nothing(self):
        path = self.write("doc.md", BAD)
        result = run_hook(self.project, path)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertFalse((self.project / ".claude").exists())

    def test_opt_in_warns_and_logs(self):
        self.opt_in()
        path = self.write("doc.md", BAD)
        result = run_hook(self.project, path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("PR-014", result.stderr)
        log = self.project / ".claude" / "logs" / "ja_lint" / "checked.jsonl"
        entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("PR-014", entry["violations"])

    def test_clean_prose_has_no_warning(self):
        self.opt_in()
        result = run_hook(self.project, self.write("doc.md", CLEAN))
        self.assertEqual(result.stderr, "")

    def test_excluded_and_outside_files_are_skipped(self):
        self.opt_in()
        for name in ("CLAUDE.md", "AGENTS.md", ".claude/logs/x.md"):
            self.assertEqual(run_hook(self.project, self.write(name, BAD)).stderr, "", name)
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "doc.md"
            outside.write_text(BAD, encoding="utf-8")
            self.assertEqual(run_hook(self.project, outside).stderr, "")

    def test_short_or_non_japanese_files_are_skipped(self):
        self.opt_in()
        self.assertEqual(run_hook(self.project, self.write("a.md", "確認はしていないだろう。\n")).stderr, "")
        self.assertEqual(run_hook(self.project, self.write("b.py", "print('hello')\n")).stderr, "")

    def test_kill_switch(self):
        self.opt_in()
        result = run_hook(self.project, self.write("doc.md", BAD), {"JA_LINT": "off"})
        self.assertEqual(result.stderr, "")

    def test_bad_input_never_fails(self):
        self.opt_in()
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)}
        for stdin in ("", "not json", "[]", '{"tool_input": 3}'):
            result = subprocess.run([sys.executable, str(HOOK)], input=stdin, text=True, capture_output=True, env=env)
            self.assertEqual(result.returncode, 0, stdin)

    def test_project_rules_are_added(self):
        self.opt_in()
        rule = {
            "id": "UL-001", "pattern": "サンプル語", "severity": "warning", "label": "サンプル語を使った",
            "good": ["別の語を使う"], "scenes": [], "enabled": True, "min_count": 1,
        }
        (self.project / ".claude" / "ja-lint" / "rules.jsonl").write_text(
            json.dumps(rule, ensure_ascii=False) + "\n" + "broken line\n", encoding="utf-8"
        )
        path = self.write("doc.md", "ここでサンプル語を使う。" + CLEAN)
        self.assertIn("UL-001", run_hook(self.project, path).stderr)

    def test_only_prose_files_are_checked(self):
        self.opt_in()
        for name in ("watch.yaml", "tool.py"):
            path = self.write(name, "# 実行中・保留の一覧\n" + BAD)
            self.assertEqual(run_hook(self.project, path).stderr, "", name)
        for name in ("note.md", "paper.tex", "memo.txt"):
            self.assertIn("PR-014", run_hook(self.project, self.write(name, BAD)).stderr, name)

    def test_a_rule_without_a_recommended_form_is_ignored(self):
        self.opt_in()
        rule = {
            "id": "UL-901", "pattern": "サンプル語", "severity": "warning", "label": "サンプル語を使った",
            "good": [], "scenes": [], "enabled": True, "min_count": 1,
        }
        (self.project / ".claude" / "ja-lint" / "rules.jsonl").write_text(
            json.dumps(rule, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        path = self.write("doc.md", "ここでサンプル語を使う。" + CLEAN)
        self.assertNotIn("UL-901", run_hook(self.project, path).stderr)

    def test_no_project_specific_rule_ships(self):
        text = (ROOT / "hooks" / "ja_lint" / "rules.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("decidability", text)


class CliTest(unittest.TestCase):
    def run_core(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "JA_LINT"}
        return subprocess.run([sys.executable, str(CORE), *args], text=True, capture_output=True, env=env)

    def test_test_rule_reports_match_and_no_match(self):
        result = self.run_core("--test-rule", "PR-014", "--match", "原因は設定にあるだろう。", "--no-match", "原因は設定にある。")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("MATCH=yes NO_MATCH=yes", result.stdout)

    def test_file_check_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.md"
            bad.write_text(BAD, encoding="utf-8")
            good = Path(tmp) / "good.md"
            good.write_text(CLEAN, encoding="utf-8")
            self.assertEqual(self.run_core(str(bad)).returncode, 1)
            self.assertEqual(self.run_core(str(good)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
