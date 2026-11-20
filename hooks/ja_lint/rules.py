"""Load the small, machine-readable ja-lint rule registry."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


BUILTIN_RULES_PATH = Path(__file__).with_name("rules.jsonl")
# CLAUDE_JA_LINT_RULES replaces the bundled rules (used to try a rule file in isolation).
RULES_PATH = Path(os.environ.get("CLAUDE_JA_LINT_RULES") or BUILTIN_RULES_PATH)


def project_rules_path() -> Path:
    """Rules that belong to the consuming project, added to the bundled ones."""
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return root / ".claude" / "ja-lint" / "rules.jsonl"
REQUIRED_KEYS = {
    "id": str,
    "pattern": str,
    "severity": str,
    "label": str,
    "scenes": list,
    "enabled": bool,
    "min_count": int,
}


def _valid_rule(value: Any) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("good"), list):
        return False
    for key, expected_type in REQUIRED_KEYS.items():
        if not isinstance(value.get(key), expected_type):
            return False
    if not value["id"] or not value["pattern"] or not value["label"]:
        return False
    if value["min_count"] < 1:
        return False
    # A rule without a recommended form leaves the writer guessing how to avoid it (ja-lint-rules).
    if not value["good"] or not all(isinstance(item, str) and item for item in value["good"]):
        return False
    if not all(isinstance(item, str) for item in value["scenes"]):
        return False
    try:
        re.compile(value["pattern"])
    except re.error:
        return False
    return True


def load_rules(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return valid, enabled JSONL rules; ignore every malformed line.

    Without ``path``: the bundled rules (or CLAUDE_JA_LINT_RULES) plus the
    project's own ``.claude/ja-lint/rules.jsonl`` when it exists.
    """
    if path is None:
        combined = load_rules(RULES_PATH)
        extra = project_rules_path()
        if extra.is_file() and extra != Path(RULES_PATH):
            combined += load_rules(extra)
        return combined
    loaded: list[dict[str, Any]] = []
    try:
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if _valid_rule(value) and value["enabled"]:
                    loaded.append(value)
    except OSError:
        return []
    return loaded
