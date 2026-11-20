"""Shared ja-lint entry points used by the PostToolUse hook and the command line."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Iterable

from checks import Violation, check_text
from mask import mask_text
from rules import RULES_PATH, load_rules


PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
_JAPANESE = re.compile(r"[ぁ-んァ-ヶ一-鿆々〆ヵヶ]")
# Prose only: in code and config files a "#" comment reads as a Markdown heading, and the rules
# are about prose (a YAML file with Japanese comments drew thousands of heading warnings).
PROSE_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".rst", ".tex"}


def is_disabled() -> bool:
    return os.environ.get("JA_LINT", "").lower() == "off"


def is_excluded(path: Path | str, project_only: bool = False) -> bool:
    """Skip instruction files, rule files and logs; with ``project_only``, files outside the project too."""
    try:
        resolved = Path(path).resolve()
        relative = resolved.relative_to(PROJECT_ROOT)
    except (OSError, ValueError):
        return project_only
    if resolved.name in {"CLAUDE.md", "AGENTS.md", "MEMORY.md", "rules.jsonl"}:
        return True
    return relative.parts[:2] == (".claude", "logs")


def check_file(
    path: Path | str, rules: Iterable[dict] | None = None, project_only: bool = False
) -> list[Violation] | None:
    """Return violations, or ``None`` when the path is intentionally skipped."""
    if is_disabled():
        return None
    candidate = Path(path)
    if candidate.suffix.lower() not in PROSE_SUFFIXES or is_excluded(candidate, project_only):
        return None
    try:
        source = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if len(_JAPANESE.findall(source)) < 30:
        return None
    return check_text(source, load_rules() if rules is None else rules)


def _format_violation(violation: Violation) -> str:
    return f"{violation.rule_id} line {violation.line}: {violation.label}: {violation.sentence}"


def _test_rule(rule_id: str, match_text: str, no_match_text: str) -> int:
    rules = {rule["id"]: rule for rule in load_rules(RULES_PATH)}
    rule = rules.get(rule_id)
    if rule is None:
        print(f"unknown rule: {rule_id}")
        return 2
    pattern = re.compile(rule["pattern"], re.MULTILINE)
    matched = len(list(pattern.finditer(mask_text(match_text)))) >= rule["min_count"]
    not_matched = len(list(pattern.finditer(mask_text(no_match_text)))) < rule["min_count"]
    print(f"{rule_id}: MATCH={'yes' if matched else 'no'} NO_MATCH={'yes' if not_matched else 'no'}")
    return 0 if matched and not_matched else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Japanese prose against ja-lint rules.")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--test-rule")
    parser.add_argument("--match")
    parser.add_argument("--no-match")
    arguments = parser.parse_args(argv)
    if arguments.test_rule:
        if arguments.match is None or arguments.no_match is None:
            parser.error("--test-rule requires --match and --no-match")
        return _test_rule(arguments.test_rule, arguments.match, arguments.no_match)
    if not arguments.file:
        parser.error("a file or --test-rule is required")
    violations = check_file(arguments.file)
    if violations is None:
        return 0
    for violation in violations:
        print(_format_violation(violation))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
