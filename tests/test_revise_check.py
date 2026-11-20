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
        added = section(self.sections, "直したあとに増えた")
        self.assertIn("150", added)
        self.assertIn("Redis", added)
        self.assertNotIn("ms", added)

    def test_a_lost_number_is_listed(self):
        self.assertIn("120", section(self.sections, "直したあとに減った"))

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
        added = section(revise_check.compare(BEFORE, BEFORE + code), "直したあとに増えた")
        self.assertNotIn("999", added)


class MissedChangesTest(unittest.TestCase):
    """Changes the first version did not list (found by using it on this repository)."""

    def lines(self, before, after, start):
        return section(revise_check.compare(before, after), start)

    def test_negation_dropped_in_past_and_conditional_forms(self):
        self.assertIn("- 前: これは採らなかった。", self.lines("これは採らなかった。", "これは採った。", "否定や条件"))
        self.assertIn("- 前: 値がなければ止める。", self.lines("値がなければ止める。", "値があれば止める。", "否定や条件"))

    def test_conditions_are_listed_with_negations(self):
        lines = self.lines("設定が有効なら動く。", "設定が有効でも動く。", "否定や条件")
        self.assertIn("- 前: 設定が有効なら動く。", lines)

    def test_adverbs_ending_in_zu_are_not_negations(self):
        self.assertEqual(self.lines("まず、読む。", "まず、よく読む。", "否定や条件"), [])

    def test_a_frame_in_kanji_numerals_is_listed(self):
        self.assertIn("三つ", self.lines("理由がある。", "理由は三つある。", "直したあとに増えた"))

    def test_deshou_is_a_hedge(self):
        self.assertIn("- 前: 遅れるでしょう。", self.lines("遅れるでしょう。", "遅れます。", "推量"))

    def test_full_width_period_ends_a_sentence(self):
        self.assertIn("- 前: 警告は出ず.", self.lines("警告は出ず．次へ進む．", "警告は出る．次へ進む．", "否定や条件"))

    def test_a_repeated_value_is_counted(self):
        self.assertIn("5 (前 1 → 後 2)", self.lines("図は 5 枚。", "図は 5 枚。表も 5 枚。", "直したあとに増えた"))

    def test_names_in_inline_code_count(self):
        self.assertIn("revise_check.py", self.lines("道具を使う。", "`revise_check.py` を使う。", "直したあとに増えた"))


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
