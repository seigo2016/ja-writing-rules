#!/usr/bin/env python3
"""Register ja-writing-rules in a consumer repository.

ja-writing-rules is read in place from one clone ($JA_WRITING_RULES_HOME, default
~/.local/share/ja-writing-rules). This script writes only what belongs to the consumer:
the marketplace and plugin entries in .claude/settings.json (the plugin provides the
writing-lint hook), symlinks .agents/skills/<name> -> $JA_WRITING_RULES_HOME/shared-skills/<name>
(Codex reads .agents/skills/; Claude reads it through .claude/skills -> ../.agents/skills),
and .claude/ja-lint/rules.jsonl, the marker that turns the lint hook on for this project.
It copies no skill or hook. It never replaces a real file or directory.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SOURCE = Path(__file__).resolve().parent
MARKETPLACE = "ja-writing-rules"
PLUGIN = "ja-writing-rules@ja-writing-rules"
SKILLS_DIR = Path(".agents/skills")
CLAUDE_SKILLS = Path(".claude/skills")
LINT_RULES = Path(".claude/ja-lint/rules.jsonl")


def writing_rules_home() -> Path:
    return Path(os.environ.get("JA_WRITING_RULES_HOME") or Path.home() / ".local/share/ja-writing-rules").expanduser()


def update_settings(root: Path, home: Path, apply: bool) -> str:
    """Add the marketplace and enable the plugin; never change an existing, different entry."""
    path = root / ".claude/settings.json"
    existed = path.exists()
    data = json.loads(path.read_text(encoding="utf-8")) if existed else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    wanted = {"source": {"source": "directory", "path": str(home)}, "autoUpdate": False}
    marketplaces = data.setdefault("extraKnownMarketplaces", {})
    enabled = data.setdefault("enabledPlugins", {})
    if not isinstance(marketplaces, dict) or not isinstance(enabled, dict):
        raise ValueError(f"{path}: extraKnownMarketplaces and enabledPlugins must be objects")
    changed = False
    if MARKETPLACE not in marketplaces:
        marketplaces[MARKETPLACE] = wanted
        changed = True
    elif marketplaces[MARKETPLACE] != wanted:
        return "conflict"
    if PLUGIN not in enabled:
        enabled[PLUGIN] = True
        changed = True
    if changed and apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ("update" if existed else "create") if changed else "kept"


def skill_names(home: Path) -> list[str]:
    shared = home / "shared-skills"
    if not shared.is_dir():
        raise ValueError(f"{shared} does not exist; set JA_WRITING_RULES_HOME to a ja-writing-rules clone")
    return sorted(path.name for path in shared.iterdir() if (path / "SKILL.md").is_file())


def link_state(link: Path, target: Path) -> str:
    if link.is_symlink():
        return "kept" if os.readlink(link) == str(target) else "relink"
    return "conflict" if link.exists() else "link"


def skill_links(root: Path, home: Path) -> list[tuple[Path, Path, str]]:
    """(link, target, state) per shared skill, in .agents/skills and, when it is a real directory, .claude/skills."""
    directories = [SKILLS_DIR]
    if (root / CLAUDE_SKILLS).is_dir() and not (root / CLAUDE_SKILLS).is_symlink():
        directories.append(CLAUDE_SKILLS)
    return [
        (directory / name, home / "shared-skills" / name,
         link_state(root / directory / name, home / "shared-skills" / name))
        for directory in directories
        for name in skill_names(home)
    ]


def claude_skills_state(root: Path) -> str:
    return "kept" if (root / CLAUDE_SKILLS).is_symlink() or (root / CLAUDE_SKILLS).exists() else "link"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--root", required=True, type=Path, help="the consumer repository")
    parser.add_argument("--no-lint", action="store_true",
                        help="do not create .claude/ja-lint/rules.jsonl (the lint hook then stays off)")
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / ".git").exists():
        parser.error(f"--root is not a Git repository: {root}")
    home = writing_rules_home()
    try:
        settings_state = update_settings(root, home, False)
        links = skill_links(root, home)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    lint_state = "kept" if (root / LINT_RULES).exists() or args.no_lint else "create"
    claude_link = claude_skills_state(root)
    print(f"{settings_state:8} .claude/settings.json")
    for link, target, state in links:
        print(f"{state:8} {link} -> {target}")
    print(f"{claude_link:8} {CLAUDE_SKILLS} -> ../.agents/skills")
    if not args.no_lint:
        print(f"{lint_state:8} {LINT_RULES}")
    failed = False
    if settings_state == "conflict":
        print(f"Refusing to overwrite extraKnownMarketplaces.{MARKETPLACE} in {root / '.claude/settings.json'}",
              file=sys.stderr)
        failed = True
    for link, _, state in links:
        if state == "conflict":
            print(f"conflict: {root / link} is a real file or directory; delete the consumer's copy and run again",
                  file=sys.stderr)
            failed = True
    if failed:
        return 2
    if args.mode == "apply":
        update_settings(root, home, True)
        (root / SKILLS_DIR).mkdir(parents=True, exist_ok=True)
        for link, target, state in links:
            if state != "kept":
                (root / link).unlink(missing_ok=True)
                (root / link).symlink_to(target)
        if claude_link == "link":
            (root / CLAUDE_SKILLS).parent.mkdir(parents=True, exist_ok=True)
            (root / CLAUDE_SKILLS).symlink_to("../.agents/skills")
        if lint_state == "create":
            (root / LINT_RULES).parent.mkdir(parents=True, exist_ok=True)
            (root / LINT_RULES).write_text("", encoding="utf-8")
    if home.resolve() != SOURCE:
        print(f"note: this clone ({SOURCE}) is not JA_WRITING_RULES_HOME ({home}); the plugin is read from {home}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
