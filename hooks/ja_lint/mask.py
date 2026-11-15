"""Mask non-prose spans without moving any source position."""

from __future__ import annotations

import re


_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?=\r?\n|\Z)", re.DOTALL)
_FENCED_CODE = re.compile(
    r"(?ms)(?:^[ \t]*(?P<backticks>`{3,})[^\n]*(?:\n.*?)*?^[ \t]*(?P=backticks)`*[ \t]*$"
    r"|^[ \t]*(?P<tildes>~{3,})[^\n]*(?:\n.*?)*?^[ \t]*(?P=tildes)~*[ \t]*$)"
)
_INLINE_CODE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`)[^\n]*?(?P=ticks)(?!`)")
_URL = re.compile(r"\b(?:https?|ftp)://[^\s<>]+")
_HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")


def _spaces(match: re.Match[str]) -> str:
    return "".join("\n" if character == "\n" else " " for character in match.group(0))


def mask_text(source: str) -> str:
    """Replace excluded spans by same-length spaces while retaining newlines."""
    masked = source
    for pattern in (_FRONTMATTER, _FENCED_CODE, _INLINE_CODE, _URL, _HTML_TAG):
        masked = pattern.sub(_spaces, masked)
    return masked
