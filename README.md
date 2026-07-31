# ja-writing-rules

読み手が一度で受け取れる日本語を書くための規約と、Claude 用のスキル。

> **Status: experimental.** 個人の作業のなかで書いた規約をそのまま公開している。内容も構成も変わりうる。

規約の全文は [skills/ja-writing-rules/SKILL.md](skills/ja-writing-rules/SKILL.md) にある。

## 何のためのものか

三つの場面を想定している。

- AI が人に返す報告文。Slack やチャット経由で、エンジニアでない読み手に届く場合を含む
- README・設計文書・仕様書・リリースノート・commit message
- エンジニアでない読み手に向けた案内文と通知文

## 使い方

規約として読むなら [skills/ja-writing-rules/SKILL.md](skills/ja-writing-rules/SKILL.md) を開く。

Claude Code で使うなら、`skills/ja-writing-rules/` をスキルの置き場所に配置する。

```bash
# 一つのプロジェクトで使う
cp -r skills/ja-writing-rules <プロジェクト>/.claude/skills/

# すべてのプロジェクトで使う
cp -r skills/ja-writing-rules ~/.claude/skills/
```

規約と参照先はスキルの中にあるので、このコピーだけで完結する。

```
skills/ja-writing-rules/
├── SKILL.md              規約の本体
└── reference/
    ├── reports.md        報告文
    └── naming.md         命名と訳語
```

人に読ませる日本語を書くときスキルが起動する。引用文、法令の定型表現、コード識別子、既存 UI のラベルには適用しない。

## 何を書いてあるか

| 章 | 内容 |
|---|---|
| 報告文 | 結論を先頭に置く。観測と推測を分ける。根拠を示す。強調を絞る |
| 語と名前 | 直訳のカタカナ語を作らない。名前を作る前に既存の語を探す。一つの対象に一つの語 |
| 文と段落 | 能動態を優先する。名詞が四つ以上つながったら動詞に開く。一段落に一つの話題 |
| 決まったこと | 送った語は変えない。仕様の語を黙って言い換えない |
| 症状から引く | 読みにくさの症状から直し方を引く表 |

専門用語は読み手で決める。読み手が理解する語なら使ってよい。求めるのは、初出で定義を置くことと、一つの意味で使い続けることの二つだけである。

文の語数は数えない。判断は一文一義と、一段落に一つの話題で行う。

## 対応モデル

Sonnet 以上を勧める。Haiku では、渡していない事実を書くことがある。報告文と設計文書では、この失敗が読み手の判断を直接誤らせる。

観測した内容は [docs/evaluations.md](docs/evaluations.md) にある。

## 参考にした資料

[Federal Plain Language Guidelines](https://www.plainlanguage.gov/guidelines/) と [W3C COGA](https://www.w3.org/TR/coga-usable/) の考え方を参考にした。一覧は [SKILL.md](skills/ja-writing-rules/SKILL.md#参考にした資料) にある。

調査したが採用しなかった資料と、その理由は [docs/design-notes.md](docs/design-notes.md) に書く。

## ライセンス

MIT License。[LICENSE](LICENSE) を参照。
