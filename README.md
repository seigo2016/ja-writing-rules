# ja-writing-rules

読み手が一度で受け取れる日本語を書くための規約と、Claude 用のスキル。

> **Status: experimental.** 個人の作業のなかで書いた規約をそのまま公開している。内容も構成も変わりうる。

規約の全文は [shared-skills/ja-writing-rules/SKILL.md](shared-skills/ja-writing-rules/SKILL.md) にある。

## 何のためのものか

三つの場面を想定している。

- 技術文書。README、設計文書、仕様書、リリースノート、commit message
- 研究の記録と論文の草稿
- AI が人に返す報告文。読み手は、技術の分かる共同作業者である

## 配布のしくみ

スキルはリポジトリ内の `shared-skills/` にあり、フックは Claude Code プラグインとして配る。

- 利用側は、このリポジトリのクローンを一つだけ持つ。既定の場所は `~/.local/share/ja-writing-rules`。環境変数 `JA_WRITING_RULES_HOME` で変えられる
- 利用側のプロジェクトは、`.agents/skills/<スキル名>` を、クローン内の `shared-skills/<スキル名>` へのシンボリックリンクにする。`.claude/skills` は `../.agents/skills` へのリンクにする。Claude と Codex が同じファイルを読む
- プラグインはフックだけを提供する。スキルを提供しない。プラグインの `skills/` はスキルを自動で読み込むため、スキルを `shared-skills/` に置いて二重読み込みを避けている

```
shared-skills/
├── ja-writing-rules/   規約の本体 (SKILL.md と reference/ の報告文、命名、推敲、論証)
├── ja-naming/          命名。規則は ja-writing-rules/reference/naming.md を参照
├── ja-report/          報告文。規則は ja-writing-rules/reference/reports.md を参照
├── ja-prose/           技術文書のリズムと論理密度、推敲の手順、検査スクリプトの使い方
├── slop-removal/       AI 生成文に出る型の除去
└── ja-lint-rules/      検査規則の登録と見直し
hooks/                  PostToolUse の検査フック (ja_lint/)
.claude-plugin/         plugin.json と marketplace.json
init.py                 利用側への登録
```

同じ規則を複数の場所に書かない。規則の正本は `ja-writing-rules` にあり、ほかのスキルは参照する。

## インストール

1. クローンを置く。

```bash
git clone <このリポジトリの URL> ~/.local/share/ja-writing-rules
```

別の場所に置くなら `JA_WRITING_RULES_HOME` を設定する。

2. 利用側のプロジェクトで登録する。まず `plan` で何が変わるかを見る。

```bash
python3 ~/.local/share/ja-writing-rules/init.py plan --root <プロジェクト>
python3 ~/.local/share/ja-writing-rules/init.py apply --root <プロジェクト>
```

`init.py` がするのは次の三つだけである。スキルもフックもコピーしない。

- `.claude/settings.json` に `extraKnownMarketplaces` (種別 `directory`、パスは `$JA_WRITING_RULES_HOME`) と、`enabledPlugins` の `ja-writing-rules@ja-writing-rules` を書く。既にある別の設定は変えない
- `.agents/skills/<スキル名>` のシンボリックリンクを作り、無ければ `.claude/skills` を `../.agents/skills` へのリンクにする。実ファイルや実ディレクトリがあるときは置き換えず、エラーで止まる
- `.claude/ja-lint/rules.jsonl` を空で作る。フックを有効にする目印である。要らなければ `--no-lint` を付ける

更新はクローンで `git pull` するだけでよい。利用側のプロジェクトは何も変えなくてよい。

テストは `python3 -m unittest discover -s tests` で動く。

## 検査フック (ja-lint)

Write と Edit のあとに、書かれた日本語のファイルを機械的に検査し、該当する規則の警告を出す。警告は助言であり、作業を止めない。

フックは、プロジェクトに `.claude/ja-lint/` ディレクトリがあるときだけ動く。無いプロジェクトでは何も検査せず、何も書かない。

動いているときの検査対象は次の条件で決まる。

- プロジェクトの中のファイルだけを検査する
- 日本語の文字が 30 字以上あるファイルだけを検査する。コードブロック、インラインコード、URL、HTML タグ、フロントマターは除いて検査する
- `CLAUDE.md`、`AGENTS.md`、`MEMORY.md`、`rules.jsonl`、`.claude/logs/` 以下は検査しない
- 環境変数 `JA_LINT=off` で止められる

規則は `hooks/ja_lint/rules.jsonl` にある。プロジェクト固有の規則は `.claude/ja-lint/rules.jsonl` に書くと、同梱の規則に足して読まれる。規則の足し方は `ja-lint-rules` スキルにある。検査した記録は `.claude/logs/ja_lint/checked.jsonl` に残る。

## 使い方

規約として読むなら [shared-skills/ja-writing-rules/SKILL.md](shared-skills/ja-writing-rules/SKILL.md) を開く。

Claude Code だけで、シンボリックリンクを使わずに試すなら、スキルをコピーしてもよい。更新は追従しない。

```bash
cp -r shared-skills/ja-writing-rules <プロジェクト>/.claude/skills/
```

人に読ませる日本語を書くときスキルが起動する。引用文、法令の定型表現、コード識別子、既存 UI のラベルには適用しない。

## 何を書いてあるか

| 章 | 内容 |
|---|---|
| 報告文 | 結論を先頭に置く。観測と推測を分ける。根拠を示す。強調を絞る |
| 語と名前 | 直訳のカタカナ語を作らない。名前を作る前に既存の語を探す。一つの対象に一つの語 |
| 文と段落 | 能動態を優先する。名詞が四つ以上つながったら動詞に開く。起きることを語で書く。否定を畳んでも真偽を保つ。中身のない文と語を削る。一段落に一つの話題 |
| 人の文書を直す | 確信の度合い、数、主張の重さ、構成を変えない。意味が決まらなければ書き手に問う |
| 論証 | 因果に仕組みを添える。例の範囲に主張を狭める。譲歩のあとは論を進める |
| 決まったこと | 送った語は変えない。仕様の語を黙って言い換えない |
| 症状から引く | 読みにくさの症状から直し方を引く表 |

専門用語は読み手で決める。読み手が理解する語なら使ってよい。求めるのは、初出で定義を置くことと、一つの意味で使い続けることの二つだけである。

文の語数は数えない。判断は一文一義と、一段落に一つの話題で行う。

## 対応モデル

Sonnet 以上を勧める。Haiku では、渡していない事実を書くことがある。報告文と設計文書では、この失敗が読み手の判断を直接誤らせる。

観測した内容は [docs/evaluations.md](docs/evaluations.md) にある。

## 参考にした資料

[Federal Plain Language Guidelines](https://www.plainlanguage.gov/guidelines/) の考え方を参考にした。一覧は [SKILL.md](shared-skills/ja-writing-rules/SKILL.md#参考にした資料) にある。

調査したが採用しなかった資料と、その理由は [docs/design-notes.md](docs/design-notes.md) に書く。

## ライセンス

MIT License。[LICENSE](LICENSE) を参照。

外部リポジトリのファイルは含めない。規則は、次の外部のスキルを参考に書き下ろした。

- [natural-japanese](https://github.com/coji/natural-japanese) (MIT License)
- [meiseki](https://github.com/bamboo-nova/meiseki) (MIT License)
- [japanese-tech-writing](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d) (Unlicense)
- [yomiyasu](https://github.com/nanaism/yomiyasu) (MIT License)
- [skill-deslop](https://github.com/stephenturner/skill-deslop) (MIT License)
- [humanizer](https://github.com/jooray/humanizer) (MIT License)

何を採り、何を採らなかったかは [docs/design-notes.md](docs/design-notes.md) にある。検査スクリプトと詳しい一覧は、それらが入っているときだけ使う。使い方は `ja-prose` と `slop-removal` の SKILL.md にある。
