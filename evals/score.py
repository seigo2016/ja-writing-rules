"""Score the outputs of run.py: mechanical checks, then a judge model that does not see the condition.

    python3 evals/score.py --out <dir> [--judge opus] [--jobs 4]

Writes scores.json and prints a table of pass rates per task, condition and model.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "evals" / "tasks"
INPUT_NUMBERS = {
    "t1-design": {"1"},
    "t2-record": {"12", "0.42", "0.61", "3", "1.3"},
    "t3-report": {"3", "02", "10", "2"},
}
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def mechanical(task: str, text: str) -> dict[str, bool]:
    checks: dict[str, bool] = {"answer_written": bool(text.strip())}
    if task in INPUT_NUMBERS:
        checks["no_new_numbers"] = set(_NUMBER.findall(text)) <= INPUT_NUMBERS[task]
    if task == "t4-revise":
        checks["numbers_kept"] = all(n in text for n in ("120", "45", "5"))
        checks["hedge_kept"] = bool(re.search(r"考えられ|推測|と見られ|可能性", text))
        checks["no_section_preview"] = "本節では" not in text
        checks["no_metaphor_kiku"] = not re.search(r"効い|効く", text)
        checks["no_hedge_disclaimer"] = "目安であって" not in text
        checks["no_negated_contrast"] = "魔法ではなく" not in text
        checks["double_negation_truth_kept"] = not re.search(r"メモリ[^。]*増えない。", text) or "とは言えない" in text
    if task == "t5-scope":
        for name, fixed in {"ui_label": "「保存して閉じる」", "file_name": "`config.yaml`", "key": "`retry_limit`",
                            "legal_quote": "「本サービスは、予告なく変更されることがあります」",
                            "quote": "「設定は月に一度しか変えない」"}.items():
            checks[f"kept_{name}"] = fixed in text
        checks["prose_fixed"] = "検討を行う" not in text
    return checks


RUBRIC = """あなたは日本語の技術文書の採点者です。依頼と入力と出力を読み、次の各項目を 1 (満たす) か 0 (満たさない) で採点してください。当てはまらない項目は null にしてください。
R1 入力にない事実・数値・原因を足していない
R2 確かめていないことを、推測や未確認だと分かる形で書いている (直す依頼では、元の確信の度合いを保っている)
R3 最初の文が、読み手が最初に知るべきこと (結論、結果、要点) になっている (直す依頼では null)
R4 中身のない文 (文書について述べる予告、飾り、「A ではなく B」の対比、予防線) がない
R5 比喩や擬人化で、何が起きるかを隠していない
R6 一文に複数の主張を詰め込んでおらず、名詞の連鎖で関係が読めなくなっていない
出力は JSON だけにしてください: {"R1": 0, "R2": 1, "R3": null, "R4": 1, "R5": 1, "R6": 1, "note": "短い理由"}"""


def judge(task: str, text: str, model: str) -> dict:
    request = (TASKS / f"{task}.md").read_text(encoding="utf-8")
    inputs = "".join(f"\n--- 入力 {p.name} ---\n{p.read_text(encoding='utf-8')}"
                     for p in sorted(TASKS.glob(f"{task.split('-')[0]}-*.md")) if p.name != f"{task}.md")
    prompt = f"{RUBRIC}\n\n--- 依頼 ---\n{request}{inputs}\n--- 出力 ---\n{text}"
    result = subprocess.run(["claude", "-p", "--model", model, "--setting-sources", "project,local", prompt],
                            capture_output=True, text=True, timeout=600)
    match = re.search(r"\{.*\}", result.stdout, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {"error": result.stdout[-200:]}
    except json.JSONDecodeError:
        return {"error": result.stdout[-200:]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--judge", default="opus")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    runs = json.loads((args.out / "runs.json").read_text(encoding="utf-8"))

    def score(run: dict) -> dict:
        text = (args.out / f"{run['name']}.md").read_text(encoding="utf-8")
        return {**run, "mechanical": mechanical(run["task"], text),
                "judge": judge(run["task"], text, args.judge) if text.strip() else {}}

    with ThreadPoolExecutor(args.jobs) as pool:
        scored = list(pool.map(score, runs))
    (args.out / "scores.json").write_text(json.dumps(scored, ensure_ascii=False, indent=1), encoding="utf-8")

    table: dict[tuple, list[float]] = defaultdict(list)
    for s in scored:
        values = list(s["mechanical"].values()) + [v for k, v in s["judge"].items() if k.startswith("R") and v is not None]
        table[(s["task"], s["model"], s["condition"])].append(sum(map(float, values)) / max(len(values), 1))
    print("task\tmodel\tbase\tskill")
    for task, model in sorted({(t, m) for t, m, _ in table}):
        cells = [table.get((task, model, c), []) for c in ("base", "skill")]
        print(task, model, *(f"{sum(c) / len(c):.2f} (n={len(c)})" if c else "-" for c in cells), sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
