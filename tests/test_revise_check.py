"""Tests for revise_check: each kind of change a revision can slip in is listed, and none when unchanged."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks" / "ja_lint"))
import revise_check  # noqa: E402

BEFORE = (
    "処理時間は 120 ms だった。原因は設定にあると考えられる。キャッシュは使わない。"
    "詳しくは「設定の手引き」を見る [3]。\n"
)
AFTER = "処理時間は 150 ms だった。原因は設定にある。キャッシュを使う。Redis を入れる。\n"


def section(sections, start):
    return next(lines for heading, lines in sections if heading.startswith(start))


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.sections = revise_check.compare(BEFORE, AFTER)

    def test_new_numbers_and_names_are_listed(self):
        added = section(self.sections, "直した後にだけある")
        self.assertIn("150", added)
        self.assertIn("Redis", added)
        self.assertNotIn("ms", added)

    def test_a_lost_number_is_listed(self):
        self.assertEqual(section(self.sections, "消えた数値"), ["120"])

    def test_a_guess_turned_into_an_assertion_is_listed(self):
        lines = section(self.sections, "推量")
        self.assertIn("- 前: 原因は設定にあると考えられる。", lines)

    def test_a_changed_negation_is_listed(self):
        lines = section(self.sections, "否定")
        self.assertIn("- 前: キャッシュは使わない。", lines)

    def test_a_dropped_quote_and_citation_are_listed(self):
        lines = section(self.sections, "引用")
        self.assertIn("- 前だけ: 「設定の手引き」", lines)
        self.assertIn("- 前だけ: [3]", lines)

    def test_nothing_is_listed_when_nothing_changed(self):
        for _, lines in revise_check.compare(BEFORE, BEFORE):
            self.assertEqual(lines, [])

    def test_code_is_not_read_as_prose(self):
        code = "```\nvalue = 999\n```\n"
        added = section(revise_check.compare(BEFORE, BEFORE + code), "直した後にだけある")
        self.assertNotIn("999", added)


class CliTest(unittest.TestCase):
    def test_git_mode_compares_with_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
            run("init", "-q")
            run("config", "user.email", "t@example.test")
            run("config", "user.name", "t")
            doc = repo / "doc.md"
            doc.write_text(BEFORE, encoding="utf-8")
            run("add", "doc.md")
            run("commit", "-qm", "before")
            doc.write_text(AFTER, encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "hooks" / "ja_lint" / "revise_check.py"),
                                     "--git", str(doc)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("150", result.stdout)
            self.assertIn("手で確かめること", result.stdout)


if __name__ == "__main__":
    unittest.main()
