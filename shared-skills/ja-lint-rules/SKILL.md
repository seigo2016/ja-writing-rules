---
name: ja-lint-rules
description: Use when a user corrects Japanese wording and that correction should become a permanent check, when adding or narrowing a ja-lint rule, when reviewing which rules fire too often or never, or when mining past transcripts for repeatedly-corrected expressions. Triggers: 日本語を指摘された, 表現を訂正された, 規則を追加, 規則を狭める, 誤検知を直す, 発火数を見直す, 会話履歴から規則候補を洗い出す.
---

# ja-lint 規則の登録と見直し

日本語検査 (ja-lint) の規則を登録し、見直す手順。
ja-lint は `ja-writing-rules` プラグインの PostToolUse フックである。Write と Edit のあとに、書かれた日本語のファイルを検査して警告を出す。警告は助言であり、作業を止めない。

規則の正本は `hooks/ja_lint/rules.jsonl` (`ja-writing-rules` のリポジトリ内) である。
SKILL.md 側に個々の禁止表現を書き足さない (二重管理になる)。

以下の `<ja-lint>` は、`$JA_WRITING_RULES_HOME/hooks/ja_lint` (既定 `~/.local/share/ja-writing-rules/hooks/ja_lint`) を指す。

## 規則を置く場所

| 置き場所 | 使いどころ |
|---|---|
| `<ja-lint>/rules.jsonl` | どのプロジェクトでも通用する規則。リポジトリを更新して配る |
| `<プロジェクト>/.claude/ja-lint/rules.jsonl` | そのプロジェクトだけの語・言い回しの規則。フックが上の規則に足して読む |

特定のプロジェクトの語や名前を、共有側の `rules.jsonl` に入れない。

## 守る原則

**推奨形のない規則を登録しない。**
禁止だけを与えるとエージェントは避け方が分からず、不自然な回避文を書く。
`good` は全規則必須である。

**実測を通らない規則を登録しない。**
指摘された文に当たること (MATCH) と、正当な文に当たらないこと (NO MATCH) を毎回コマンドで確かめる。
実測結果を示さずに「登録した」と報告しない。

**語のみの置換を促さない。**
`good` には、語の差し替えでなく、検出箇所を含む文の書き直し方を書く。
語だけを差し替えると同じ問題が別の語形で残り、文が破綻する。

## 規則の形

`rules.jsonl` は 1 行 1 規則の JSON Lines。

| 欄 | 意味 |
|---|---|
| `id` | 規則 id (下記の接頭辞規約に従う) |
| `pattern` | Python の正規表現。表面文字列だけで判定できる形にする |
| `severity` | 文字列。同梱の規則はすべて `warning`。現在のフックは重大度で挙動を変えない |
| `label` | 何が問題かを 1 行で。警告文にそのまま出る |
| `good` | 推奨置換形の配列。1 件以上必須 |
| `scenes` | 適用場面の配列。記録用で、検査の絞り込みには使わない |
| `enabled` | `false` で一時停止。誤検知の調査中に使う |
| `min_count` | この回数以上出たら指摘する。乱用系に使う。1 以上の整数 |

どの欄も省けない。欠けた欄や型の違う欄がある行は、警告を出さずに読み飛ばされる。

### 規則 id の接頭辞

| 接頭辞 | 由来 |
|---|---|
| `JT-` | 用語・命名に関する規則。既存の番号を保つ |
| `PR-` | 文章のリズムに関する規則。既存の番号を保つ |
| `UL-` | ユーザー指摘から学んだ規則。連番は `UL-001` から |
| `AGG-` | `checks.py` が文書全体を集計して出す検査 (文末の繰り返し、文体の混在)。`rules.jsonl` には置かない |

新規に採番するのは `UL-` だけである。

## 経路 1: 指摘された瞬間に登録する

主経路。
ユーザーが日本語を直したら、その場で規則を 1 本足す。

1. 直された文と、直した後の文を控える。
2. 何を禁じるのかを 1 行で書く (`label`)。指示対象を先に固定し、語より先に何を指しているかを決める。
3. 直した後の文から推奨形を 1 件以上取り出す (`good`)。ここで推奨形を取り出せないなら、その指摘はまだ規則にできない。判断が要る型として `ja-writing-rules` 側へ残す。
4. `pattern` を書く。正当な複合語に当たらないところまで狭める。
5. 実測する。`--test-rule` は読み込んだ規則の中から id を探すので、候補の 1 行を一時ファイルに書き、`CLAUDE_JA_LINT_RULES` でそのファイルを指して実行する。この変数は同梱の規則を置き換える。

```bash
CLAUDE_JA_LINT_RULES=<一時ファイル> python3 <ja-lint>/core.py --test-rule UL-NNN \
  --match "指摘された文をそのまま" \
  --no-match "当たってはいけない正当な文"
```

6. 両方の期待が通ったときだけ `rules.jsonl` へ 1 行追記する。落ちたら `pattern` を直して 5 に戻る。`UL-NNN` は、`rules.jsonl` にまだない番号にする。
7. 実測の出力を示して報告する。

登録した規則を後から試すときは、`CLAUDE_JA_LINT_RULES` を付けずに実行すると同梱の規則から探す。プロジェクト側の規則は、`CLAUDE_JA_LINT_RULES=<プロジェクト>/.claude/ja-lint/rules.jsonl` を付けて実行する。

### 狭め方の例

「会社の案内」に当たる規則を作りたいとき、`案内` だけを見る規則は「会社案内」「駅の案内板」にも当たる。

```bash
CLAUDE_JA_LINT_RULES=<一時ファイル> python3 <ja-lint>/core.py --test-rule UL-NNN \
  --match "会社の案内をご覧ください" \
  --no-match "駅の案内板を確認する"
```

NO MATCH が落ちるうちは登録しない。
助詞を含める、前後の語を限る、といった形で狭める。

## 送付済みの語が変わっていたとき

相手へ送った語が別語に変わっていることに気づいたら、その語だけを `UL-` 規則として、プロジェクト側の `rules.jsonl` に足す。

汎用の台帳は持たない。変わった語そのものを禁止する 1 本を書く。
`label` には元の語を書き、`good` には送付済みの語をそのまま挙げる。これで次からフックが警告を出す。

## 経路 2: 会話履歴から候補を洗い出す

人が指摘し忘れた表現も候補にするための経路。
週 1 を目安にする。

1. 直近の transcript の読み取りを別のエージェントへ委譲する (全文を自分で読まない)。
2. 繰り返し直している表現を候補として返させる。返すのは表現と実例だけで、規則の確定はさせない。
3. 候補 1 件ずつを経路 1 の手順 2 以降へ通す。実測は候補にも必須である。

## 経路 3: 発火数から見直す

規則が増えたあと、一度も当たらない規則と当たりすぎる規則を洗い出す。

記録先は `<プロジェクト>/.claude/logs/ja_lint/checked.jsonl`。
違反がなかったファイルも記録されるため、母数と発火数の両方が取れる。日本語が 30 字に満たず検査を飛ばしたファイルも違反なしとして入るので、母数はその分だけ多く出る。

```bash
python3 - <<'PY'
import json, collections, pathlib
p = pathlib.Path(".claude/logs/ja_lint/checked.jsonl")
c = collections.Counter()
files = 0
for line in p.read_text(encoding="utf-8").splitlines():
    try:
        rec = json.loads(line)
    except ValueError:
        continue
    files += 1
    for rule_id, n in (rec.get("violations") or {}).items():
        c[rule_id] += n
print(f"検査ファイル数: {files}")
for rule_id, n in c.most_common():
    print(f"{rule_id}\t{n}")
PY
```

見直しの判断:

- 発火 0 の規則: `pattern` が現実の書き方に当たっていないか、既に癖が消えている。前者なら直し、後者なら `enabled: false` にする。
- 発火が突出した規則: 誤検知を疑う。実際の検出箇所を数件見て、正当な文に当たっていれば `pattern` を狭める。

規則を消す前に、なぜ入れたかを `git log` で確かめる。

## 経路 4: レビュー指摘を取り込む

文章のレビューで入った指摘のうち、表現の型に関するものを候補へ回す。
人の指摘だけに依存しないための経路である。

指摘は診断と処方を分けて扱う。
診断 (この表現が読み手を誤導する) は候補にする。
処方 (この語に置き換えよ) はそのまま `good` にせず、推奨形として妥当か確かめてから入れる。

## 登録後

規則を足したら、直近に書いた日本語ファイルへ 1 度かけて誤検知が出ないことを見る。

```bash
python3 <ja-lint>/core.py <検査したいファイル>
```

誤検知が多くて作業の妨げになったら、`JA_LINT=off` で全体を止められる。
止めたまま忘れないよう、詰まった原因を規則側へ直してから戻す。
