"""Deterministic regex and document-level checks for Japanese prose."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from mask import mask_text


_SENTENCE_END = re.compile(r"[。！？!?]")
_BULLET_NOUN_STOP = re.compile(
    r"^\s*(?:[-*+]|[0-9０-９]+[.)）]|[・])\s*[^。！？!?]*$"
)
_POLITE_ENDING = re.compile(r"(?:ませんでした|ました|ません|ましょう|ます|でした|です|でしょう)\s*[。！？!?]\s*$")
@dataclass(frozen=True)
class Violation:
    rule_id: str
    severity: str
    label: str
    good: tuple[str, ...]
    line: int
    sentence: str


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    line: int
    text: str


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _next_prose_offset(masked: str, start: int, end: int) -> int | None:
    for index in range(start, end):
        if not masked[index].isspace():
            return index
    return None


_BLANK_LINE = re.compile(r"\n[ \t\u3000]*\n")


def _block_bounds(source: str, offset: int) -> tuple[int, int]:
    """Return the blank-line-delimited block containing ``offset``.

    A blank line ends a sentence even without a period, and so does the end of
    a heading line. Without this, a heading with no ``。`` merges into the next
    paragraph and the reported line number points at the heading instead of the
    line that actually violated the rule.
    """
    start = 0
    for match in _BLANK_LINE.finditer(source, 0, offset):
        start = match.end()
    tail = _BLANK_LINE.search(source, offset)
    end = tail.start() + 1 if tail else len(source)

    line_start = source.rfind("\n", 0, offset) + 1
    stripped = source[line_start:].split("\n", 1)[0].lstrip()
    if stripped.startswith("#"):
        # A heading is its own sentence.
        heading_end = source.find("\n", offset)
        return line_start, heading_end if heading_end >= 0 else len(source)
    # A heading above the offset also bounds the block from the left.
    for match in re.finditer(r"(?m)^\s{0,3}#{1,6}[^\n]*\n", source[start:offset]):
        start = start + match.end()
    return start, end


def sentence_at(source: str, masked: str, offset: int) -> tuple[int, str]:
    """Return the source sentence containing ``offset`` and its first line."""
    block_start, block_end = _block_bounds(source, offset)
    left = max(
        masked.rfind(mark, block_start, offset) for mark in ("。", "！", "？", "!", "?")
    )
    start = block_start if left < 0 else left + 1
    prose_start = _next_prose_offset(masked, start, offset + 1)
    if prose_start is None:
        prose_start = offset
    right_candidates = [
        found
        for mark in "。！？!?"
        for found in (masked.find(mark, offset, block_end),)
        if found >= 0
    ]
    end = min(right_candidates) + 1 if right_candidates else block_end
    text = source[prose_start:end].strip()
    return _line_number(source, prose_start), text


def _mask_bullet_noun_stops(source: str, masked: str) -> str:
    characters = list(masked)
    offset = 0
    for line in source.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        # Headings are excluded from the sentence-ending tally for the same
        # reason bullet noun-stops are: they are not prose sentences, and
        # counting them invents ending runs that no reader perceives.
        if _BULLET_NOUN_STOP.match(body) or re.match(r"^\s{0,3}#{1,6}\s", body):
            for index in range(offset, offset + len(body)):
                characters[index] = " "
        offset += len(line)
    return "".join(characters)


def _sentences(source: str, masked: str) -> list[Sentence]:
    """Split from the masked text but retain the matching original text."""
    sentences: list[Sentence] = []
    sentence_mask = _mask_bullet_noun_stops(source, masked)
    start = 0
    for match in _SENTENCE_END.finditer(sentence_mask):
        end = match.end()
        prose_start = _next_prose_offset(sentence_mask, start, end)
        if prose_start is not None:
            text = source[prose_start:end].strip()
            if text:
                sentences.append(Sentence(prose_start, end, _line_number(source, prose_start), text))
        start = end
    prose_start = _next_prose_offset(sentence_mask, start, len(source))
    if prose_start is not None:
        tail = source[prose_start:].strip()
        if tail:
            sentences.append(Sentence(prose_start, len(source), _line_number(source, prose_start), tail))
    return sentences


def _is_bullet_noun_stop(sentence: Sentence) -> bool:
    return bool(_BULLET_NOUN_STOP.match(sentence.text))


def _rule_violations(source: str, masked: str, rules: Iterable[dict[str, Any]]) -> list[Violation]:
    violations: list[Violation] = []
    for rule in rules:
        try:
            matches = list(re.finditer(rule["pattern"], masked, re.MULTILINE))
        except (KeyError, TypeError, re.error):
            continue
        if len(matches) < rule["min_count"]:
            continue
        # A threshold rule (min_count > 1) says the document overuses something.
        # That is one finding, not one per occurrence: reporting all of them
        # buries the other rules' output in noise.
        if rule["min_count"] > 1:
            matches = matches[:1]
        for match in matches:
            detection_offset = _next_prose_offset(masked, match.start(), match.end())
            line, sentence = sentence_at(source, masked, detection_offset or match.start())
            violations.append(
                Violation(rule["id"], rule["severity"], rule["label"], tuple(rule["good"]), line, sentence)
            )
    return violations


def _style_mixing_violations(source: str, masked: str) -> list[Violation]:
    classified: list[tuple[Sentence, str]] = []
    for sentence in _sentences(source, masked):
        if _is_bullet_noun_stop(sentence):
            continue
        if _POLITE_ENDING.search(sentence.text):
            classified.append((sentence, "丁寧体"))
        elif _SENTENCE_END.search(sentence.text):
            classified.append((sentence, "常体"))
    polite = [item for item in classified if item[1] == "丁寧体"]
    plain = [item for item in classified if item[1] == "常体"]
    total = len(classified)
    if not polite or not plain or total == 0:
        return []
    minority = polite if len(polite) < len(plain) else plain
    if len(minority) / total <= 0.20:
        return []
    sentence, style = minority[0]
    return [
        Violation(
            "AGG-STYLE-MIX",
            "warning",
            "です・ます調と常体が混在",
            ("文書内の文体を一方に統一する",),
            sentence.line,
            sentence.text,
        )
    ]


def check_text(source: str, rules: Iterable[dict[str, Any]]) -> list[Violation]:
    """Check source text and return all rule and aggregate violations."""
    masked = mask_text(source)
    return (
        _rule_violations(source, masked, rules)
        + _style_mixing_violations(source, masked)
    )
