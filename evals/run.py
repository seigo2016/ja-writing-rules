"""Run the evaluation: each task, with and without the skills, on several models.

    python3 evals/run.py --out <dir> [--reps sonnet=3,opus=3,haiku=1] [--jobs 4]

Each run gets a fresh project. "skill" registers this repository with init.py (skills and the
ja-lint hook); "base" leaves the project empty. Both start Claude Code with only the project's
settings (--setting-sources project,local), so the user's own plugins stay out. The user's
CLAUDE.md is read in both conditions alike.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "evals" / "tasks"
# task id -> (request file, {input file in the task dir: name in the project}, file the answer goes to)
TASK_FILES = {
    "t1-design": ("t1-design.md", {}, "design.md"),
    "t2-record": ("t2-record.md", {}, "record.md"),
    "t3-report": ("t3-report.md", {}, "report.md"),
    "t4-revise": ("t4-revise.md", {"t4-draft.md": "draft.md"}, "draft.md"),
    "t5-scope": ("t5-scope.md", {"t5-notice.md": "notice.md"}, "notice.md"),
}


def run_one(out: Path, task: str, condition: str, model: str, rep: int) -> dict:
    request, inputs, answer = TASK_FILES[task]
    name = f"{task}.{condition}.{model}.{rep}"
    with tempfile.TemporaryDirectory(prefix="ja-eval-") as tmp:
        project = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        for source, target in inputs.items():
            shutil.copy(TASKS / source, project / target)
        env = {**os.environ, "JA_WRITING_RULES_HOME": str(ROOT)}
        if condition == "skill":
            subprocess.run(["python3", str(ROOT / "init.py"), "apply", "--root", str(project)],
                           cwd=project, env=env, check=True, capture_output=True)
        try:
            result = subprocess.run(
                ["claude", "-p", "--model", model, "--setting-sources", "project,local",
                 "--permission-mode", "acceptEdits", (TASKS / request).read_text(encoding="utf-8")],
                cwd=project, env=env, capture_output=True, text=True, timeout=900)
            stdout, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired:
            stdout, code = "", -1
        produced = project / answer
        text = produced.read_text(encoding="utf-8") if produced.exists() else ""
        hook_log = project / ".claude" / "logs" / "ja_lint" / "checked.jsonl"
        hook_runs = len(hook_log.read_text(encoding="utf-8").splitlines()) if hook_log.exists() else 0
    (out / f"{name}.md").write_text(text, encoding="utf-8")
    (out / f"{name}.stdout.txt").write_text(stdout, encoding="utf-8")
    return {"name": name, "task": task, "condition": condition, "model": model, "rep": rep,
            "exit": code, "answer_written": bool(text), "hook_runs": hook_runs}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reps", default="sonnet=3,opus=3,haiku=1")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--tasks", default=",".join(TASK_FILES), help="走らせるタスクの id (カンマ区切り)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    reps = {m: int(n) for m, n in (item.split("=") for item in args.reps.split(","))}
    jobs = [(t, c, m, r) for t in args.tasks.split(",") for c in ("base", "skill") for m, n in reps.items() for r in range(1, n + 1)]
    with ThreadPoolExecutor(args.jobs) as pool:
        runs = list(pool.map(lambda j: run_one(args.out, *j), jobs))
    (args.out / "runs.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(runs)} runs, {sum(r['answer_written'] for r in runs)} answers written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
