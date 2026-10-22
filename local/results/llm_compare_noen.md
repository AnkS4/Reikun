# LLM comparison — grammar explanations

## Format adherence (level-aware prompts)

| model | level | n | bullets ok | words ok | bolded | leaks | errors | avg ms |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | N1 | 10 | 10/10 | 9/10 | 10/10 | 0 | 0 | 2975 |
| openai/gpt-oss-120b | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 3242 |

## openai/gpt-oss-120b (groq)

### N5 — もう３ページ残っている。
_132 words, 5 bullets, 1075 ms — judge: fit 4/5, acc 2/5 — The explanation is mostly appropriate for N5 but contains inaccurate points (e.g., the omitted が and the nuance of もう) and misses the simple “plain‑style” nature of the sentence._

- **もう** – “already” or “still”; it shows a state has continued up to now, similar to English “already” in “It’s already finished.”
- **３ページ** – a counter phrase; the number plus the counter word (ページ) tells how many pages, like “3 pages” in English.
- **残っている** – verb 残る “to remain” in the **～ている** form; this pattern expresses a continuing state (something is left), comparable to English “is remaining” or “has remained.”
- **が** (implied) – the subject‑marking particle that would appear before 残っている if the sentence were longer, marking what is left; particles are tiny words that show a noun’s role, like “‑subject” in “She runs.”
- **です** (omitted) – the polite copula often dropped in casual speech; it works like “is” in English, linking the description to the subject.

### N1 — もう３ページ残っている。
_6 words, 3 bullets, 867 ms — judge: fit 5/5, acc 5/5 — The explanation accurately and appropriately uses advanced grammatical terminology suitable for an N1 learner._

- **〜ている**：結果継続の状態を示す。「残っている」は「残る」の結果が今も続くことを強調し、単なる過程ではなく「残りが依然として存在する」ことを示す。  
- **もう**：余剰感・残量の認識を示す限定副詞で、文脈により「すでに」か「あと」かの含意が変わる。  
- **３ページ**：数量詞＋単位が直接名詞化し、残量の具体的測定を示す。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_126 words, 5 bullets, 870 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and mostly appropriate for N5, though some terminology could be simplified further._

- **は** – topic particle, marks what the sentence is about (like “as for …”). It tells the listener, “we’re talking about him.”
- **と** – connective particle, links nouns in a list (similar to “and” in English). Here it joins “サラダ” and “ロールパン.”
- **と一緒に** – “together with” construction; the first と is the same connective particle, and 一緒に means “together.” Together they express doing something alongside something else, like “with the salad and roll bread.”
- **を** – object particle, marks the thing that receives the action (the direct object). It shows that “鶏肉” is what is being eaten.
- **た** – past tense ending for verbs; attaches to the verb stem (食べ) to indicate a completed action, comparable to the English “‑ed” ending.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_16 words, 4 bullets, 1330 ms — judge: fit 5/5, acc 5/5 — The explanation accurately and appropriately uses advanced terminology suitable for an N1 learner._

- **と** (列挙助詞)：同等要素を列挙し、各要素を明示的に対等に扱う。複数名詞を並べる際の「A と B と C」形は、列挙のリズムと均衡を保ちつつ、個別性を強調する効果がある。  
- **一緒に** (副詞的用法)：動作主体の共同性を示す副詞で、主語の意図的合致を暗示し、文脈上は「共に」や「同時に」のニュアンスを付加する。  
- **を** (格助詞)：他動詞の直接目的語を示す基本格で、ここでは食事対象の具体性と限定性を明示し、食べた対象が複数項目の中の「鶏肉」であることを際立たせる。  
- **た** (過去形助動詞)：完了・過去を示す助動詞で、事実的述語化に加え、出来事の時間的閉鎖感と客観的報告性を付与する。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_156 words, 6 bullets, 1029 ms — judge: fit 4/5, acc 4/5 — The explanation is largely appropriate for N5 and mostly accurate, though a few nuances could be clarified._

- **の** → shows possession or description, like “the cap **of** the ink refill bottle”. It links two nouns, similar to the English “’s” or “of”.  
- **で** → instrument particle that marks the tool used for an action, e.g., “with a pipette”. Think of it like “by means of”.  
- **へ** → direction particle indicating where something is moved or sent, here “to the absorber of the marker”. It works like the English “to”.  
- **て** (conjunctive form) → connects verbs to show a sequence of actions, as in “remove the cap, **and** draw ink, **and** drop it”. It’s comparable to saying “and then” in English.  
- **を** → object particle that marks the direct object of a verb, such as “the cap” being removed. It’s like the English “(do something) to”.  
- **ください** → polite request form meaning “please do …”. It attaches to the verb stem and is similar to the English “please”.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_18 words, 4 bullets, 4490 ms — judge: fit 5/5, acc 4/5 — 説明はN1学習者に適した用語と文法解説を提供しているが、最後が途中で切れており、完全な正確さに欠ける。_

- **Vて** (外し、吸い上げ、滴下してください) – 連用形接続で動作を順序的に列挙し、最後に一括した依頼を示す。  
- **Vてください** – 丁寧依頼の助動詞形。複数の動詞を連用形で接続し、全体を一つの依頼として統合できる。  
- **Nへ** (吸収体へ) – 目的地を示すが、到達点ではなく「向かって」や「対象として」捉えるニュアンスが強く、**Nに**より抽象的・指向的。  
- **適量、** – 名詞をコンマで区切り、指示語的に「適切な量を」省略的に付随させ、指

### N5 — 関税申告書が必要になります。
_108 words, 5 bullets, 3961 ms — judge: fit 4/5, acc 2/5 — Explanation misidentifies ます and includes です which isn’t in the sentence, though the basic particle and になる points are roughly correct._

- **が** – particle that marks the subject (what something is about). Similar to “as for” in English: “As for the customs declaration form, …”.
- **必要になる** – verb phrase meaning “to become needed/necessary”. Think of English “to turn into a requirement”.
- **ます** – polite verb ending that makes a statement courteous, like adding “‑please” or “‑would you mind” in English politeness.  
- **です** – copula (linking word) used after nouns or adjectives to state something politely, comparable to the verb “to be” in English.  
- **になる** – auxiliary verb that attaches to nouns or adjectives to express change, like “to become” in English (“cold becomes hot”).

### N1 — 関税申告書が必要になります。
_8 words, 3 bullets, 2867 ms — judge: fit 5/5, acc 4/5 — The explanation is appropriately advanced for N1, but the description of が is somewhat inaccurate._

- **V/Adj + になる**：状態の変化・新たな必要性の発生を示す。ここでは「必要になる」で「必要という状態に転換する」ことを表す。  
- **が**：主語の自発的・客観的な変化を強調し、話者の意図的介入を排除する。  
- **必要**：抽象名詞化された形容動詞で、文末に来ることで形式的・書面的な語感を付与し、官庁文書等の硬い文体に適合させる。

### N5 — この本には美しい挿絵が入っている。
_104 words, 4 bullets, 6553 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and clear, though the particle descriptions could be slightly simplified for an N5 learner._

- **に** → a particle that shows location or direction; here it marks “in the book” (the place where something exists).  
- **は** → a particle that makes the preceding word the topic of the sentence; combined with に it becomes **には**, meaning “as for … in …”.  
- **が** → a particle that marks the subject (the thing that does the action); it highlights “the beautiful illustration(s)”.  
- **入っている** → the **ている** form of the verb 入る (to go in, to be contained). It expresses a continuing state, like “is inside”. Similar to English “has/contains” when you say “The book has beautiful illustrations.”

### N1 — この本には美しい挿絵が入っている。
_4 words, 2 bullets, 1764 ms — judge: fit 5/5, acc 3/5 — 説明は～ているの意味は正しいが、にはの解説がやや不正確でN1学習者にはもう少し詳しい説明が必要です_

- **～ている**：結果的状態を表す。動作が完了し、その結果が現在も継続していることを示す。ここでは「入る」の完了が「本に挿絵が存在する」状態を指す。  
- **には**：限定的対象を示す格助詞の組み合わせ。話題の対象（本）に対して、そこに限定された情報（挿絵の有無）を提示する際に用い、対比的・焦点的ニュアンスを付与する。

### N5 — 彼女は宝石を得意げに見せびらかした。
_109 words, 6 bullets, 4324 ms — judge: fit 3/5, acc 2/5 — The explanation correctly covers most points, but the description of を as “...‑ing a thing” is inaccurate and a bit too technical for N5._

- **は** – topic particle: marks what the sentence is about, like “as for …” in English.  
- **を** – object particle: shows the direct object of a verb, similar to “...‑ing” a thing in English.  
- **に** – adverbial particle: turns an adjective or noun into “in a … way,” comparable to “‑ly” in English.  
- **～げ** – suffix that adds the meaning “seems/looks …,” turning an adjective (得意) into “confident‑looking.”  
- **Vた** – past plain verb ending: indicates a completed action, like the English simple past “‑ed.”  
- **見せびらかす** – compound verb pattern: two verbs combined (見せる “to show” + びらかす “to flaunt”) to express “show off.”

### N1 — 彼女は宝石を得意げに見せびらかした。
_6 words, 2 bullets, 4199 ms — judge: fit 5/5, acc 3/5 — 説明はN1向きに専門用語を使っているが、～げの品詞や見せびらかすの構造についての記述が不正確です。_

- **～げ**: 接尾形容動詞的に「…の様子・印象」を示す。文脈次第で皮肉・軽蔑を帯びることが多く、**得意げに**は「自信満々な様子を外向きに示す」意味合いになる。  

- **～びらかす**: 動詞「見せる」に強調の助動詞「びらかす」が結合した形で、「人目を引くほどに誇示する」ことを表す。文語的・皮肉的表現として頻出。

### N5 — 彼の福祉の概念はかなり観念的だ。
_113 words, 4 bullets, 2953 ms — judge: fit 4/5, acc 3/5 — The explanation is mostly appropriate for N5 but misinterprets the の phrase and could be clearer about the structure._

- **の** – a particle that shows possession or a relationship, similar to “’s” in English. In the sentence it links 「彼」 and 「福祉」 to indicate “his welfare.”
- **は** – the topic particle that marks what the sentence is about, like “as for …” in English. It sets 「概念」 as the thing being described.
- **かなり** – an adverb that means “quite” or “fairly,” used to modify the adjective that follows, just as “very” can strengthen an adjective in English.
- **だ** – the plain‑form copula, the informal version of 「です」, which works like the verb “to be” linking the subject and its description. It is the ending that states the predicate.

### N1 — 彼の福祉の概念はかなり観念的だ。
_16 words, 4 bullets, 2799 ms_

- **の** : 連体修飾の所有関係を示す。文脈上は抽象的概念の範囲限定で、後続名詞を限定的に特定する機能を持つ。  
- **は** : 主題提示＋対照的焦点付与。ここでは「福祉の概念」を議論対象とし、暗に他の概念との差異を示唆。  
- **かなり** : 程度副詞として、評価的強度を緩和せずに直接的に「相当」さを付与。  
- **だ** : 判定語としての断定形。形容動詞「観念的」に直結し、文体的に硬式・学術的トーンを保持する。

### N5 — この岩は何に似ていますか。
_146 words, 5 bullets, 2878 ms_

- **この** – a demonstrative adjective that means “this” and comes before a noun to point it out, similar to “this” in English.  
- **は** – a topic particle — a small word that marks what the sentence is about; it sets “この岩” as the topic, like saying “As for this rock …”.  
- **何に** – the question word 何 (what) followed by the particle に, which marks the target of a verb; together they ask “what … to/for”. This is like “what … to” in English (“what is it similar to?”).  
- **似ています** – the verb 似る (to resemble) in the **ている** form, which shows a continuing state; it means “is similar” or “looks like”, comparable to the English present progressive “is looking like”.  
- **か** – a question particle that turns a statement into a question, similar to adding a question mark in English.

### N1 — この岩は何に似ていますか。
_92 words, 4 bullets, 4837 ms — judge: fit 4/5, acc 2/5 — The explanation misidentifies the function of か (it forms a wh‑question, not a yes‑no question) and over‑complicates other particles for an N1 learner._

- **は**: contrastive/topical particle marking 「この岩」 as the subject of evaluation, implying a comparison frame rather than mere identification.  
- **に**: dative marker indicating the standard of similarity; in 「何に」 it functions as an interrogative complement to the verb 「似る」, foregrounding the referent being compared.  
- **似ている**: stative progressive of 「似る」, used here to denote an inherent resemblance rather than a transient action; the polite 「です」 auxiliary adds formality without altering aspectual nuance.  
- **か**: interrogative particle that converts the predicative clause into a polite yes‑no question, preserving the speaker’s epistemic distance.

### N5 — この報告書は要領をえていない。
_132 words, 6 bullets, 3038 ms — judge: fit 4/5, acc 5/5 — The explanation correctly covers the particles and grammar, though some terms may be a bit advanced for strict N5 level._

- **は** – particle that marks the topic (what the sentence is about); similar to “as for” in English.  
- **を** – particle that marks the direct object (the thing acted upon); works like “(object) + verb” in English.  
- **～ている** – verb suffix showing a continuing state or result; comparable to “is …‑ing” or “has …ed” (e.g., “is being” or “has become”).  
- **～ない** – negative ending that turns a verb into “does not …”; works like adding “not” to an English verb.  
- **～ていない** – combination of the progressive/result suffix with the negative; means “is not …‑ing” or “has not …ed” (e.g., “is not having”).  
- **得る** – verb meaning “to obtain” or “to have”; when used with an object and ている, it expresses possessing a certain ability or knack.

### N1 — この報告書は要領をえていない。
_4 words, 2 bullets, 2704 ms — judge: fit 5/5, acc 5/5 — Explanation is appropriately detailed for N1 and accurately describes the usage of ～ている and 要領を得る._

- **～ている**：結果状態を表す。動作完了後にその状態が継続していることを示すため、単なる進行ではなく「要領を得た（把握した）まま」＝把握していないという意味になる。  
- **要領を得る**：慣用句的に「要点を把握する」「要領をつかむ」ことを指す。否定形で「要領を得ていない」は、要旨や要点が全く掴めていない、理解不足を強調するニュアンスになる。

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_120 words, 5 bullets, 5739 ms — judge: fit 2/5, acc 4/5 — The explanation covers the grammar correctly but includes forms (のだが, であろう) that are beyond the N5 level._

- **～ている** – shows a continuing state or habit; similar to the English present progressive “is living.”  
- **のだが** – combines the explanatory particle **の** (adds reason or emphasis) with **が** (conjunction “but”). It softens a statement and then contrasts it, like “...though...” in English.  
- **であろう** – the polite conjectural form of **だ** (the copula, a word that links a subject to a description). It expresses a guess or prediction, roughly “will probably be.”  
- **～を** – a particle that marks the direct object of a verb, the thing the action is done to, similar to the English “‑object‑” after a verb.  
- **～に** – a particle indicating location where something exists or happens, comparable to “in/at” in English.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_6 words, 3 bullets, 3891 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N1-level depth and accurately describes the grammar used in the sentence._

- **～ている**：継続状態を示すだけでなく、環境変化に対する現在の実態を客観的に提示し、科学的記述に適する。  
- **のだが**：説明的体言化に接続し、前文の事実を提示した上で対比・逆説を導入する論理的接続詞的機能。  
- **～であろう**：推量の敬体で、確度の高い予測を示すと同時に、学術的・客観的文体を保持する。
