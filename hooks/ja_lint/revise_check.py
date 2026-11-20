"""Compare a document before and after revising, and list what to check by hand.

    python3 revise_check.py <before> <after>
    python3 revise_check.py --git <file>      # before = the file at HEAD

Mirrors "直したあとに確かめること" in ja-writing-rules/reference/revising.md: new numbers and
names, guesses turned into assertions (or the reverse), changed negations, and changed quotes and
citations. It points at places; it does not judge them. Standard library only, no network.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from mask import mask_text

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*%?")
_ASCII_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*(?:\.[A-Za-z0-9_+-]+)*")
_KATAKANA_TERM = re.compile(r"[ァ-ヺー]{2,}")
_HEDGE = re.compile(
    r"と(?:考えられ|思われ|見られ|推測され|推定され)|だろう|であろう|かもしれ|可能性が|可能性も|"
    r"推測|見込み|おそらく|らしい|ようだ|ようです|疑われ|示唆"
)
_NEGATION = re.compile(r"ない|なく|ません|ず(?=[、。，．,\s]|$)")
_QUOTE = re.compile(r"「[^「」\n]+」|“[^”\n]+”|\"[^\"\n]+\"")
_CITATION = re.compile(r"\\cite[pt]?\{[^}]*\}|\[\d+(?:[,\-–]\s*\d+)*\]|\b(?:https?|ftp)://[^\s<>)]+")
_SENTENCE_END = re.compile(r"(?<=[。！？!?])|\n")
_FENCED = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _prose(text: str) -> str:
    # Citation markers are compared on their own below; their numbers are not facts in the prose.
    return _CITATION.sub(" ", _normalize(mask_text(text)))


def _sentences(prose: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(prose) if s and s.strip()]


def _terms(prose: str) -> set[str]:
    return set(_NUMBER.findall(prose)) | set(_ASCII_TERM.findall(prose)) | set(_KATAKANA_TERM.findall(prose))


def _with(pattern: re.Pattern[str], sentences: list[str]) -> list[str]:
    return [s for s in sentences if pattern.search(s)]


def compare(before: str, after: str) -> list[tuple[str, list[str]]]:
    """Sections of (heading, lines); a section with no lines had nothing to report."""
    old, new = _prose(before), _prose(after)
    old_sentences, new_sentences = _sentences(old), _sentences(new)
    old_set, new_set = set(old_sentences), set(new_sentences)
    old_terms, new_terms = _terms(old), _terms(new)
    old_numbers, new_numbers = set(_NUMBER.findall(old)), set(_NUMBER.findall(new))

    def changed(pattern: re.Pattern[str]) -> list[str]:
        gone = [f"- 前: {s}" for s in _with(pattern, old_sentences) if s not in new_set]
        came = [f"+ 後: {s}" for s in _with(pattern, new_sentences) if s not in old_set]
        return gone + came

    raw_old = _normalize(_FENCED.sub("", before))
    raw_new = _normalize(_FENCED.sub("", after))
    old_refs = set(_QUOTE.findall(raw_old)) | set(_CITATION.findall(raw_old))
    new_refs = set(_QUOTE.findall(raw_new)) | set(_CITATION.findall(raw_new))

    return [
        ("直した後にだけある数値・英字の語・カタカナの語 (元にない事実や固有名詞の候補)",
         sorted(new_terms - old_terms)),
        ("消えた数値", sorted(old_numbers - new_numbers)),
        ("推量の言い方を含む文で、変わったもの (確信の度合いが変わっていないか)", changed(_HEDGE)),
        ("否定を含む文で、変わったもの (畳んだあとも真偽が同じか)", changed(_NEGATION)),
        ("引用と出典で、変わったもの",
         [f"- 前だけ: {r}" for r in sorted(old_refs - new_refs)]
         + [f"+ 後だけ: {r}" for r in sorted(new_refs - old_refs)]),
    ]


MANUAL = (
    "手で確かめること (機械では決められない):",
    "- 元が主に置いた主張が、直したあとも主になっているか",
    "- 頼まれていない構成の変更 (見出し、箇条書きと地の文、段落の組み) をしていないか",
)


def render(sections: list[tuple[str, list[str]]]) -> str:
    out: list[str] = []
    for heading, lines in sections:
        out.append(f"## {heading}")
        out.extend(lines or ["(なし)"])
        out.append("")
    out.extend(MANUAL)
    return "\n".join(out)


def _at_head(path: Path) -> str:
    top = subprocess.run(["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, check=True).stdout.strip()
    relative = path.resolve().relative_to(Path(top).resolve())
    return subprocess.run(["git", "-C", top, "show", f"HEAD:{relative.as_posix()}"],
                          capture_output=True, text=True, check=True).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="直す前と直した後。--git のときは直した後だけ")
    parser.add_argument("--git", action="store_true", help="HEAD の版を直す前として比べる")
    args = parser.parse_args(argv)
    try:
        if args.git:
            if len(args.files) != 1:
                parser.error("--git には直した後のファイルを一つだけ渡す")
            after_path = args.files[0]
            before = _at_head(after_path)
        else:
            if len(args.files) != 2:
                parser.error("直す前と直した後の二つのファイルを渡す")
            before = args.files[0].read_text(encoding="utf-8")
            after_path = args.files[1]
        after = after_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"読めない: {error}", file=sys.stderr)
        return 2
    print(render(compare(before, after)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
