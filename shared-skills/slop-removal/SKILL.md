---
name: slop-removal
description: AI-slop マーカー（機械生成と検出される表現パターン・空虚な装飾語・陳腐な構文）を学術・技術文書（英語と日英の翻訳）から検出・除去する。下書きの後に残った型と事実の保持を監査する2段手順と、学術慣行を保ちつつ英語の型を除く規則を適用する。日本語の型の規則は ja-writing-rules が決め、ここから参照する。
---

# slop-removal — AI-slop マーカーの検出と除去

機械生成特有の統計的マーカー、陳腐な誇張、空虚な文構造を排除し、**主張と観測データだけが残る素直で明瞭な文**にする。

## 2段推敲手順: 下書き → 監査と仕上げ

1. 第1段（下書き作成）: 原文の主張・条件・数値を保ち、素直な表現で起草する。新しい事実を作らない規則は `ja-writing-rules` の「確かめていないことを書かない」に従う。
2. 第2段（監査と仕上げ）: 以下の2問で監査し、残った型を解消して最終稿とする。
   - 自問 1: 「何がまだ明らかに機械生成臭いか？」（前置き、誇張、エムダッシュ、安易な対比、太字見出しの残存点検）
   - 自問 2: 「元にない事実を捏造していないか、元の主張・条件・数値を落としていないか？」（事実を捏造しない。規則は `ja-writing-rules` が決める）

## 学術慣行の保持（消してはならない要素）

- 方法節の受動態: 実験手順や手法（"Images were captured...", "Parameters were optimized using Adam"）の受動態は標準的慣行であり、不自然に能動態に崩したり人称代名詞を無理に挿入しない。
- 正当な留保・限定: 科学的境界を示す留保（"may indicate", "under assumption C", "within experimental uncertainty"）は過剰な断定に改変せず保持する。
- 定着専門術語: 数理的・技術的に確立した定義や定型表現は、平易化を名目に崩さず原文の術語を守る。

---

## Layer 1: 禁止語彙（英語・英訳）

### 1a. 純粋 slop（削除するか平易な語に戻す。新しい修飾を足さない）
- 動詞: delve, leverage, harness, utilize, streamline, unlock, empower, capitalize on, navigate, foster, spearhead, embark
- 強調修飾: groundbreaking, game-changing, cutting-edge, transformative, unprecedented, paramount, vital, seamlessly, sophisticated
- 抽象 filler: tapestry, labyrinth, crucible, landscape, realm, journey, multifaceted
- メタ言及・前置き: "Here's the thing:", "Let that sink in.", "At its core", "It is worth noting that", "In today's rapidly evolving landscape"
- be 動詞の回避: "serves as" / "stands as" / "acts as" → 素直に "is" に戻す
- 意義を誇張する分詞構文: ", highlighting/underscoring its importance", ", setting the stage for" → 削除し事実のみ記す
- Puffery 述語: "a testament to", "plays a crucial/pivotal role", "marking a pivotal moment" → 具体機構を名指すか削除

### 1b. 文脈依存語（数値か機構の裏付けがあるときだけ使う）
- significant: 具体数値（p値・向上幅）がある場合のみ可（空虚な "a significant improvement" は禁止）。
- robust: 耐性の検証条件（ノイズ強度・外れ値比率等）がある場合のみ可。
- novel / state-of-the-art: 原則使わず、既存手法との具体的な差分・比較結果を記述する。

---

## Layer 2: 構造的罠と修辞パターン（英語・翻訳）

- False Ranges（空虚な範囲）: "from healthcare to finance" 等、連続尺度でない無関係な概念を並べる幅表現を禁止。
- Em Dash（エムダッシュ乱用）: 劇的演出や挿入節のための `—` を排し、コンマ・ピリオド・括弧・平易な複文に直す。
- Bold-Lead Bullets（太字箇条書き連打）: 全項目が `**Term**: Explanation` で始まる定型を避け、散文で自然に展開する。強調の絞り方一般は `ja-writing-rules` の `reference/reports.md`「強調を絞る」に従う。
- Dramatic Fragmentation（劇的断片化）: "Latency. Gone. Just like that." のような短文連打を排し統合する。
- Forced Contrast / Q&A: "not only X, but also Y" / "What does this mean? It means..." の自問自答をやめ、直接結論を述べる。日本語の「A は B ではない。C だ」と先回りの打ち消しは、`ja-writing-rules` の「中身のない文と語を削る」に従う。
- Stacked Anaphora / Tricolon: 無理な3点揃え（Rule of Three）や同一語での文頭連続（"No X. No Y."）を排す。
- Argument Residue（対話痕跡）: "Certainly!", "As mentioned earlier", "In conclusion" などのAI対話・定型結びを削除。

---

## Layer 3: 具体性とリズム (Authenticity)

- Content Tell 排除: 進行実況文（"To understand this, we first consider..."）を削除し、本論から開始する。日本語の同種の文は `ja-writing-rules` の「中身のない文と語を削る」に従う。
- 文長は主張で決める: 文の長さは、一文に入る主張の数で決まる。リズムを崩すためだけに短文を差し込んだり、語数を目標にしたりしない。
- 具体性の徹底: "various methods" ではなく具体手法名（"SIFT, SuperPoint"）を明記する（捏造は厳禁）。

---

## Pass B: 日英 翻訳 slop マップ

| 日本語草稿 | ❌ 避ける英訳 (slop) | ✅ 推奨する英訳 (slopless) |
|---|---|---|
| 〜を活用する | leverage / utilize | use / apply / exploit |
| さまざまな手法 | various methods | 手法名を直接列挙 |
| 近年注目を集めている | has garnered significant attention | 具体的な先行研究を引用 |
| 〜することが可能である | it is possible to ... | 能動態で直接述べる ("X detects Y") |
| 重要な役割を果たす | plays a crucial role | 機構・動作を具体的に名指しする |
| 〜と考えられる | it can be considered that | 根拠を主語にする（"X suggests Y"）。留保の強さは原文から変えない |
| 本研究では | In this paper, we ... | 削除、または "We" で直接開始 |

---

## Pass A & Layer 4: 日本語の読みの負荷と slop の除去

- メタ言及と飾り: 「〜という点が重要である」「注目すべきは」「言うまでもなく」の類は、`ja-writing-rules` の「中身のない文と語を削る」に従って削る。言い換えて補わない。
- 比喩と直訳: 擬人化、英語の慣用句の直訳、話し言葉の動詞は、`ja-writing-rules` の「起きることを語で書く」に従う。
- 主述のねじれ: 英語直訳由来の「その条件は〜を報告する」などの不自然な主述を正す。
- 40字超の連体修飾主語: 「〜する〜の〜は…」と主語が長すぎる場合、修飾を述語的に前置する。
- 名詞の過剰連鎖（「の」の多用）: `ja-writing-rules` の「名詞の連鎖を動詞に開く」に従う。

---

## LaTeX / 論文執筆時の書式 Tells

- Abstract 自己完結性: Abstract 内に `\ref{sec:...}` などの節番号参照を置かない。
- 太字の乱用防止: 本文中で術語を一律 `\textbf{}` にしない。絞り方は `ja-writing-rules` の `reference/reports.md` に従う。
- Contraction (短縮形) 排除: Formal prose では "it's" ではなく "it is" を使用する。
- 引用と数値の整合: 表面的な言い換えでなく、引用・数値が一次記録と一致していることを確認する。

## 参照資料
英語の型の詳しい一覧と Before/After 例は、このリポジトリに含めない。外部の次の資料にある (どちらも MIT License)。このスキルの規則は、これらを参考に書き直したものである。

- [skill-deslop](https://github.com/stephenturner/skill-deslop): `deslop` スキル。表現・構文・修辞の一覧と推敲例を `references/` に持つ。プラグインではない。
- [humanizer](https://github.com/jooray/humanizer): `humanizer` スキル (Claude Code プラグイン)。Wikipedia「Signs of AI writing」に基づく型の一覧を SKILL.md に持つ。

これらのスキルが入っているときは参照してよい。入っていないときは、このスキルの規則だけで進める。
