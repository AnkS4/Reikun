# LLM comparison — grammar explanations

## Format adherence (level-aware prompts)

| model | level | n | bullets ok | words ok | bolded | leaks | errors | avg ms |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | N1 | 10 | 9/9 | 9/9 | 9/9 | 0 | 1 | 1704 |
| openai/gpt-oss-120b | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1684 |
| openai/gpt-oss-20b | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 563 |
| openai/gpt-oss-20b | N5 | 10 | 9/10 | 10/10 | 10/10 | 0 | 0 | 695 |
| qwen/qwen3.8-27b | N1 | 10 | 8/9 | 9/9 | 9/9 | 0 | 1 | 10663 |
| qwen/qwen3.8-27b | N5 | 10 | 4/8 | 8/8 | 8/8 | 0 | 2 | 35864 |
| command-a-plus-05-2026 | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1908 |
| command-a-plus-05-2026 | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 2204 |

## openai/gpt-oss-120b (groq)

### N5 — もう３ページ残っている。
_148 words, 5 bullets, 1119 ms — judge: fit 4/5, acc 3/5 — The explanation is mostly appropriate for N5 but contains some inaccurate points (e.g., mentions a が particle that isn’t present) and oversimplifies the nuance of もう._

- **もう** – “already” or “still” when talking about time left. It shows that something continues up to now, similar to English “already have … left.”  
- **〜ている** – verb‑stem + て + いる expresses a continuing state or ongoing action. Here it means “is remaining.” Think of English “is ___ing” for a state, e.g., “is staying.”  
- **残る** – the plain verb “to remain” or “to be left over.” When combined with ている it becomes “残っている” to describe the current amount that is still there.  
- **数 + カウンター** – using a number with a counter (ページ for pages) to count objects. It works like “three pages” in English, where the counter specifies the type of thing counted.  
- **が** (particle) – marks the subject of a sentence, showing what is doing the action. In this case it would mark “three pages” as the thing that remains.

### N1 — もう３ページ残っている。
_9 words, 3 bullets, 717 ms — judge: fit 5/5, acc 5/5 — 説明はN1レベルに適切で、文法的にも正確です_

- **もう**: 残余的時間・数量を示す「既に」ではなく、残りがまだあることを示唆する「まだ」のニュアンスを帯び、口語的に残存感覚を強調。  
- **残っている**: 動詞「残る」の**〜ている**形は結果状態を表す。ここでは「残る」自体が不完了動作であり、結果としての残量が現在も継続していることを示す。  
- **３ページ**: 数量詞＋助数詞の直接連体修飾で、抽象的な「ページ数」の具体的残量を指示し、文全体の焦点を数量的制限に限定。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_105 words, 5 bullets, 1128 ms — judge: fit 5/5, acc 5/5 — The explanation matches N5 expectations and correctly describes each grammatical element of the sentence._

- **は** – topic particle, a small word that marks what the sentence is about; similar to saying “as for …” in English.  
- **と** – listing particle, joins nouns like “and”; works like the English “and” when you list items.  
- **と一緒に** – phrase meaning “together with”; it adds the idea of doing something side‑by‑side, like “with …” in English.  
- **を** – object particle, a small word that marks the direct object (the thing being acted on); comparable to the English “(verb) …”.  
- **た** – past‑tense ending for verbs; turns a present action into “did”, just as adding “‑ed” does in English.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
**ERROR** `RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m25vxfjee54thh21g0armvjt` service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 7453, Requested 668. Please try again in 907.5ms. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}`

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_159 words, 6 bullets, 4762 ms_

- **の** – a particle that shows possession or relationship, like “of” in English. Example: インキ補充瓶のキャップ (the cap **of** the ink refill bottle).  
- **を** – a particle marking the direct object, the thing a verb acts on. Example: キャップを外し (remove **the cap**).  
- **て** – the te‑form connects multiple actions in a sequence, similar to “and then” in English. Here it links 外し, 吸い上げ, and 滴下してください, showing the steps are done one after another.  
- **へ** – a particle indicating direction or destination, like “to” in English. Example: 吸収体へ適量 (the appropriate amount **to** the marker’s core).  
- **ください** – a polite request form meaning “please do …”. It attaches to the verb stem (滴下し) to ask the listener to perform the action.  
- **て + ください** – combines the connective te‑form with ください to request a series of actions. It’s like saying “please … and then …” in English, e.g., “remove the cap, then fill the dropper, please.”

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_9 words, 3 bullets, 2876 ms — judge: fit 5/5, acc 5/5 — The explanation correctly and appropriately uses N1‑level terminology to describe the て‑form sequencing, the polite ください command, and the function of the particle へ._

- **～て**: 連用形で並列動作を示す。文中の「外し、吸い上げ、滴下してください」は順序的連続を暗示し、各動作の独立性を保ちつつ全体指示に統合する効果がある。  
- **～ください**: 丁寧な命令形。動詞連用形に接続し、聞き手に実施を促すが、文全体の指示性を緩和し、指示対象が複数動作であることを示すために最後の動作にのみ付す。  
- **へ**: 目的・到達点を示す格助詞。ここでは「吸収体へ適量滴下してください」で、滴下の方向を「吸収体」に限定し、対象への動作焦点を明確にする。

### N5 — 関税申告書が必要になります。
_117 words, 5 bullets, 3972 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and clear, though a few terms could be simplified further for N5._

- **が** – particle that marks the subject (the thing doing or being described). It’s like “as for” in English “As for the customs form…”.  
- **必要** – a na‑adjective (adjective that needs the copula だ/です) meaning “necessary”. Think of it like the English word “necessary”.  
- **になる** – verb phrase meaning “to become”. It turns a noun or adjective into a state, similar to “become” in English (“the form becomes necessary”).  
- **必要になります** – combines the na‑adjective 必要 with になる, giving “becomes necessary”. This pattern is used when something changes from not needed to needed.  
- **が必要になります** – the whole chunk shows the subject 関税申告書 is what becomes needed, equivalent to “A customs declaration is required.”

### N1 — 関税申告書が必要になります。
_6 words, 3 bullets, 1208 ms — judge: fit 5/5, acc 5/5 — The explanation accurately captures the N1‑level nuance of ～になる, especially its use with 必要になる in formal contexts._

- **～になる**：形容動詞・形容詞＋になるで、状態の客観的変化を示す。文脈上、必然性や外的要因による転換を暗示し、公式文書で頻出。  
- **です/ます形のになる**：敬体で述べる際、述語を名詞化した上で敬語化し、文全体の硬度を高める。  
- **必要になる**：形容動詞「必要」＋になるの固定表現。要求が外部条件により発生したことを示し、主観的意志を排除する。

### N5 — この本には美しい挿絵が入っている。
_151 words, 5 bullets, 1088 ms — judge: fit 5/5, acc 5/5 — The explanation is clear, accurate, and well‑suited to an N5 learner._

- **には** – combination of the particle **に** (marks location or target) and the topic marker **は**; it shows “as for … in/at …”. Think of it like “as for this book, regarding its inside”.  
- **が** – particle – a small word that marks the subject (the thing that does or has something). It highlights “illustrations” as the thing that exists in the book. Similar to English “there is/are …”.  
- **入っている** – verb in the **ている** form; **ている** adds a continuous or resultant state to a verb, like “is …ing” or “has …”. Here it means “are included” → “is included/has”. Comparable to English “is/has … inside”.  
- **美しい** – adjective – a word that directly describes a noun; placed before the noun it modifies. In English this is like “beautiful”.  
- **この本** – demonstrative + noun; “this book”. Demonstratives point out specific things, similar to “this/that” in English.

### N1 — この本には美しい挿絵が入っている。
_6 words, 3 bullets, 843 ms — judge: fit 5/5, acc 5/5 — The explanation is appropriately advanced for N1 and accurately describes each grammatical element._

- **には**：格助詞「に」＋係助詞「は」。対象を限定し、そこに存在・作用があることを強調する文脈で、限定的トピックを示す。  
- **が**：主格助詞。主語を明示し、限定的に情報を提示する際のニュアンスを保持。  
- **入っている**：動詞「入る」のテ形＋いる。結果状態を表す現在完了的用法で、物理的に「入って」いる状態が継続していることを示す。

### N5 — 彼女は宝石を得意げに見せびらかした。
_111 words, 5 bullets, 959 ms — judge: fit 3/5, acc 5/5 — The explanation is accurate, but the vocabulary (得意げ, 見せびらかす) is slightly beyond typical N5 level._

- **は** – topic particle, marks what the sentence is about (like “as for …” in English).  
- **を** – object particle, shows the direct object that the action acts on (similar to “‑‑ the …”).  
- **に** – adverbial particle, turns a noun into an adverb describing how something is done (like “‑‑ly” in English).  
- **～げ** – suffix that adds the nuance “seems/looks …” to a noun or adjective, e.g., *得意げ* “looks confident”. It’s comparable to adding “‑ish” or “‑like” in English (“proud‑looking”).  
- **した** – past form of *する* (to do), used here to make the verb *見せびらかす* “to flaunt” past tense, similar to adding “‑ed” in English.

### N1 — 彼女は宝石を得意げに見せびらかした。
_6 words, 2 bullets, 659 ms — judge: fit 5/5, acc 5/5 — The explanation correctly details the 〜げ and 〜に constructions with appropriate nuance for an N1 learner._

- **〜げ**: 動詞・形容詞連用形＋げで、話者の主観的感情・様子を外見的に示す。文脈により揶揄的・軽蔑的ニュアンスが付くことがある。  
- **〜に**（形容詞連用形＋に）: 形容詞を副詞化し、動作の様態を修飾。**得意げに**は「得意な様子で」だけでなく、聞き手に対する皮肉的評価を暗示する場合も。

### N5 — 彼の福祉の概念はかなり観念的だ。
_103 words, 4 bullets, 668 ms — judge: fit 3/5, acc 4/5 — Explanation is mostly correct but uses somewhat advanced vocabulary for N5, making the pitch a bit high._

- **の** – particle — a small word that shows one noun belongs to or describes another; similar to the English “'s” or “of” (彼の福祉 = his welfare).  
- **は** – particle — marks the topic, what the sentence is about; works like “as for …” in English (概念は = as for the notion).  
- **だ** – copula – the plain form of “です,” used to state something is true; equivalent to the English “is” in informal speech (観念的だ = is abstract).  
- **かなり** – adverb – modifies adjectives or verbs to mean “quite” or “fairly,” like the English “pretty” before an adjective.

### N1 — 彼の福祉の概念はかなり観念的だ。
_12 words, 3 bullets, 1229 ms — judge: fit 3/5, acc 2/5 — 説明はやや高度な語彙を使っているが、用語の誤用や不正確な説明が目立ち、文法解説としては不十分です。_

- **N1のN2** : 所有・属性を示す連体修飾で、抽象概念や学術的語彙と結合するときは、文体的にやや硬式になる。  
- **かなり＋形容詞/形容動詞** : 「相当」「かなり」の程度副詞は、客観的評価を保ちつつ、語感的に「やや強め」や「予想外の高さ」を暗示し、評価者の立場を遠ざける効果がある。  
- **観念的だ** : 「的」接尾辞で名詞を形容動詞化し、抽象的・概念的属性を示す。学術的・論説体で頻出し、感情的評価を排除した客観的述語になる。

### N5 — この岩は何に似ていますか。
_97 words, 5 bullets, 739 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N5 vocabulary and clearly describes each particle and the verb form._

- **は** – topic particle; marks what the sentence is about, like “as for …” in English.  
- **に** – particle indicating the target of similarity; similar to “to/like” in “looks like”.  
- **何** – interrogative word meaning “what”; works like the English “what” to ask for information.  
- **似ています** – the **〜ている** form of the verb 似る (to resemble); shows a continuing state, comparable to “is looking like” rather than a one‑time action.  
- **か** – question particle; placed at the end to turn the statement into a question, like adding a question mark in English.

### N1 — この岩は何に似ていますか。
_9 words, 3 bullets, 539 ms — judge: fit 5/5, acc 4/5 — Explanation is appropriate for N1, though the description of 似ている could be more precise._

- **に**: 格助詞、対象を示す。疑問代名詞「何」に接続し、比較対象を限定する機能を持つ。  
- **似ている**: 動詞「似る」の現在進行形・状態継続形。連体修飾としても用いられ、対象が持つ外観・性質が他と類似していることを客観的に示す。  
- **か**: 終助詞、疑問文を形成。文末に置くことで、情報の照会・確認を求める丁寧な疑問を構成する。

### N5 — この報告書は要領をえていない。
_122 words, 5 bullets, 1031 ms — judge: fit 5/5, acc 4/5 — The explanation matches N5 level well, but it overlooks the typo in the sentence (要領をえていない should be 要領を得ていない) and thus isn’t fully accurate._

- **は** – a particle — a tiny word that marks the topic of the sentence, like “as for …” in English.  
- **を** – a particle — marks the direct object, the thing that the verb acts on, similar to “‑‑ object” after a verb.  
- **～を得る** – a verb phrase meaning “to obtain/understand”. It works like “to get” in English (“get the point”).  
- **～ている** – shows a continuing state or result of an action; think of it like the English “‑ing” or “has‑been ‑‑‑ing”. Here it expresses the ongoing state of not having obtained the point.  
- **ない** – the plain negative ending for verbs, turning them into “not …”. It’s comparable to adding “‑n't” to an English verb.

### N1 — この報告書は要領をえていない。
_6 words, 3 bullets, 907 ms — judge: fit 5/5, acc 5/5 — Explanation correctly matches N1 level depth, terminology and accurately describes the grammar and nuance._

- **要領を得る**：慣用句で「要点・核心をつかむ」ことを指す。文脈上は抽象的対象（報告書）の「要旨を把握できていない」状態を示す。
- **Vている**（要領を得ている）：結果状態を表し、継続的な欠如ではなく「現在までに要領が形成されていない」ことを強調。  
- **ない**：否定は単純に状態の不在を示すが、ここでは批判的・やや硬い評価トーンとなり、上位文脈での改善要求を暗示する。

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_171 words, 6 bullets, 1378 ms — judge: fit 3/5, acc 4/5 — The explanation is mostly correct but includes some grammar (であろう) that is beyond the N5 level._

- **は** – topic particle, marks what the sentence is about (like “as for …” in English). It tells the listener the focus is the polar bear.  
- **に** – location particle, shows where an action happens (similar to “at” or “in” in English). It indicates the ice‑cap where the bear lives.  
- **ている** – progressive/result state form, attaches to a verb to express a continuing action or a current state (like “is living”). It conveys that the bear’s living situation is ongoing.  
- **のだ** – explanatory / nominalizer, adds a tone of explanation or emphasis (comparable to saying “you see,” before giving a reason). It stresses the fact that the bear lives there.  
- **が** – conjunction particle meaning “but,” linking two contrasting clauses (just as “but” does in English). It connects the bear’s current habitat with the upcoming problem.  
- **であろう** – tentative polite form of だ, used to guess or predict politely (like “will probably” in English). It expresses a future expectation that the bear will become extinct.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_6 words, 2 bullets, 863 ms — judge: fit 5/5, acc 5/5 — N1レベルに適した専門的用語と正確な文法解説で、説明は的確です_

- **のだが**：説明的体 + 逆接が。文脈的に「前提を示しつつ、次に続く事実を対照的に提示」する効果。口語では「んだけど」に還元されるが、書き言葉で客観的・学術的トーンを保持。  
- **であろう**：推量の助動詞「だろう」の文語形。仮定的・遠観的ニュアンスを付加し、予測の根拠が不確実であることを示す。論文体や評論文で頻用。


## openai/gpt-oss-20b (groq)

### N5 — もう３ページ残っている。
_124 words, 4 bullets, 834 ms — judge: fit 4/5, acc 5/5 — Explanation is accurate and clear, though slightly more detail than typical N5 materials._

- **もう** – an adverb meaning “already” or “still”. Here it says the pages are still left. In English we might say “still” or “yet”, but **もう** can also mean “already” in other contexts.  
- **３ページ** – a number + counter. The counter **ページ** is used for pages. In English we say “3 pages”; Japanese just puts the counter after the number.  
- **残る** (to remain) – an intransitive verb that shows something still exists. In the sentence, the verb is in its ている form.  
- **〜ている** – a verb ending that expresses a current state or ongoing action. Here it shows that the remaining pages *are* still there. It’s similar to the English “is” + verb‑ing (e.g., “There are still 3 pages left”).

### N1 — もう３ページ残っている。
_16 words, 4 bullets, 775 ms — judge: fit 4/5, acc 2/5 — 説明はN1学習者向けに詳細すぎて一部誤解を招き、‘残っている’の用法を正確に捉えていない。_

- **〜ている** (継続＋状態): 動作が完了している状態を示す。文脈で「残る」から「残っている」は、まだ未完了の状態を強調し、残りが確定していることを暗示する。  
- **〜ている** (経過＋結果): 時制が現在で、行為の結果が継続していることを表す。ここでは「ページが残る」という結果が今も存在するため、進行形的解釈も可能だが、実際は状態形。  
- **〜ている** (状態を客観化): 場所や数量の状態を客観的に記述し、読者に具体的なイメージを与える。N1レベルでは、動詞の状態化に対して「〜ている」が必須である。  
- **〜ている** (文脈的強調): 「もう３ページ残っている」では、時間の経過を伴わずに「残っている」だけで未来感を含むため、文章全体の時間軸に対する微妙なニュアンスを作り出す。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_90 words, 5 bullets, 340 ms — judge: fit 5/5, acc 5/5 — The explanation accurately covers the particles and verb form in language appropriate for an N5 learner._

- **は** – a particle that says “as for” the subject. It shows what the sentence is about.  
- **と** – a particle meaning “and” or “with” when it joins two nouns.  
- **と一緒に** – a phrase meaning “together with” or “along with.” It shows that two things happen at the same time.  
- **を** – a particle that marks the direct object, the thing being acted on.  
- **た** – the past form of a verb; it turns the action into “did” something.  Similar to adding *-ed* in English.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_14 words, 4 bullets, 537 ms — judge: fit 5/5, acc 5/5 — 説明はN1学習者向けに適切な用語と深さで正確に文法を解説している。_

- **〜と** (enumeration) → 連続的に列挙し、全てを同等に扱う。  
- **〜と一緒に** → 同一時点・同一場所で共同行動することを強調。  
- **一緒に** の後に複数語を並べると、各語が「一緒に」同時に行われる対象を示す。  
- ここでは「サラダ」と「ロールパン」が「鶏肉と同時に食べられる」ことを明示し、単なる列挙ではなく共食のニュアンスを付与する。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_141 words, 6 bullets, 527 ms_

- **を** – a particle that marks the direct object of a verb. It shows what the action is done to, like the English “to” in “drink **water**.”
- **て** – a particle that links verbs, showing that one action follows another. It works like the English “and” or “then.”  
- **で** – a particle indicating the method or means by which something is done, similar to the English “with” or “by.”  
- **へ** – a particle that shows direction or destination, comparable to the English “to” when talking about going somewhere.  
- **の** – a particle that links nouns, turning the first noun into an adjective for the second (possessive or descriptive). It’s like the English “of” or the possessive ’s.  
- **た** – the past tense marker that shows an action has finished, like the English “-ed” or “did.”

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_4 words, 2 bullets, 450 ms — judge: fit 5/5, acc 5/5 — Explanation correctly matches N1 level and accurately describes the て‑form sequence and the usage of へ._

- **〜て、〜て、〜て**：連続動作を列挙し、命令形の「ください」で統一する。  
- **〜へ**：目的地・方向を示す格助詞。動作対象を「マーカーの吸収体へ」指示し、流れの終着点を明示。

### N5 — 関税申告書が必要になります。
_108 words, 3 bullets, 644 ms — judge: fit 4/5, acc 5/5 — Clear N5‑appropriate explanation, though the note about が not being spoken aloud is slightly misleading._

- **が** – a particle that marks the subject (the thing that is the focus). It’s similar to the English “is the one that …” but you only see it in Japanese, not spoken aloud.  
- **になる** – a verb form that means “to become” or “to turn into.” In this sentence it turns the noun *必要* (need) into a state of being needed. It’s like saying “it will become necessary.”  
- **必要** – not a grammar pattern, but a noun that means “necessary” or “needed.” In this sentence it functions as the subject of the verb *になる*, so the whole sentence says “A customs declaration becomes necessary.”

### N1 — 関税申告書が必要になります。
_12 words, 4 bullets, 332 ms — judge: fit 5/5, acc 4/5 — 説明はN1向けの用語を使って概ね正しく述べているが、ニュアンスや文末表現の解釈に若干の誤りがある。_

- **必要になる**: 形容動詞＋なるは、状態変化を示し、将来の必要性を強調する。  
- **〜が必要です** → 〜が必要になるで「必要」よりも「不可欠」であるニュアンスを加える。  
- **〜になります**: 連用形＋なるで丁寧体を保ちつつ、状態変化を示す。  
- 文末の「になります」は敬語を維持しつつ、結果として「必要」となることを明示する。

### N5 — この本には美しい挿絵が入っている。
_162 words, 6 bullets, 740 ms — judge: fit 3/5, acc 2/5 — The explanation contains several inaccuracies (e.g., misuse of 入れる vs 入る and misidentifying が as marking the object) and is slightly too advanced for a strict N5 level._

- **には** – A particle combo that marks a *location* or *topic* for something happening. Think of it like “in/on” plus “as for” in English.  
- **が** – The subject marker; it points out the thing that **does** something. It is like “but” in English, but in grammar it just says “this is what the action is about.”  
- **〜ている** – A verb ending that shows a *continuing state* or *ongoing action*. It’s like the English present continuous “-ing” or simply “is doing.”  
- **〜入る (いれる)** – A verb meaning “to put in” or “to insert.” In this sentence it is the root of the **入っている** phrase, giving the idea of “has been put in.”  
- **美しい** – An adjective meaning “beautiful.” In Japanese adjectives can directly modify nouns, so it simply describes the *挿絵* (illustration).  
- **挿絵** – A noun meaning “illustration” or “picture.” It is the object that **が** marks, showing it is the item that is *in* the book.

### N1 — この本には美しい挿絵が入っている。
_13 words, 4 bullets, 480 ms — judge: fit 3/5, acc 2/5 — The explanation misuses grammatical terminology and gives an inaccurate description of 入っている, so it is not a correct N1‑level analysis._

- **～に** + **入っている**: 形容詞修飾語が示す状態を、存在・位置の連用形で表す。  
- **挿絵が入っている**: 連体修飾語の「美しい」が入っている状態を完了形で提示。  
- **入っている** の連体形は、描写対象の「入る」動作が完結した瞬間を示す。  
- 文章全体で「～に」＋「入っている」は、物事の配置や構成を「静的に存在」させる表現で、視覚的美しさを強調。

### N5 — 彼女は宝石を得意げに見せびらかした。
_166 words, 5 bullets, 751 ms — judge: fit 2/5, acc 2/5 — The explanation misidentifies particles (e.g., using で instead of に) and includes concepts beyond N5, making it only partially correct and not well‑matched to the learner level._

- **は** – the topic marker that tells what the sentence is about.  
  *Example: 彼女は* “As for she (she) …”  
  It is similar to “as for” in English, putting the subject in focus.  

- **を** – the object marker that shows what is acted upon.  
  *Example: 宝石を* “jewels (the object) …”  
  Think of it as the “to” in “give the book to him” – it points to the item being affected.  

- **で** – a particle used to describe the manner or state in which an action is done.  
  *Example: 得意げに**で*** “in a proud way”  
  It is like adding “in a proud manner” after a verb in English.  

- **た** – the plain past form ending for verbs.  
  *Example: 見せびらかした* “displayed (past)”  
  It works like the English “-ed” for simple past tense.  

- **〜ている** – a pattern that expresses a continuing state or action.  
  *Example: 〜ている* “is doing/has been doing”  
  It is comparable to “-ing” in English, but also can mean “has finished” depending on context.

### N1 — 彼女は宝石を得意げに見せびらかした。
_8 words, 4 bullets, 500 ms — judge: fit 5/5, acc 3/5 — Explanation is appropriately advanced for N1 but contains minor inaccuracies about the function of the past tense and the particle を._

- **得意げに**：形容動詞＋**げ**で自慢げな語感を付与し、動作の態度を強調する。  
- **見せびらかした**：動詞の**た形**で完了を示し、文末の「した」は非敬語の過去表記。  
- **を**：目的語を明示し、主語が動作の対象を強調。  
- **彼女は**：主語提示で対比や焦点を明確化し、文全体のリズムに寄与。

### N5 — 彼の福祉の概念はかなり観念的だ。
_155 words, 5 bullets, 875 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and clear, though a few terms may be slightly above strict N5 vocabulary._

- **は (wa)** – A particle that marks the topic of the sentence, like “as for.”  
  In the sentence it tells us that *彼の福祉の概念* is the subject being talked about, similar to the English “about” in “Regarding his concept of welfare …”

- **の (no)** – A particle that links nouns, showing possession or a descriptive relation.  
  Here it connects *彼の* (his) with *福祉* (welfare) and then *福祉* with *概念* (concept), forming the phrase “his concept of welfare.”

- **かなり (kanari)** – An adverb meaning “quite” or “pretty.”  
  It modifies the adjective *観念的* (abstract), just as “quite” modifies “abstract” in “quite abstract.”

- **観念的 (かんねんてき)** – An adjective meaning “abstract” or “ideal.”  
  It describes *概念* (concept) and functions like the English adjective “abstract.”

- **だ (da)** – A copula (verb “to be”) used in plain, present form.  
  It connects *観念的* to the subject, like the verb “is” in “His concept of welfare is pretty abstract.”

### N1 — 彼の福祉の概念はかなり観念的だ。
_12 words, 4 bullets, 666 ms — judge: fit 3/5, acc 2/5 — Explanation contains several inaccurate statements about the particles and grammar, making it unsuitable for an N1 learner._

- **の**（連体修飾格）: 連用形＋ので複数名詞を修飾し、所有や範囲を示す。  
- **は**（対比助詞）: 主題提示＋対比、特異性を強調。  
- **かなり**（程度副詞）: 「相当」「かなり」の語源と近年の軽量化・口語的度合い。  
- **だ**（判定表記）: 非自動詞の断定で、形容動詞とともに格位を保持。

### N5 — この岩は何に似ていますか。
_168 words, 5 bullets, 570 ms — judge: fit 3/5, acc 2/5 — Explanation contains some correct points but uses overly technical terms and mislabels 似ている, making it less suitable and partially inaccurate for an N5 learner._

- **～に** – a particle that shows the *target* or *comparison point*. In this sentence it marks what the rock is compared to, like the English "to" in "look *like* what?"  
- **似ている** – the verb meaning "to resemble". It is an **い形容動詞** (i‑adjective-like noun) that takes the particle **に** after it, so you say *〜に似ている*.  
- **です** – polite copula, turns the verb phrase into a question when followed by **か**. It’s the Japanese equivalent of saying “is” or “are” in English.  
- **か** – question marker added at the end of a polite sentence. It turns a statement into a yes/no or open question, similar to adding a question mark in English.  
- **この岩は** – **は** marks the topic “this rock.” It tells the listener what the sentence is about, like saying “As for this rock…” in English.  

These patterns combine to form the question: “What does this rock look like?” Each pattern plays a small but crucial role in making the sentence clear and polite.

### N1 — この岩は何に似ていますか。
_13 words, 4 bullets, 287 ms — judge: fit 5/5, acc 4/5 — 説明はN1向けに語彙と用法を概ね捉えているが、‘相似性の観点’や‘形容動作’といった表現がやや不自然で、‘不定指示語の省略’の説明が不正確です。_

- **〜に似ている**: 表示「相似性の観点」; 動作主体は形容動作であり、比較対象は名詞。  
- **疑問形の接続**: 「～か」付与で聞き手への確認。  
- **不定指示語の省略**: 「何に」が曖昧で、相対的な基準を暗示。  
- **「この岩は」主語の指示性**: 地理的・視覚的関係を前提に、類比先を想定。

### N5 — この報告書は要領をえていない。
_135 words, 5 bullets, 749 ms — judge: fit 4/5, acc 2/5 — The explanation is mostly appropriate for N5 but misidentifies the verb and omits the correct meaning of 要領を得ていない._

- **は** (wa) – a topic marker that shows what the sentence is about. It’s like “as for” in English.  
- **を** (wo) – an object marker that shows what the verb is acting on. It’s similar to “to” in “I eat **the** apple.”  
- **〜ている** – a verb ending that describes a state or ongoing action. Think of it as the English “-ing” or “-ing state” (e.g., “I am reading”).  
- **ない** – the negation ending that turns a sentence into “not” or “does not.” It’s like adding “not” in English.  
- **〜ていない** – when “ている” is combined with “ない,” it says the state is not happening. It’s equivalent to “is not doing” or “has not done.”  

These patterns together show that the report is *not* in the state of being to the point.

### N1 — この報告書は要領をえていない。
_13 words, 4 bullets, 905 ms — judge: fit 3/5, acc 2/5 — The explanation is roughly N1‑level but contains lexical errors (要領をえていない) and misinterprets the nuance of 要領を得ていない._

- **〜ている → 〜ていない**: 「ている」の否定形で、継続的な状態や結果が成立していないことを示す。  
- 「要領をえていない」では「要領を得る」＋「ていない」を用い、報告書が「要領を得ていない＝要点を掴めていない」状態を強調。  
- ここでの ていない は「まだ達成されていない」ニュアンスを含むため、報告書が「未完成・未確定」であることを示す。  
- 形容動詞的な「〜ていない」よりも、動作の継続性・状態の

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_181 words, 5 bullets, 921 ms — judge: fit 2/5, acc 3/5 — The explanation is generally correct but uses advanced grammar like であろう and contains minor inaccuracies, making it a poor fit for an N5 learner._

- **〜ている**  
  Used after a verb to show a state that continues or is happening now. It is the same idea as the English present continuous “is living” or “is doing”.  
  Example: 住んでいる = “is living / lives” on the ice cap.

- **〜のだ**  
  A sentence ending that gives an explanatory tone, like saying “you see” or “I tell you that” in English. It adds a little emphasis or explanation.  
  In the sentence, なのだ gives a soft explanatory feel before the contrast.

- **〜が**  
  A particle that joins two clauses, often meaning “but” or “however” in English. It shows a contrast or a turn of thought.  
  なのだが = “but” after explaining something.

- **〜であろう**  
  A polite, speculative ending meaning “will probably / might”. It is similar to “might” or “will probably” in English.  
  であろう is the formal version of だろう, used to guess about the future.

- **〜を**  
  The object marker particle. It tells you which noun is the object of the action, like “the home” in 失い、.  
  It is simple: the noun before を is what the verb acts on.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_9 words, 3 bullets, 702 ms — judge: fit 4/5, acc 4/5 — Explanation is mostly appropriate for N1 but contains a minor mistake ('体制' vs '状態') and could use slightly more advanced nuance._

- **〜ているのだ**  
  体制を表す状態が続くことを強調し、話し手の認識・説明を示す。ここでは「北極熊は極地の氷原に住んでいる」の事実を客観的に提示し、後続の対比へ橋渡しする。

- **〜のだが**  
  「のだ」の後に接続助詞「が」を付けることで、事実と対立・補足情報を同時に提示。情報の対比や反論のニュアンスが微妙に増す。

- **〜であろう**  
  未来の推量を示す推測表現。丁寧語調と予測の不確実性を兼ね備え、文学的・予感的語感を高める。ここでは「絶滅するであろう」が恐怖感と科学的予測を同時に訴える。


## qwen/qwen3.8-27b (groq)

### N5 — もう３ページ残っている。
_115 words, 3 bullets, 2199 ms — judge: fit 4/5, acc 4/5 — Explanation is mostly correct and appropriate for N5, but the nuance of もう could be clearer and some phrasing is slightly beyond N5 simplicity._

- **〜ている** — a form you add to verbs to describe a state that continues after something happens. Here, 残る means "to remain." 残っている = the pages *remain* (the current situation). In English, this is like saying "there are three pages left" — you're describing what's true right now, not an action.
- **もう** — a small word that usually means "already," but next to a "remaining / left" expression it shifts to mean "still" or "at least ~ left." It flags the amount that's *still there* to do.
- **Counter (ページ)** — ３ページ is number + counter. In Japanese the number always comes *before* the thing being counted (three → pages), the opposite of

### N1 — もう３ページ残っている。
_43 words, 2 bullets, 4836 ms — judge: fit 5/5, acc 5/5 — The explanation correctly captures the nuance of ている as a static result and the usage of もう as “still” for an N1 learner._

- **〜ている** — 存續の「ている」; marks the persisted state of incompleteness from a prior bounded event (the act of finishing), not progressive aspect.
- **もう** — here "still" (残存), not "already"; scopes the quantity as unexpectedly persistent, carrying a faint tone of unfulfilled obligation.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_163 words, 4 bullets, 48095 ms_

- **〜と** — connects two or more nouns, meaning "and." It works exactly like English "and": you just line up items with this particle between them. No extra meaning, no nuance — just listing.
- **〜と一緒に** — means "together with" or "along with." It marks a *secondary* item attached to the main action. In English, "along with" does the same job: the sentence is really about one thing (the chicken), and the rest is extra baggage. You could drop it and the sentence would still be grammatically fine.
- **〜を** — object particle. Marks the noun that the verb acts on directly. Here it sits before 鶏肉 because that is what he ate. You already use this; it's just doing its normal job.
- **〜た** — past tense marker. Attached to the verb (食べ**た**), it moves the action into the past. Same pattern you've been using — nothing new here, just flagging it so you can see all the pieces in one sentence.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_43 words, 2 bullets, 1037 ms — judge: fit 5/5, acc 3/5 — 説明はN1向きの語彙で書かれているが、〜とと〜と一緒にの関係を誤って解釈しており、正確さに欠ける。_

- **〜と** — 列挙. Here it groups サラダ and ロールパン into a single co-consumed unit before being combined with 一緒に.
- **〜と一緒に** — 同伴/付随. Notional scope: the と-group (salad + rolls) is pragmatically subordinate to the main object 鶏肉 (primary item). cf. **〜とともに**

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_174 words, 5 bullets, 2510 ms_

- **〜てください** — Attach this to a verb's "te-form" (a connective shape every verb takes) to make a polite request. It's like English "please do X." Here: 滴下してください = "please drip/apply it."
- **〜て (sequence)** — You can link actions in order by ending each verb in its te-form. It signals "do A, then B, then C" — very similar to how English strings short commands: "Remove the cap, fill the dropper, apply the ink." This sentence does exactly that: 外し、吸い上げ、滴下してください.
- **へ** — A small particle marking the *target* or *destination* of an action. Think of it as "toward ~" or "onto ~" in English. Here it points to where the ink goes: 吸収体**へ** = "onto the core."
- **を** — You already know this one. It marks the object — the thing that gets acted on. インキ**を**吸い上げ = "suck up the ink."
- **の** — A particle that glues two nouns together, like "of" or "'s" in English. インキ補充瓶**の**キャップ = "the cap of the ink bottle." It's very common in product descriptions.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_90 words, 3 bullets, 1023 ms — judge: fit 5/5, acc 5/5 — The explanation correctly addresses the nuanced particle choice, noun‑verb construction, and sequential te‑form usage appropriate for an N1‑level learner._

- **へ** (vs に): 方向粒子 in technical/instructional register; marks trajectory of the substance being deposited. に would be acceptable in casual contexts but loses the "onto/surface-directed" specificity standard in lab and product manuals.
- **適量 + comma + verb**: 量名詞 used adverbially without だけ/程度. The comma is a typographic convention in 製品マニュアル that isolates the quantity as an independent instruction point (≈ "a suitable amount — then: drip").
- **連用形 + 連用形 + ください**: Sequential te-form chain (外し、吸い上げ、) terminating in polite imperative. Standard for 3+ step procedures in instructional prose.

### N5 — 関税申告書が必要になります。
**ERROR** `empty`

### N1 — 関税申告書が必要になります。
_75 words, 2 bullets, 7204 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N1 depth, accurately describes the nuance of 必要になる versus なければならない and the formal use of になります._

- **必要になる** — encodes *non-agentive, external necessity* (procedural, legal, institutional). Contrast with **なければならない** (subjective compulsion, directed at an agent). In bureaucratic register this is the default for stating what a document/system *demands* independent of any actor's will.
- **〜になります** — the **な** copula of 必要 is promoted here; not a separate grammar point but worth noting that the elevated register of **なります** is standard in written administrative prose, signalling *formal notification* rather than casual advice.

### N5 — この本には美しい挿絵が入っている。
**ERROR** `empty`

### N1 — この本には美しい挿絵が入っている。
_87 words, 3 bullets, 18038 ms — judge: fit 5/5, acc 5/5 — The explanation is appropriately advanced for N1 and accurately analyses the usage of 入る, ている, and には in the sentence._

- **〜に入る** — here not physical entry but the idiomatic "to be included in a compilation/bounded work" (作品集・カタログ・目録). Distinct from 載る (more common for periodicals); 入る implies a static, curated whole.
- **〜ている** — resultant-state reading on an intransitive; no agent is recoverable. The state is treated as an inherent property of the container, not an event.
- **には** — container/topic frame; the は signals the host entity under discourse focus, while に marks the spatial/containment relation. Together they set up the "contents-of" reading without an agent.

### N5 — 彼女は宝石を得意げに見せびらかした。
_104 words, 3 bullets, 45379 ms — judge: fit 2/5, acc 3/5 — The explanation mixes correct points about な‑adjectives with inaccurate/premature details (e.g., the た‑form rule) and uses vocabulary beyond N5._

- **な-adjective + に** — A な-adjective is a type of adjective (like 静かな or 得意げ) that normally comes before a noun with な. When it instead modifies a verb, な switches to に. It tells you *how* the action happened, kind of like how "quietly" changes from "quiet + ly" in English.
- **〜た (past tense, Group 1)** — Group 1 verbs end in ぬ, ぶ, む, or す. To say the action is finished, drop that ending and add した. Think of it like the "-ed" we add in English (walk → walked).
- **を** — a particle that marks the direct

### N1 — 彼女は宝石を得意げに見せびらかした。
_12 words, 2 bullets, 17035 ms — judge: fit 4/5, acc 3/5 — Explanation uses advanced terminology appropriate for N1 but contains some inaccurate or overly convoluted points about 〜げに and 見せびらかす._

- **〜げに** — 様態助動詞；より っぽい より文語的。主語の意識的・能動的な振る舞い（本能的 っぽい との対比）を暗示。
- **見せびらかす** — 動詞複合語の「びらかす」は過剰な誇示を内包し、話者側の貶的評価が節構造に既定の値として埋め込まれている。賓語が可算・具体的（宝石）であることで、客観的基準の上での優越を示唆する構造が機能する。

### N5 — 彼の福祉の概念はかなり観念的だ。
_161 words, 4 bullets, 46504 ms — judge: fit 2/5, acc 2/5 — The explanation mislabels 観念的 as an i‑adjective and uses vocabulary beyond N5, though the particle の and だ descriptions are roughly correct._

- **の** — a particle (a small word that marks a noun's role) that connects two nouns to show possession or attribution. Works like "of" or the English possessive **'s**: 彼の概念 = "his notion."
- **〜だ** — the casual (plain) form of **です** ("is / are"). In everyday, informal Japanese, です gets replaced by だ. It's not grammatically different in function, just in register — like switching from "It is" to "It's gone" in a text message.
- **i-adjective + だ** — adjectives that end in **い** can simply stack onto だ with no change: 観念的**だ**. The い never drops. In English there's no exact equivalent, but think of it as the adjective and the "is" fusing: *big* + *is* → *big-da*.
- **かなり** — an adverb (a word that modifies an adjective or verb) meaning "pretty" or "quite." It slots in right before the adjective it describes: かなり観念的 = "pretty abstract." It never changes form, no matter what it modifies.

### N1 — 彼の福祉の概念はかなり観念的だ。
**ERROR** `empty`

### N5 — この岩は何に似ていますか。
_118 words, 3 bullets, 51756 ms — judge: fit 5/5, acc 5/5 — The explanation matches N5 level vocabulary and correctly explains the grammar of 何に似ていますか._

- **〜に** — a particle (a small word that marks a noun's role in a sentence). Here it points to *what* something is being compared to. Think of it like the word "like" in English: "What does it look **like**?"

- **似ている** — means "looks like" or "resembles." It comes from the verb 似る (to resemble). The ている ending describes a **current state** — how the thing looks right now, not a one-time action.

- **〜ています** — the polite form of ている. In N5 you'll meet this a lot. It works like the English "-ing" when you're describing a state that is true now: "It *is* looking like X" → naturally English just says "It looks like X."

### N1 — この岩は何に似ていますか。
_56 words, 3 bullets, 12828 ms — judge: fit 5/5, acc 5/5 — The explanation accurately covers the grammar of 〜に似ている and is well‑suited to an N1 learner._

- **〜に似ている** — intransitive; に marks the comparative standard. Transitive counterpart is **〜を似せる** (rare, literary; 顔に似せる).
- **〜ている** — stative only here; never progressive. Negation: **似ていない** (not *似てない* in formal registers, though colloquial contraction is common).
- Particle に is obligatory for the standard; 何に is the canonical question form (not 何か/何かに, which would imply vagueness).

### N5 — この報告書は要領をえていない。
_73 words, 2 bullets, 42163 ms — judge: fit 2/5, acc 1/5 — The explanation misdescribes ている/ていない and the example sentence contains a grammatical error, making it unsuitable for an N5 learner._

- **〜ている** — Take the te-form of a verb and add ている. It describes a state that results from a completed action. Think of English "is [having done X]." Here it means the report *has gotten* to the point and sits in that state.
- **〜ていない** — Simply ている made negative. It says the action hasn't happened or the resulting state doesn't exist. In this sentence, the state of "being to the point

### N1 — この報告書は要領をえていない。
_56 words, 3 bullets, 18177 ms — judge: fit 5/5, acc 5/5 — The explanation is appropriately advanced for N1 and correctly describes the fixed expression 要領を得ていない._

- **要領を得ない** — fixed collocation, not a productive V-au の potential construction. Implies the text is *opaque* or *logically incoherent*, not merely off-topic. Stronger than 要旨が不明.
- **〜を得ない** as a set frame also appears in 気分を得ない, meaning → idiomatic; don't decompose.
- Register: evaluative-critical, suiting reviews or written commentary. Spoken equivalent would be 要領がわかんない or 何を言ってるのか.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_128 words, 4 bullets, 46537 ms — judge: fit 2/5, acc 4/5 — The explanation is fairly accurate but uses terminology and forms (like のだが and であろう) that are beyond typical N5 expectations._

- **〜ている**: You may know it as "is doing" (食べている = "is eating"). Here it also shows a long-lasting state — "lives there," not a one-time action. English "lives" and "is living" are two different forms; Japanese ている handles both.
- **〜のだが**: のだ is an explanation marker, adding a tone like "you see" or "as you know." が is the contrast particle, like "but." Together they set up the bad news: "It lives on the ice, *but*…"
- **masu-stem + い (e.g., 失い)**: Drop ます from the polite form to get the stem (失います → 失い), then attach it to the next verb. It chains two actions in order — "do A, then B." Compare to English "lose its home **and** die out."
- **〜であろう**: A formal, written-sounding

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_14 words, 1 bullets, 18186 ms — judge: fit 5/5, acc 5/5 — The explanation correctly identifies であろう as a formal evidential conjecture appropriate for N1 level._

- **〜であろう** — Evidenced conjecture in formal expository register; implies inference from stated premises


## command-a-plus-05-2026 (cohere)

### N5 — もう３ページ残っている。
_132 words, 5 bullets, 2095 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and mostly suitable for N5, though a few terms could be simplified further._

- **〜ている** (present progressive/state) – shows that something is continuing now; compare to “is remaining” in English. In 残っている, it means “are left” or “remain.”
- **もう** (adverb) – adds the sense “already” or “still,” indicating the situation is as expected at this point; like “already” in “I’ve already read three pages.”
- **名詞 + 残っている** (noun + remain‑present) – a common pattern meaning “there are X left”; the noun tells what is remaining, and 残っている tells its current state.
- **数字 + ページ** (quantity + unit) – used to count pages; the number comes before the noun, just as in English “three pages.”
- **動詞 残る（のこる）** – the base verb “to remain”; when changed to 残っている, it becomes the present state form, similar to turning “to be left” into “are left.”

### N1 — もう３ページ残っている。
_55 words, 2 bullets, 2388 ms — judge: fit 5/5, acc 5/5 — The explanation correctly captures the resultative meaning of 残っている and the nuance of もう indicating a minimal remainder at an N1 level._

- **〜ている** (resultative present): “残っている” denotes a state where pages remain, not the act of leaving them; with “もう” it signals the remainder is minimal, implying imminent completion.  
- **もう**: adverbial marker of proximity to a limit; when paired with a present progressive, it intensifies the sense of “almost done” rather than “still in progress.”

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_124 words, 5 bullets, 3141 ms — judge: fit 5/5, acc 5/5 — The explanation is clear, appropriately simple for N5, and accurately describes each grammar point in the sentence._

- **は** – topic marker; it shows the subject of the sentence. Think of it like “As for X” in English. In this sentence it tells us the topic is “彼” (he).  
- **を** – object marker; it points to the direct object of the verb. It works like the “accusative” case, e.g., “chicken” is what he ate.  
- **と** – “and” for listing items; it joins nouns in a simple list, similar to saying “salad and rolls.”  
- **一緒に** – “together with”; this adverb adds the meaning of doing something alongside something else, like “together with” in English.  
- **食べた** – past tense of the verb “食べる” (to eat); it tells us the action happened in the past, comparable to “ate” in English.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_75 words, 4 bullets, 2200 ms — judge: fit 4/5, acc 3/5 — Explanation uses appropriate N1 terminology but contains inaccuracies about the function of 一緒に and the aspect of た._

- **は**: topic marker; foregrounds *彼* as the sentence’s focal point, implying contrast with other possible subjects.  
- **を**: direct object particle; marks *鶏肉* as the item undergoing the action, distinct from the concomitant *サラダ* and *ロールパン*.  
- **一緒に**: adverbial suffix indicating simultaneity; attaches to the noun phrase *サラダとロールパン* to denote concurrent consumption without implying causality.  
- **た**: past perfective aspect; finalizes the completed action *食べた* with a sense of finality, suitable for narrative register.

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_108 words, 5 bullets, 1673 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and clear, but uses slightly advanced terminology for an N5 learner._

- **〜を外し** – “remove …” (particle を marks the object being removed). Compare to English “take off the cap.”  
- **〜で吸い上げ** – “suck up … using …” (particle で shows the tool used). Think of “use the dropper to draw ink.”  
- **〜へ適量、滴下** – “drip an appropriate amount onto …” (particle へ indicates the destination). It’s like “pour the right amount into the marker’s core.”  
- **ください** – polite request “please do …” (adds a polite tone to the command). Similar to saying “please do the steps.”  
- **並列～、～、～** – a list of actions connected by commas, meaning “do A, then B, then C” (used for step‑by‑step instructions).

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_16 words, 3 bullets, 2391 ms — judge: fit 3/5, acc 2/5 — 説明はN1学習者向けの語彙は適切だが、文法解説が誤っており、連用形+しや上げの説明が不正確であるため正確性が低い。_

- **〜を外し**：連用形 + しで前進する動作指示；前の行動を完了させ、次の行動へ移ることを促す。
- **〜を吸い上げ**：連用形 + 上げで抽出動作を強調；道具を用いた動作の意図と結果を明確にする。
- **〜へ適量、滴下してください**：目的語 + 助詞へ + 数量詞 + 動詞の命令形；「滴下してください」は丁寧な指示で、動作の実施を要求。

### N5 — 関税申告書が必要になります。
_188 words, 6 bullets, 2057 ms — judge: fit 4/5, acc 4/5 — Explanation is mostly correct and clear, but some points (like the role of は and が) are over‑explained for N5 and a bit imprecise._

- **必要になります** – shows something becomes necessary; think of it as “becomes needed.” It’s like “is required” in English, but it adds the idea that the need is new or will happen in the future.  
- **は…が** – the particle **は** marks the topic (what we’re talking about), and **が** marks the subject of the verb “必要になります.” This is similar to “As for a customs declaration, it is required.”  
- **が** – a particle that points out the subject performing the action. Here it tells us the customs declaration is the thing that becomes necessary.  
- **です** – a polite ending that links the subject to its state. It works like “is” in a simple statement.  
- **名詞 + が + 動詞** – a noun followed by **が** then a verb shows the noun does the action. In English you’d say “A customs declaration is required,” but in Japanese the noun is the subject of the verb “becomes necessary.”  
- **〜になります** – a pattern meaning “becomes” or “turns into.” It’s used with many nouns to show a change to a new state, similar to “turns into” in English.

### N1 — 関税申告書が必要になります。
_46 words, 2 bullets, 1539 ms — judge: fit 4/5, acc 3/5 — The explanation is fairly advanced for N1 but misstates が as a topic marker and oversimplifies 必要になります._

- **必要になります**: nominal predicate indicating a transition to a required state; used in formal notices to convey that a specific item or action will become mandatory.  
- **が**: subject particle marking the preceding noun as the topic of the necessity; typical in official or written contexts.

### N5 — この本には美しい挿絵が入っている。
_123 words, 6 bullets, 1843 ms — judge: fit 4/5, acc 3/5 — The explanation is mostly appropriate for N5 but slightly misdescribes には and the nuance of ている, though the overall grammar points are correct._

- **この + Noun** – shows “this” something. It points to something near the speaker, like “this book.”  
- **には** – particle (ni wa) marks the place or item that receives the action, similar to “to” in “This book has illustrations.”  
- **美しい** – adjective describing the noun; it comes before the noun, just like “beautiful” before “illustrations.”  
- **挿絵** – noun meaning “illustration.”  
- **が入っている** – verb phrase meaning “are included” or “are inside.” It shows a state that started in the past and continues, comparable to “has … inside” in English.  
- **〜ている** (te-iru form) – used after verbs to show a continuous or resulting state; think of it as “is being” or “has been” (e.g., “the book is being illustrated”).

### N1 — この本には美しい挿絵が入っている。
_49 words, 2 bullets, 1447 ms — judge: fit 5/5, acc 5/5 — Explanation correctly captures the function of には, が, and the resultative ている for an N1 learner._

- **には…が入っている**: marks the location (or container) with には and asserts the presence of an entity inside; the subject of the sentence is the container, not the content.  
- **ている**: resultative aspect; denotes a state that has been achieved and continues, often translated as “is …ed” or “has …”.

### N5 — 彼女は宝石を得意げに見せびらかした。
_77 words, 4 bullets, 2424 ms — judge: fit 4/5, acc 4/5 — The explanation is mostly clear for N5 but slightly over‑explains the verb composition and could simplify the terminology._

- **は** — topic particle, shows the subject of the sentence (she).  
- **を** — object particle, marks what the action is done to (jewels).  
- **得意げに** — adverb ending in に, tells how the action is done (proudly). It works like “proudly” in English.  
- **見せびらかした** — past tense of the verb “見せびらかす” (to show off), meaning “showed off.” It combines the causative “見せ” and the verb “びらかす” (to flaunt), similar to “showed off” in English.

### N1 — 彼女は宝石を得意げに見せびらかした。
_50 words, 2 bullets, 1333 ms — judge: fit 5/5, acc 5/5 — The explanation accurately captures the nuances of 得意げに and 見せびらかした and is well‑suited for an N1 learner._

- **得意げに** – adverbial suffix indicating a self-assured, confident demeanor; often used in narrative to convey internal pride or arrogance, adding a subtle evaluative tone.
- **見せびらかした** – past tense of the compound verb “見せびらかす”; expresses deliberate, ostentatious display, typically with a negative or critical connotation toward the subject's vanity.

### N5 — 彼の福祉の概念はかなり観念的だ。
_147 words, 6 bullets, 2576 ms — judge: fit 5/5, acc 4/5 — Explanation is clear and appropriate for N5, though the description of "形容詞＋だ" could be phrased more naturally._

- **〜の** (possessive particle) — connects a noun to another noun, showing ownership or relation; like “his book” in English. In *彼の福祉の概念*, “彼の” means “his” and “福祉の” means “of welfare.”  
- **〜は** (topic marker) — shows what the sentence is about; it’s like saying “As for X…” in English. *彼の福祉の概念は* tells us the topic is “his notion of welfare.”  
- **かなり** (adverb) — adds the degree “pretty” or “rather” to the adjective that follows.  
- **〜だ** (copula) — links the subject to a description, similar to “is” in English. In *観念的だ*, it says “is abstract.”  
- **形容詞 + だ** (adjective predicate) — a simple way to make a statement with an adjective, just like “abstract is” in informal English.  
- **名詞 + の + 名詞** (noun‑of‑noun) — a common way to create a compound noun, such as “concept of welfare,” showing a relationship between the two nouns.

### N1 — 彼の福祉の概念はかなり観念的だ。
_42 words, 2 bullets, 1639 ms — judge: fit 4/5, acc 5/5 — Explanation is accurate and appropriate for N1, though the terminology could be slightly more nuanced for full N1 depth._

- **「...の...は...だ」**: nominal topic‑comment construction; the genitive phrase marks the object, wa marks the topic, and da provides a predicative comment, often with evaluative nuance.  
- **「かなり...だ」**: intensifier + predicate; quite modifies the adjective, raising its degree without altering the grammatical function.

### N5 — この岩は何に似ていますか。
_137 words, 5 bullets, 2351 ms — judge: fit 4/5, acc 2/5 — The explanation misidentifies key parts (e.g., omits 似る and misstates 何に) and introduces unrelated ている, making it inaccurate for an N5 learner._

- **この** – demonstrative word meaning “this”; it attaches directly to a noun (e.g., *この岩* “this rock”). Think of it like pointing to something near you.  
- **何** – interrogative word meaning “what”; it asks for information about the noun that follows. In English you might say “What does it look like?”  
- **に** – particle that marks the thing being compared to. It tells us the noun before the verb is the “model” for the comparison.  
- **〜ている** – present‑continuous form of a verb meaning “is looking” or “looks.” It shows an ongoing state, similar to “is looking” in English.  
- **か** – sentence‑ending particle that makes the whole sentence a question, just like a question mark at the end of an English question.  

These pieces together form the question “What does this rock look like?”

### N1 — この岩は何に似ていますか。
_47 words, 2 bullets, 1538 ms — judge: fit 4/5, acc 5/5 — The explanation correctly describes 似ています and the 何に...か pattern, though it could use slightly more N1‑level nuance._

- **〜ています**: nominalizes a stative predicate, indicating a current likeness; “is resembling” rather than an ongoing action.  
- **何に...か**: wh‑question construction where the wh‑phrase is fronted and marked by に, then the main clause ends with か; yields “What does X look like (in terms of Y)?”

### N5 — この報告書は要領をえていない。
_146 words, 5 bullets, 2085 ms — judge: fit 4/5, acc 3/5 — The explanation matches N5 vocabulary and terms, but it misinterprets the sentence’s grammar and omits that 要領を得ていない means “doesn’t grasp the gist,” so its accuracy is only moderate._

- **「このXは」** – shows “this X” and marks it as the topic. The particle **は** tells us what we are talking about, like saying “this report” in English.  
- **「～を」** – direct object marker. It shows that the thing before it is being acted on, here “要領” (the point/essence) is what is being gotten.  
- **「～ていない」** – negative form of the present progressive “～ている”. It means “is not doing/does not have”. In English you could compare it to “is not …ing” or “doesn’t have”.  
- **「～ている」** – present progressive (or present continuous) meaning “is doing” or “has”. Used after verbs to show an ongoing state. Here it is turned negative to say the report does not have the point.  
- **「～ていない」** – combines the negative “ない” with “～ている” to say something is not in a certain state. It’s like saying “doesn’t have” or “is not …ing”.

### N1 — この報告書は要領をえていない。
_56 words, 2 bullets, 2393 ms — judge: fit 5/5, acc 4/5 — Explanation is appropriate for N1 but slightly misstates the verb form and nuance of 要領を得ていない._

- **〜ていない**: denotes a current state where the described action or condition is absent; here, the report lacks the act of grasping the gist, implying it is unfocused.  
- **要領をえる**: a set phrase meaning “to capture the essential point”; its negative form conveys a failure to meet the expected conciseness, a critique of the report’s coherence.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_103 words, 5 bullets, 1792 ms — judge: fit 3/5, acc 4/5 — The explanation is mostly correct but includes concepts and terminology beyond typical N5 scope and misses a brief note on the advanced grammar of であろう._

- **〜は〜に住んでいる** – Shows where something exists now; like “The polar bear lives on the polar ice‑cap.” It’s the present progressive “is living.”  
- **〜のだが** – Connects two ideas, the first giving background, the second a contrast; similar to “although” or “but.”  
- **〜を失う** – Means “to lose” something; the object is the thing being lost, like “lose its home.”  
- **〜絶滅するであろう** – Predicts a future result; the “will” in English, used after a cause.  
- **〜ていく** – Not present here, but note that many N5 verbs use it to show gradual change; compare “to gradually disappear” (e.g., “The ice is melting away”).

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_72 words, 3 bullets, 2208 ms — judge: fit 5/5, acc 4/5 — The explanation is clear and appropriate for N1, but it misstates that 失う takes a location object and omits that であろう is a formal speculative form of だろう._

- **～ているのだが** – concessive connective linking a present progressive clause to a contrasting outcome; the “ている” emphasizes ongoing state, while “のだが” signals a concession that leads to the subsequent clause.  
- **～を失う** – transitive verb phrase indicating loss of a location; the subject’s existential base is the object of the loss.  
- **絶滅するであろう** – modal suffix “であろう” expresses future prediction with a degree of certainty, often used in formal or academic discourse.
