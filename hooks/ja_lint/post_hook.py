"""Advisory PostToolUse hook for ja-lint.

Opt-in: it does nothing unless the project has a ``.claude/ja-lint/`` directory.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

REPOSITORY_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
OPT_IN = REPOSITORY_ROOT / ".claude" / "ja-lint"
LOG_PATH = REPOSITORY_ROOT / ".claude" / "logs" / "ja_lint" / "checked.jsonl"


def _written_path(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _append_check(path: Path, counts: Counter[str]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path.resolve()),
        "violations": dict(sorted(counts.items())),
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _warning(violation: Any) -> str:
    good = " / ".join(violation.good)
    return (
        f"ja-lint advisory [{violation.rule_id}] {violation.label} (line {violation.line})\n"
        f"  offending sentence: {violation.sentence}\n"
        f"  good patterns: {good}\n"
        "  (Advisory: No immediate rewrite required; keep this in mind for subsequent turns.)"
    )


def main() -> int:
    try:
        if os.environ.get("JA_LINT", "").lower() == "off":
            return 0
        if not OPT_IN.is_dir():
            return 0
        from core import check_file

        payload = json.load(sys.stdin)
        raw_path = _written_path(payload)
        if raw_path is None:
            return 0
        path = Path(raw_path)
        if not path.is_absolute():
            path = REPOSITORY_ROOT / path
        violations = check_file(path, project_only=True)
        counts: Counter[str] = Counter()
        if violations is not None:
            counts.update(violation.rule_id for violation in violations)
        _append_check(path, counts)
        for violation in violations or []:
            print(_warning(violation), file=sys.stderr)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
