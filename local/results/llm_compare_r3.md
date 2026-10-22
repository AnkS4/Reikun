# LLM comparison — grammar explanations

## Format adherence (level-aware prompts)

| model | level | n | bullets ok | words ok | bolded | leaks | errors | avg ms |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1026 |
| openai/gpt-oss-120b | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1802 |
| openai/gpt-oss-20b | N1 | 10 | 9/10 | 10/10 | 10/10 | 0 | 0 | 680 |
| openai/gpt-oss-20b | N5 | 10 | 9/10 | 10/10 | 10/10 | 0 | 0 | 808 |
| gemini-3.5-flash-lite | N1 | 10 | 7/10 | 10/10 | 10/10 | 0 | 0 | 5858 |
| gemini-3.5-flash-lite | N5 | 10 | 9/10 | 10/10 | 10/10 | 0 | 0 | 5607 |
| gemma-4-31b-it | N1 | 10 | 0/0 | 0/0 | 0/0 | 0 | 10 | 40147 |
| gemma-4-31b-it | N5 | 10 | 5/5 | 5/5 | 5/5 | 0 | 5 | 57743 |
| command-a-plus-05-2026 | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 2224 |
| command-a-plus-05-2026 | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 3633 |

## openai/gpt-oss-120b (groq)

### N5 — もう３ページ残っている。
_141 words, 5 bullets, 7117 ms — judge: fit 4/5, acc 2/5 — The explanation correctly covers もう and the ～ている construction, but mentions a non‑existent に particle and misstates もう as “still,” making it partially inaccurate for the sentence._

- **もう** – “already” or “still” used to show something continues up to now; similar to English “still have” in “I still have three pages left.”  
- **～ている** – the -te form plus いる indicates a continuing state or result; works like English “to be + -ing” (e.g., “is remaining”).  
- **数 + カウンター + が** – a number plus a counter (pages) followed by the subject particle が marks what is being counted; comparable to “three pages” as the subject in “Three pages are left.”  
- **残る** – verb “to remain” in its dictionary form; when combined with ～ている it expresses that something is left at the present moment.  
- **...に** – the particle に can show the target of a quantity (e.g., “three pages left *in* the book”); similar to English “in” when indicating where the remaining amount exists.

### N1 — もう３ページ残っている。
_69 words, 3 bullets, 1443 ms — judge: fit 5/5, acc 5/5 — The explanation correctly captures the nuance of 〜ている as a resultant state, the meaning of もう with a quantity, and the use of 数量+残っている for indicating remaining amount, matching an N1 learner._

- **〜ている** expresses a resultant state derived from a preceding action; here 残っている conveys that three pages are in the state of remaining, not the act of leaving them.  
- **もう** before a quantity + 残っている signals “still” in the sense of “a further amount remains,” contrasting with 完了感.  
- **数量+残っている** functions as a quasi‑adverbial phrase denoting the amount of distance/time left, often used in travel or progress contexts.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_127 words, 5 bullets, 970 ms — judge: fit 5/5, acc 5/5 — The explanation is well‑suited to an N5 learner and accurately describes all particles and the past tense in the sentence._

- **は** – a particle (a tiny word that shows the noun’s role) marking the topic; it tells the listener “as for him…”, similar to saying “regarding” in English.  
- **と** – a particle used to list items, meaning “and”; it works like the English “and” when you put several things together.  
- **と一緒に** – a phrase meaning “together with”; it adds the idea of doing something at the same time as something else, like “along with” in English.  
- **を** – a particle that marks the direct object, the thing directly acted upon; comparable to the English “(object)‑do” structure, e.g., “eat *the chicken*.”  
- **た** – the past‑tense ending for verbs; it changes a present action into “did,” just like adding “‑ed” to an English verb.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_20 words, 4 bullets, 888 ms — judge: fit 4/5, acc 2/5 — The explanation misinterprets the function of と and と一緒に, leading to inaccurate analysis despite using appropriate N1 terminology._

- **と** (列挙) → 複数名詞を対等に並列させ、各要素が同格であることを示す。ここでは「サラダ」と「ロールパン」の二項列挙が「鶏肉」と同格に扱われ、全体が「食べた」の対象になる。  
- **と一緒に** (共同行為) → 「一緒に」は同行・同時性を強調し、主体が共に行うことを示す副助詞的表現。主語「彼」が「サラダ」と「ロールパン」と同時に「鶏肉」を摂取したことを示す。  
- **を** (対格助詞) → 直接目的語を明示し、動作の対象を限定。ここでは「鶏肉」を唯一の直接目的語とし、列挙された他の食材は「と一緒に」により付随的に扱われる。  
- **た** (過去形) → 完了・経験の意味を付与し、過去に完結した動作を示す。文全体の時間的枠組みを過去に固定する。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_116 words, 5 bullets, 964 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N5 vocabulary and accurately describes each particle and the request form._

- **の** – a particle that shows possession or relationship, like “of” in English. *インキ補充瓶のキャップ* means “the cap of the ink‑refill bottle.”  
- **を** – a particle that marks the direct object (the thing a verb acts on). In *キャップを外し*, “キャップ” is what is being removed.  
- **て** – the verb‑て form connects actions in order, similar to “and then” in English. Here *外し、吸い上げ、滴下してください* strings three steps together.  
- **へ** – a particle indicating direction or goal, like “to” or “toward.” *吸収体へ* means “to the absorber (core) of the marker.”  
- **ください** – a polite request form that follows the verb stem, equivalent to “please do …” in English. *滴下してください* asks the listener to “please drip.”

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_90 words, 4 bullets, 933 ms — judge: fit 5/5, acc 5/5 — The explanation accurately captures the N1‑level grammar points and their usage in the procedural sentence._

- **V連用形＋、** → enumerates successive actions in written instructions, yielding a crisp, procedural register.  
- **Vてください** → polite request for the listener to perform the final action; the preceding て‑form links it to earlier steps, emphasizing completion of the sequence.  
- **Nへ＋V** → directional particle marking the target of a transfer (here, the ink onto the marker’s absorbent core), often used in technical manuals for precision.  
- **適量** as a pre‑modifier of a verb (滴下してください) → conveys an implicit quantitative nuance without explicit numeric expression, common in formal procedural text.

### N5 — 関税申告書が必要になります。
_132 words, 5 bullets, 1065 ms — judge: fit 5/5, acc 4/5 — The explanation is clear and suitable for N5, but it mislabels 必要 as a noun/adjective instead of a na‑adjective._

- **が** – particle — a small word that marks the subject (the thing doing or being described). It’s like the English “*as for*” that points out what we’re talking about.  
- **必要** – noun/adjective – means “necessary” or “required”. When used by itself it works like the English word “necessary”.  
- **になる** – verb phrase – になる combines the verb *なる* (“to become”) with another word, turning that word into a state. It’s similar to English “to get” in “gets needed”.  
- **必要になる** – pattern – attaches *になる* to a noun/adjective to say “becomes necessary”. Think of “needs to become” as in “the form needs to become required”.  
- **です** – copula – the polite “to be”. It makes the statement polite, just like adding “is” in a formal English sentence.

### N1 — 関税申告書が必要になります。
_60 words, 2 bullets, 2029 ms — judge: fit 4/5, acc 5/5 — The explanation correctly describes the usage of になる and が, though it could use slightly more advanced terminology for an N1 learner._

- **〜になる**: 「必要になる」 indicates a change of state or emergence of necessity, often implying that the requirement arises due to external conditions rather than being an intrinsic property.  
- **が** (subject marker for inanimate): marks 「関税申告書」 as the entity that undergoes the change, emphasizing its role as the object that becomes required, contrasting with 「は」 which would foreground the topic.

### N5 — この本には美しい挿絵が入っている。
_110 words, 4 bullets, 2005 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N5 level and accurately describes the particles and verb usage._

- **に** – particle that marks the place something exists or the target of an action; here it shows “in the book.” (English “in/at”)

- **は** – topic marker, a small word that tells the listener what the sentence is about; when attached after に it makes “as for this book.”

- **が** – subject marker, a particle that points out what is doing or being described; it highlights “the beautiful illustration” as the thing that exists.

- **入っている** – the verb 入る (to go in) in the **ている** form, which shows a current state resulting from an action; similar to English “is/has … inside” (e.g., “has been put in”).

### N1 — この本には美しい挿絵が入っている。
_7 words, 2 bullets, 571 ms — judge: fit 5/5, acc 4/5 — Explanation is appropriately advanced for N1, but the claim that 入っている conveys a passive nuance is inaccurate._

- **Vている**（結果・状態）: 「入っている」は動作の完了が現在の状態に持続していることを示し、物理的に内部に存在する様相を描写する。  
- **Vている**（受動的含意）: 文脈次第で「入っている」は外部からの施行（例: 挿絵が作者により本に組み込まれた）を暗示し、受動的ニュアンスを帯びる。

### N5 — 彼女は宝石を得意げに見せびらかした。
_113 words, 5 bullets, 1261 ms — judge: fit 3/5, acc 5/5 — The explanation is grammatically correct but includes the ~げ suffix, which is beyond the typical N5 curriculum._

- **は** – topic particle; marks what the sentence is about, like “as for …”. It’s similar to saying “regarding” in English.  
- **を** – object particle; shows the direct object that the verb acts on, comparable to the English “‑​object” after a transitive verb.  
- **に** – adverbial particle; turns a noun into an adverb describing how an action is done, like “proudly” in English.  
- **～げ** – appearance suffix; attached to a noun to mean “seeming …”, “looking …”. It conveys the speaker’s impression, e.g., “得意げに” → “looking proud”.  
- **～た** – past tense ending; attaches to a verb to indicate a completed action, similar to the English simple past “‑ed”.

### N1 — 彼女は宝石を得意げに見せびらかした。
_4 words, 2 bullets, 963 ms — judge: fit 5/5, acc 5/5 — The explanation accurately describes the げ and びらかす constructions and matches N1 proficiency._

- **Adj‑げに**：形容詞・形容動詞＋げで「…らしい様子」を副詞的に表す。感情・態度の主観的評価を示し、文語的・皮肉的ニュアンスを帯びやすい。  
- **V‑びらかす**：動詞連用形＋びらかすで「…を堂々と見せる」意味の複合動詞。動作の意図的・誇示的側面を強調し、文語体で頻出。

### N5 — 彼の福祉の概念はかなり観念的だ。
_80 words, 5 bullets, 580 ms — judge: fit 2/5, acc 4/5 — The explanation is mostly correct but the vocabulary in the sentence is beyond N5, making the pitch too advanced._

- **の** – particle that shows possession or connection, like “’s” in English.  
- **は** – topic particle that marks what the sentence is about, similar to “as for …”.  
- **かなり** – adverb meaning “quite” or “fairly”, used to intensify the adjective that follows.  
- **だ** – plain‑form copula, the basic “to be” verb used in informal statements.  
- **だ** after an adjective (概念は…だ) turns the adjective into a statement, just like adding “is” after an adjective in English.

### N1 — 彼の福祉の概念はかなり観念的だ。
_12 words, 3 bullets, 1081 ms — judge: fit 5/5, acc 4/5 — 説明はN1向きで概ね正しいが、のの説明で同格関係を示すと述べた点がやや不正確です。_

- **の** – 連体修飾格助詞；所有・所属・範囲を示す。ここでは「彼の福祉」の全体を「概念」の限定語として機能し、同格関係を暗示する。  
- **は** – 主題提示助詞；文全体を概念の性質評価に限定し、対照的焦点を設定することで、評価的述語「かなり観念的だ」を強調する。  
- **かなり観念的だ** – 「かなり」+形容動詞語幹＋**だ**の構造；「かなり」は程度副詞で評価を増幅し、形容動詞は連体形＋判定語「だ」で述語化し、客観的評価を示す。

### N5 — この岩は何に似ていますか。
_122 words, 5 bullets, 667 ms — judge: fit 4/5, acc 5/5 — The explanation is mostly appropriate for N5, though a few terms are a bit advanced, the grammar details are correct._

- **この** – a demonstrative adjective that points out something close to the speaker, like “this” in English.  
- **は** – the topic particle, a small word that marks what the sentence is about; similar to saying “as for …”.  
- **何に** – the question word “what” plus the particle に, which shows the target of a comparison; think of “what … like”.  
- **似ています** – the verb 似る “to resemble” in the ている form, which expresses a continuing state (like the English “looks like”). The ている form turns a verb into “‑ing” or “‑ed” meaning “is …”.  
- **か** – the question particle that turns a statement into a yes‑no or information‑seeking question, similar to adding a question mark in English.

### N1 — この岩は何に似ていますか。
_6 words, 2 bullets, 710 ms — judge: fit 5/5, acc 3/5 — Explanation is appropriate for N1 but contains inaccurate statements about the function of 「か」 and politeness._

- **～に似ている** 「似る」＋格助詞「に」で比較対象を示す。抽象的・具象的問答に使い、対象が不特定の場合は「何に」で疑問化し、読者の想像力を喚起する。  
- **～か** 文末疑問助詞。敬意を示す語調は語尾の上昇と「か」の有無で変化し、丁寧語体での直接質問を形成。

### N5 — この報告書は要領をえていない。
_123 words, 5 bullets, 2008 ms — judge: fit 3/5, acc 3/5 — The explanation uses some appropriate basics but misstates nuances and includes vocabulary beyond typical N5 scope._

- **は** – a particle — a tiny word that marks the topic of the sentence, similar to “as for” in English.  
- **を** – a particle — marks the direct object, like “the … that” in “I read the book.”  
- **～ている** – verb‑stem + て + いる indicates a continuing state; here “得ていない” shows the state of not having obtained something, comparable to “is not having” in English (“is not to the point”).  
- **ない** – plain negative form that turns a verb into “does not/ is not,” equivalent to adding “not” after a verb in English.  
- **要領** – a noun meaning “the point” or “essence”; when combined with the verb “得る” (to obtain) it expresses “to get the point.”

### N1 — この報告書は要領をえていない。
_9 words, 3 bullets, 835 ms — judge: fit 4/5, acc 2/5 — Explanation contains several inaccuracies (e.g., mis‑spelling of 得て, misuse of 四字熟語 label) and oversimplifies the nuance, though the overall depth is appropriate for N1._

- **～ている**（否定形）: 動詞の継続的・結果的状態を示す。ここでは「要領を得る」＝「要領がある」→「要領を得ていない」で「要領がない」＝「的確でない」状態を表す。  
- **要領を得る**: 四字熟語的慣用句。文字通り「要点をつかむ」意味だが、文語的・硬い語感があり、報告書・論文などの正式文書で頻出。  
- **要領をえていない**: 形容的用法。述語が形容詞的に機能し、対象の性質を評価する文体的効果として、批判的かつ客観的なトーンを醸し出す。

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_151 words, 6 bullets, 1383 ms — judge: fit 2/5, acc 4/5 — The explanations are mostly correct, but the vocabulary and grammar points (e.g., のだが, であろう) are too advanced for an N5 learner._

- **は** – topic particle, a small word that marks what the sentence is about; similar to saying “as for …” in English.  
- **に** – location particle, shows where an action takes place; comparable to “in/at” for static locations.  
- **住んでいる** – 「住む」 (to live) + ている (progressive/resultant form). The ている suffix attaches to a verb to indicate a continuing state, like “is living” rather than a one‑time action.  
- **のだが** – explanatory の (turns a statement into an explanation) + conjunction が (“but”). Together they mean “the fact is …, but …,” similar to “...you see, but …” in English.  
- **を** – object particle, marks the direct object of a verb; like “the … that …” in English sentences.  
- **であろう** – polite conjectural form of だ (to be). It expresses a guess about the future, comparable to “will probably …” or “is likely to …” in English.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_9 words, 3 bullets, 812 ms — judge: fit 5/5, acc 5/5 — Explanation matches N1 expectations and accurately describes the grammar points._

- **～ている**: 現在進行・継続状態を示す。ここでは「住む」の継続的存在を表し、自然環境に定着している様相を強調。  
- **のだが**: 断定的説明＋逆接。文全体を客観的事実として提示しつつ、後続の危機的展開への転換を示す文語的接続。  
- **であろう**: 推量の敬体。文脈上は必然的帰結の予測を示し、学術的・論説的トーンを保持する。


## openai/gpt-oss-20b (groq)

### N5 — もう３ページ残っている。
_240 words, 0 bullets, 787 ms — judge: fit 4/5, acc 3/5 — The explanation is mostly appropriate for N5, but contains some inaccuracies such as the wrong reading of 残る and a misleading description of もう._

**〜ている**  
A verb ending in **〜ている** shows an ongoing state or result of a previous action. Here, **残っている** means “is left” or “remains.” It’s similar to saying “has remained” in English, but you can think of it as “the state that still exists.”

**残る** (はずる)  
This verb means “to remain” or “to be left.” It is a **dictionary form** (plain form) and can be combined with **ている** to talk about a present state. In the sentence, **残っている** is just the combination of **残る + ている**.

**もう**  
A simple adverb meaning “already” or “anymore.” In this context it stresses that the pages have already been almost finished: “I already have three left.” It’s like the English “any more” used with “remain.”

**３ページ**  
This is the noun phrase “three pages.” In Japanese, the number comes before the noun. The particle **が** is omitted because the subject marker is unnecessary in this simple statement.

**いる**  
When attached to the て-form, **いる** indicates that a state is true now. It is the same **いる** you learn for “to be” with animate objects, but it can also mark inanimate states like “remain” or “continue.” Think of it as “is (presently)”.

**残っている** vs. **残る**  
If you only said **残る**, you’d be talking about the action of remaining (future or general). Adding **ている** makes it a *current state*: “there are still three pages left now.” This is the key difference between “remain” (verb) and “is remaining” (state).

### N1 — もう３ページ残っている。
_8 words, 4 bullets, 1431 ms — judge: fit 3/5, acc 2/5 — Explanation uses advanced terminology but contains several inaccurate statements about the grammar, making it only partially suitable for an N1 learner._

- **〜ている**：状態継続を示す非完了形で、残っているがまだ解消されていない点を強調。  
- **〜残っている**：残存状態の記述。ここで「ページ」は単位であり、数量表現を伴うことで「残数が確定」している。  
- **もう＋数量＋ページ**：完了・未完了の切れ目を示す「もう」を用い、未完了を前置的に提示。  
- **現在形＋残る**：動作主体が自動・受動ではなく、主体的に残りを把握する語調で、意識的な計測感を暗示。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_138 words, 5 bullets, 598 ms — judge: fit 5/5, acc 4/5 — Explanation is clear and appropriate for N5, though it oversimplifies the second と as merely a list connector instead of part of the と一緒に phrase._

- **は** – a particle that marks the topic of the sentence. It tells us who or what we are talking about, like “as for” in English.  
- **と** – a particle that links items in a list, similar to the English word “and.” In the sentence, it connects “salad” and “rolls.”  
- **と一緒に** – a phrase that means “together with.” It shows that two things happen at the same time or in the same place. It is like saying “with” in English, but only used after a noun.  
- **を** – a particle that marks the direct object, the thing that is acted upon. Here it shows that “chicken” is what was eaten.  
- **た** – the past‑tense ending for verbs in plain form. It indicates that the action already happened, like the English past tense “ate.”

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_12 words, 3 bullets, 494 ms — judge: fit 3/5, acc 2/5 — The explanation misinterprets the function of と and contains inaccurate grammatical statements, making it only partially suitable for an N1 learner._

- **と** で列挙し、主語が「何と何と」を同格に列挙している。  
- **と** を使った同格列挙は、主語が「一緒に」「同時に」という意味合いを強調し、複数の項目が同等に並列される点で、**～と** よりも**と** の方が統語的に強い。  
- **一緒に** と**と** の併用は、動作主体が複数対象を同時に享受することを明示し、語感的に「共食」的ニュアンスを持たせる。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_181 words, 6 bullets, 661 ms — judge: fit 4/5, acc 2/5 — The explanation contains several incorrect points (e.g., misuse of ～と and mentioning ～ている which isn’t in the sentence), so it’s not accurate for the N5 sentence._

- **～を** – a particle that shows the direct object of an action (like “the ball” in “I hit the ball”).  
- **～と** – a particle that introduces an explanation or reason; it’s a bit like “so” or “because” in English when you explain why you do something.  
- **～て** – the te‑form that links verbs together to show a sequence (one after the other). Think of it like a chain of actions: “open the cap, then fill the dropper, then drip”.  
- **～ている** – a verb ending that indicates an ongoing state or result of an action. In this sentence, it appears in “吸い上げている” (not shown directly, but you can imagine it as “I am drawing up the ink”). It’s similar to the English present continuous “I am drawing”.  
- **～ください** – a polite request marker that turns a verb into a polite “please do X”. It works like the English “please” used with a verb.  
- **～に** – a particle that points to a target or goal of an action, like the “to” in “pour onto the marker’s core”.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_77 words, 4 bullets, 587 ms — judge: fit 5/5, acc 5/5 — The explanation matches N1 expectations and accurately describes the grammar points in the sentence._

- **〜て** (連用形＋て) – connects sequential actions without explicit subject shift, emphasizing smooth progression.
- **〜を外す** – particle‑verb construction marking direct object removal; 〜を indicates the item being acted upon, 〜外す expresses physical detachment.
- **〜で吸い上げる** – 〜で as instrumental marker here indicates the means (スポイト) used to draw up ink, while 〜上げる conveys upward movement.
- **〜へ滴下する** – 〜へ denotes directional target (吸収体へ) rather than a location; 〜滴下する expresses the act of dispensing a controlled drop.

### N5 — 関税申告書が必要になります。
_213 words, 5 bullets, 895 ms — judge: fit 4/5, acc 5/5 — Explanation is accurate and clear, though slightly advanced terminology for a strict N5 learner._

- **が** – A particle that marks the subject or the thing that needs attention.  
  In this sentence, it tells us the *customs declaration* is the item that is needed. It is similar to “the” in English when we talk about a specific thing, but it does not mean “is”; it just shows the subject.

- **必要** – A noun meaning “necessary” or “required.”  
  When you put it after a noun (like 関税申告書), it describes that the noun has the property of being required. Think of it like saying “necessary ___” in English.

- **になる** – A verb phrase meaning “to become” or “to turn into.”  
  Here it attaches to 必要, turning it into a predicate that tells us a state: something becomes necessary. It is like saying “becomes necessary” in English.

- **必要になる** – A set pattern that means “becomes necessary” or “is required.”  
  It is the whole idea that a certain item will be needed. It is similar to the English phrase “will be needed.”

- **が + 必要になる** – The combination of the subject marker **が** with the pattern **必要になる** creates a short sentence that says “X becomes necessary.”  
  This is a common way to talk about future requirements in Japanese, just like saying “X will be required” in English.

### N1 — 関税申告書が必要になります。
_18 words, 4 bullets, 613 ms — judge: fit 4/5, acc 2/5 — Explanation contains several misunderstandings (e.g., calling 必要になる a 自動詞化 and mislabeling ます＋なる as 敬語), making it inaccurate despite being fairly detailed for N1._

- **必要になる**: 受動的状態変化を示す自動詞化; 「〜が必要になる」→「必要条件が成立する」  
- **〜ます**（**～ます**）＋**なる** → 敬語化; 「必要になります」＝「必要です」の丁寧表現  
- **〜になる**の「変化・確定」語感: 状態が「必須」に変わることを暗示し、主体が変化に対して受動的  
- 文脈依存: 請求書や手続きで「必須」となるとき、官庁や商習慣で「必要になります」＝法的・行政的必須を指す

（合計 57 語）

### N5 — この本には美しい挿絵が入っている。
_119 words, 4 bullets, 1099 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate and appropriate for N5, though the terminology could be slightly simplified._

- **には** – a combination of the topic marker **は** and the location marker **に**, used to say “in/inside” something. It’s like saying “in this book” in English.  
- **が** – a particle that marks the subject of the verb in a simple sentence. Here it shows that the illustrations are what “enter” the book.  
- **入っている** – the **〜ている** form of the verb **入る** (“to enter”) used to describe an ongoing state. It’s similar to the English present continuous “is entering” but means “has been placed/exists inside.”  
- **この** – a demonstrative adjective meaning “this.” It directly modifies a noun and is the Japanese way to point out something close to the speaker, much like the English “this.”

### N1 — この本には美しい挿絵が入っている。
_10 words, 4 bullets, 486 ms — judge: fit 3/5, acc 2/5 — 説明はN1向きの用語を使っているが、入っているは受動ではなく結果状態を表す自発的・結果的用法であり、説明に誤りがある。_

- **入っている**: 受動・存在表現として機能し、入っている状態を継続的に示す。物事が「入る」動作が完了し、その後もその位置に留まっていることを強調し、図版が本に「取り込まれた」状態を示す。  
- **〜ている**: 形容詞化された動詞で完了＋継続を同時表現。ここでは「入っている」が「美しい挿絵が入っている」と結びつき、静的状態の美しさを修飾。  
- 文脈的な「美しい挿絵が入っている」は、形容詞の「美しい」に対して受動形が加わり、視覚的な美しさを持つ「挿絵」の存在を強調。  
- 受動形の「入っている」が「美しい挿絵が入っている」という自然な構造を作り、図版が本の内側に「宿る」感覚を与える。

### N5 — 彼女は宝石を得意げに見せびらかした。
_157 words, 5 bullets, 590 ms — judge: fit 3/5, acc 2/5 — The explanation contains some inaccuracies (e.g., mentions です which isn’t in the sentence) and uses terminology that’s a bit advanced for N5._

- **は** – This marks the topic of the sentence. It’s like the word “as for” in English, showing what the sentence is about.  
- **を** – This marks the direct object, the thing the action is done to. Think of it like “to” in the phrase “give a gift to someone.”  
- **得意げに** – This is an adverbial phrase meaning “proudly” or “with confidence.” The げ suffix turns the adjective 得意 (good at) into an expression of how the action is done, similar to adding “proudly” after an action in English.  
- **見せびらかした** – The verb 見せびらかす means “to show off” or “to flaunt.” It ends in した because it’s the past tense of the plain form 見せびらかす, like “showed off” in English.  
- **です** – Used at the end of a simple descriptive sentence to politely state something. It’s similar to the copula “is” in “She is a student,” but here it just adds politeness.

### N1 — 彼女は宝石を得意げに見せびらかした。
_10 words, 4 bullets, 380 ms — judge: fit 5/5, acc 5/5 — 説明はN1学習者に適切な語彙と深さで、見せびらかすと得意げにの意味と文法的役割を正確に述べている。_

- **見せびらかす**：自らの所有物や成果を、他者の羨望・評価を意図した場面で、誇示的・挑戦的に提示する。  
- **得意げに**：主語の自信・自負を強調し、自己表現を相手へ押し付けるニュアンス。  
- **〜た** (過去形)＋**見せびらかす**：行為の完了と同時に、観客への印象を残す意図を示す。  
- **宝石** を「持ち物の象徴」として使うことで、富と社会的地位の提示を暗示し、語感を高揚させる。

### N5 — 彼の福祉の概念はかなり観念的だ。
_197 words, 6 bullets, 972 ms — judge: fit 2/5, acc 3/5 — The explanation uses some intermediate vocabulary and over‑generalizes the pattern, making it only partially correct for an N5 learner._

- **の** – a possessive particle that links two nouns, showing that the first noun belongs to or is related to the second. In English it’s like the apostrophe‑s: *his* in “his welfare”.  
- **は** – the topic marker that says “as for …”, putting the noun before it in the sentence. It’s a way of saying “talking about …”.  
- **かなり** – an adverb meaning “quite” or “pretty”. It works like the English adverb “quite” to strengthen the adjective that follows.  
- **〜的** – an adjective‑ending that turns a noun into a description, like “abstract” from “idea”. In English it’s similar to the suffix **‑al** in “abstract”.  
- **だ** – the plain copula, the Japanese “is/are”. It’s the same function as the English verb *to be* in a simple statement.  
- **名詞 + の + 名詞 + は + 形容詞 + だ** – a basic sentence pattern for describing a noun. The first noun (彼の福祉) is the subject, the second noun (概念) is what is being described, the particle は sets the topic, the adjective (観念的) describes it, and だ ends the sentence. This is the simplest way to say “X is Y” at N5 level.

### N1 — 彼の福祉の概念はかなり観念的だ。
_8 words, 0 bullets, 749 ms — judge: fit 5/5, acc 4/5 — 説明は概ね正確だが、かなりの用法や「的」の語源的説明がやや不明瞭で、N1学習者にとってはもう少し具体例が欲しい。_

**かなり**  
程度副詞として「かなり」で「かなり観念的だ」では程度を強調し、定量的尺度を曖昧に上位に置く語調を演出する。

**～的**  
形容詞化接尾辞として「観念的」に用い、抽象的・概念的な性質を指示。名詞を形容詞に転換し、語感を抽象度高へ向上させる。

**だ**  
終止形の断定形。名詞的な形容詞に対しても用い、文末で事実性を表し、文体を口語的な平易さに保つ。

**福祉の概念**  
名詞＋

### N5 — この岩は何に似ていますか。
_196 words, 5 bullets, 1005 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate but includes some terminology slightly above the typical N5 scope._

- **に**  
  The particle **に** marks the object of comparison or the target of an action. In this sentence, it connects 「何」 (what) to 「似ている」 (to look like). Think of it as the English “to” in “look like ___”.  

- **か**  
  The particle **か** signals a yes/no question. It is placed at the end of a sentence to turn it into a question, just like adding a question mark in English.  

- **です**  
  「です」 is a polite copula that makes a statement or a question polite. In this context it links the adjective 「似ている」 to the rest of the sentence. It’s similar to saying “is” or “are” in a polite form.  

- **何**  
  「何」 is a question word meaning “what.” It is used before a noun or verb to ask for an unspecified thing. It works like the English “what” in “What is that?”  

- **に似ている**  
  The pattern 「〜に似ている」 means “to look like” or “to resemble.” It is a verb phrase that uses the stem of a noun or adjective followed by 「に」 and the adjective 「似ている」. It’s similar to saying “looks like” in English, but it’s a single grammatical construction rather than two separate words.

### N1 — この岩は何に似ていますか。
_6 words, 3 bullets, 1034 ms — judge: fit 5/5, acc 5/5 — The explanation accurately and appropriately matches N1-level expectations, correctly detailing the grammar points and usage._

- **〜に似ている**：名詞＋に＋似ているで「～に似ているか」を疑問形にし、対象が何に類似しているかを尋ねる。  
- **何に**：疑問詞が対象を限定し、比較対象を自由に設定できる。  
- **ですか／か**：丁寧体で疑問を示し、文末の「か」だけでも口語的に終えることができる。

### N5 — この報告書は要領をえていない。
_190 words, 5 bullets, 793 ms — judge: fit 2/5, acc 2/5 — The explanation mismatches the sentence (both the verb and its meaning are incorrect) and uses terminology beyond N5, so it is poorly suited and inaccurate._

- **ている** – A verb ending that shows an ongoing action or a current state. Think of it like the English “-ing” (e.g., *running, studying*). In Japanese, it also indicates a result that is still true, like *“I have finished”* → *終わっている*.

- **ない** – The negative suffix that turns a verb into “not …”. It is the same as saying “do not” in English. It directly negates the meaning that follows: *取っている* → *取っていない* means “not taking/has not taken”.

- **は** – A particle that marks the topic of the sentence, the thing we are talking about. It’s similar to saying “as for” in English. In *この報告書は…* the topic is the report.

- **を** – A particle that marks the direct object, the thing the action is done to. It’s like the object in the English sentence *I eat **an apple**.* In *要領を取っている* the object is *要領* (the “to-do list” or “plan”).

- **です** – A polite copula that works like the English “is/are.” It’s used to end sentences politely when describing a state or identity. In a beginner sentence you can often drop it, but it shows respect.

### N1 — この報告書は要領をえていない。
_12 words, 4 bullets, 499 ms_

**〜ている**  
- 現在形＋動作完了＋継続を同時に示す。ここでは「取っていない」は「取った」の否定継続形で、報告書が「要領を取る」状態を持たないことを強調する。  
- 「取る」自体は目的語を取る動詞ではなく、比喩的に「要点を掴む・把握する」意味で使われる。  
**〜を取る**  
- 受格を取る動詞構造。報告書に対して「要領を取る」は「要点を取る」＝「要点を掴む」を意味し、文章の焦点が欠けることを示す。  
**否定の ている形**  
- 付加的に「ない」を付けて「取っていない」とすることで、状態の欠如を現在進行形で表し、単なる過去の未達ではなく現在継続していない点を強調する。

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_216 words, 6 bullets, 681 ms — judge: fit 2/5, acc 4/5 — The explanation is mostly correct but includes advanced grammar (であろう) and some slight nuance errors, making it a bit too high for N5._

- **〜ている** – This pattern shows a state that started in the past and continues now. It’s like the English present continuous, but it can also mean “currently in a situation.” In the sentence, **住んでいる** tells us the polar bear is *currently* living on the ice.

- **〜のだ** – A little “explanatory” form that adds background or explanation. Think of it as “the reason is that” or “you see.” Here **のだ** gives a reason for why the polar bear lives in the ice, adding a factual tone.

- **〜が** – The particle “but” that introduces a contrast or a new point. In Japanese, **が** is the same particle used for “subject” in simple sentences, but here it acts like English “however.” It links the fact of living to the problem of losing habitat.

- **〜であろう** – A future‑probability ending that means “probably will.” It’s similar to the English “will probably.” This pattern tells the reader that the polar bear *might* go extinct.

- **〜のだが** – When combined, this pair gives a “the fact is … but” sense. It’s a useful way to express cause and effect or contrast in simple sentences.

- **〜に** – A location particle meaning “in” or “at.” In **氷原に住んでいる**, **に** marks where the polar bear lives, like “living *in* the ice field.”

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_16 words, 4 bullets, 522 ms — judge: fit 5/5, acc 5/5 — 説明は語尾の機能とN1レベルでの適切さを正確に捉えており、簡潔かつ的確です_

- **〜ている** → 進行・状態の継続を示し、事実を客観的に述べる。  
- **〜のだが** → 事実提示＋逆接。前述の事実に対し、後ろの事実が対照的であることを強調。  
- **〜であろう** → 未来予測・推量の高度表現。確信度は低く、推量の程度を示す語尾としては最も上位。  
- **〜るであろう** の「であろう」＋動詞連用形の組み合わせは、正式文体での推量を示す。  

これらの語尾は、N1レベルの文脈で客観性と推測を組み合わせた表現として最適。


## gemini-3.5-flash-lite (gemini)

### N5 — もう３ページ残っている。
_113 words, 4 bullets, 8583 ms — judge: fit 4/5, acc 5/5 — The explanation is accurate but uses slightly advanced meta‑linguistic terms for an N5 learner._

* **〜ている** → Add this to the "te-form" (a verb change used to connect actions) to show an action happening right now, or a state that keeps going. It is a lot like adding "-ing" to an English verb.
* **もう** → An adverb (a word that describes a verb) meaning "already" or "yet," used here to talk about what is left over.
* **３ページ** → The number three combined with a counter (a special word used for counting things, like "sheets" of paper) for flat objects like pages.
* **残っている** → The verb "to remain or be left over" ending in **〜ている**, meaning the state of having pages left over right now.

### N1 — もう３ページ残っている。
_51 words, 2 bullets, 1429 ms — judge: fit 4/5, acc 4/5 — Explanation is mostly correct and suitably advanced for N1, but the phrasing is slightly overly technical and could be clearer._

- **〜て残る**: Expresses a static, residual state persisting as a result of a prior subtractive process, focusing on the objective quantity that remains rather than the ongoing action of leaving.
- **数量 ＋ 残っている**: Functions adverbial-nominally to frame the remaining quantum as an autonomous subject existing independently of the agent's intent.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_100 words, 4 bullets, 1898 ms — judge: fit 4/5, acc 2/5 — Explanation misidentifies に as a direction marker and oversimplifies the usage of と一緒に, though the overall level is roughly appropriate for N5._

* **〜と (noun connector)** — a particle (a small word marking the noun's role) that means "and," used to connect two nouns equally like "salad and rolls."
* **〜と一緒に (together with)** — a phrase meaning "together with" or "along with," which adds someone or something to an action.
* **〜に (direction marker)** — a particle showing the target or place connected to the action, used here right before "together with."
* **〜た (past tense)** — an ending attached to verbs (action words) that changes the time to the past, similar to adding "-ed" in English to turn "eat" into "ate."

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_17 words, 1 bullets, 1535 ms — judge: fit 5/5, acc 5/5 — The explanation correctly describes the usage of ～と一緒に and is appropriately detailed for an N1 learner._

* **〜と一緒に** → Denotes accompaniment with animate or inanimate entities; stylistically neutral, marking standard synchronous spatial coexistence.

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_103 words, 4 bullets, 1721 ms — judge: fit 4/5, acc 5/5 — The explanation is mostly appropriate for N5, though some terminology could be simplified further._

* **〜て** (connecting form — changing the end of a verb so you can keep talking) connects multiple actions in a row, much like saying "do this, *and then* do that" in English.
* **で** (particle — a small word showing how or where something happens) marks the tool or instrument you use to do an action, similar to the English word "with."
* **へ** (particle showing direction) points to the exact destination or place where something is going, very similar to the English word "to."
* **〜てください** (request pattern) politely tells someone to do something, matching phrases like "please do" in English.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_36 words, 2 bullets, 1715 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N1-level expectations and accurately describes the use of て and てください in procedural instructions._

- **〜て** → Connects sequential, non-simultaneous actions in procedural or instructional contexts, maintaining tense across clauses.
- **〜てください** → Polite imperative expressing direct instructions; softens the command in manual or instructional registers compared to plain imperatives.

### N5 — 関税申告書が必要になります。
_146 words, 5 bullets, 2078 ms — judge: fit 4/5, acc 2/5 — Explanation contains several inaccuracies (e.g., misuse of くなります) and oversimplifies particles, making it only partially suitable for N5._

* **〜が** (marker for the subject — a small word showing who or what does the action, or what exists) attaches to nouns like 関税申告書 (customs declaration) to show it is the main topic doing the needing here.
* **〜に** (target marker — a small word showing direction, time, or a goal) attaches to nouns to show a change into a new state, much like saying "into" or "to" in English.
* **なる** (verb — an action word) means "to become," showing that a situation is changing from one state to another.
* **〜ます** (polite ending) attaches to the end of verbs to make your speech polite when talking to people you don't know well, similar to putting "please" or using formal language in English.
* **〜くなります** (verb changing state politely) combines an adjective meaning "necessary" with becoming and politeness, transforming "need" into "will become necessary."

### N1 — 関税申告書が必要になります。
_31 words, 1 bullets, 1376 ms — judge: fit 3/5, acc 2/5 — The explanation mischaracterizes になります as honorific; it is simply a polite copula indicating a change of state, not a softening device._

* **〜になります**: Honorific/polite softening device functioning as a copula substitute; shifts the interpersonal register from direct assertion to indirect, polite framing by nominalizing the outcome as an objective transition of state.

### N5 — この本には美しい挿絵が入っている。
_157 words, 4 bullets, 2185 ms — judge: fit 3/5, acc 2/5 — The explanation contains several inaccuracies (e.g., misidentifying 挿絵 as the direct object and the role of を) and uses terminology slightly above N5 level._

* **〜には** (ni wa) → A particle (a small word marking the noun's role) combination. に shows the location or place, and は highlights it as the topic. It means "in/on this [thing], as for it."
* **美しい** (utsukushii) → An "i-adjective" (a describing word ending with the sound *i*) that goes directly in front of a noun to describe it, meaning "beautiful."
* **挿絵** (sashie) → A noun (a naming word) meaning "illustration" or "picture." This acts as the direct object of the sentence, marked by the object marker を (wo)—though here, the marker is hidden because the focus is on existence.
* **入っている** (haitte iru) → The core verb structure, made of the "te-form" (a connecting form used to link actions or states) of 入る (to enter/go in) plus いる (to exist for living things, or to continue). Just like English "is containing" or "has entered," this describes a current state that continues right now.

### N1 — この本には美しい挿絵が入っている。
_51 words, 2 bullets, 14431 ms — judge: fit 5/5, acc 5/5 — The explanation correctly captures the static state meaning of ている in 入っている and is suitably detailed for an N1 learner._

- **〜ている (state continuation / permanent state)**: Unlike standard action-result states, here it marks a static, inherent property or composition of an inanimate object rather than a temporal condition.
- **〜ている (literary/descriptive register)**: Functions as a non-volitional descriptive predicate common in expository prose, framing an objective existing state without subject agency.

### N5 — 彼女は宝石を得意げに見せびらかした。
_107 words, 3 bullets, 10949 ms — judge: fit 2/5, acc 3/5 — The particle explanations are correct but the sentence contains intermediate vocabulary and grammar not covered, making it mismatched for N5._

* **は** → a topic marker particle (a small word attached after a noun to show it is the main topic). It points directly to the person or thing you are talking about.
* **を** → a direct object marker particle (a small word showing who or what receives the action of the verb). It connects the action word to the thing being acted upon.
* **Past tense verbs** → changing the ending of an action word to talk about the past. Just like adding "-ed" to an English verb like "show" to make "showed," Japanese verbs change their ending sounds to show the action happened already.

### N1 — 彼女は宝石を得意げに見せびらかした。
_35 words, 1 bullets, 12693 ms — judge: fit 5/5, acc 5/5 — The explanation accurately describes the function and usage of the 〜げ suffix at an N1‑appropriate level._

* **〜げ**: Forms an adjectival noun indicating subjective impression or outward appearance of an internal mental state, restricted primarily to emotion-denoting roots (e.g., 得意, 残念, 不安) and used attributively or predicatively with a literary tone.

### N5 — 彼の福祉の概念はかなり観念的だ。
_114 words, 4 bullets, 12842 ms — judge: fit 3/5, acc 4/5 — The explanation is mostly correct but includes vocabulary and nuance beyond N5 and a slight mischaracterization of だ._

* **〜の** (noun connector) — a particle (a small word marking the noun's role) that connects two nouns, similar to the apostrophe-s ('s) in English to show that the first noun describes the second.
* **は** (topic marker) — a particle that points out the main topic you are talking about, sitting right after the thing you want to introduce.
* **かなり** (degree adverb) — a word placed before adjectives or other adverbs to mean "fairly" or "pretty," showing a medium-high level of something.
* **だ** (plain copula) — a polite-dropping verb equivalent to "is" or "am," used at the end of a sentence to state that a noun or adjective describes the topic.

### N1 — 彼の福祉の概念はかなり観念的だ。
_49 words, 3 bullets, 17822 ms — judge: fit 5/5, acc 4/5 — The explanation is appropriately advanced for N1, though the nuance of かなり as merely a notable deviation is slightly overstated._

* **〜の概念**: Compound nominalization emphasizing a theoretical, systemic framework rather than a concrete idea (観念).
* **かなり**: Degree adverb implying a notable deviation from the norm, distinct from purely objective measurement.
* **観念的**: Sino-Japanese compound denoting abstract, speculative, or ungrounded ideation, often carrying a critical undertone regarding practical applicability.

### N5 — この岩は何に似ていますか。
_155 words, 6 bullets, 11878 ms — judge: fit 4/5, acc 4/5 — The explanation is mostly appropriate for N5 but misstates the role of ます and could simplify some terminology._

* **〜に (ni)** → a particle (a small word attached to a noun to show its role) marking the target of a similarity, just like "to" or "like" in English.
* **何 (nani)** → a question word meaning "what," placed right before the particle **に** to ask "to what."
* **似る (niru)** → a verb meaning "to resemble" or "to look like," changing its form to connect with the helper verb below.
* **〜ている (te iru)** → a pattern combining a verb's "-te" form (a connecting form) with **いる** ("to exist") to show an ongoing state, much like "-ing" in English ("resembling").
* **〜ます (masu)** → a polite ending attached to verbs to make your speech polite and respectful, similar to using "is" instead of "be."
* **か (ka)** → a sentence-ending particle placed at the very end of a sentence to turn it into a question, acting just like a question mark in English.

### N1 — この岩は何に似ていますか。
_37 words, 2 bullets, 4269 ms — judge: fit 4/5, acc 4/5 — Explanation is mostly correct and uses appropriate terminology, but could be slightly deeper for N1 proficiency._

- **〜に（助詞）**: Marks the target of resemblance or psychological orientation with verbs like 似る, indicating the recipient of the likeness.
- **何（代名詞） + に（助詞）**: Interrogative adverbial phrase functioning as an oblique complement specifying the parameter of comparison.

### N5 — この報告書は要領をえていない。
_128 words, 5 bullets, 1945 ms — judge: fit 3/5, acc 2/5 — The explanation contains several particle and grammar errors, making it inaccurate for the given sentence._

- **〜は** → topic marker, a small word marking what the sentence is about, used here to point to the report as the main subject.
- **〜の** → possessive particle, a small word showing ownership, connecting "this" and "report" into a single phrase.
- **〜を** → object marker, a small word marking the exact thing that the verb acts upon.
- **〜ていない** → negative continuous form, meaning "is not doing" right now, made by changing a verb to its "-te" form (a connecting form used to link actions) and adding "not being". This is very similar to the English "is not hitting the mark."
- **Kanji (漢字)** → Chinese characters used in writing, seen here in words like 報告書 (hōkokusho / report) and 要領 (yōryō / the point).

### N1 — この報告書は要領をえていない。
_59 words, 2 bullets, 1561 ms — judge: fit 4/5, acc 2/5 — The explanation misidentifies the verb form and misstates the idiom, giving an inaccurate analysis of the sentence._

* **〜をえない** → Negative potential form of *eru* (得る), lexicalized to mean "incapable of grasping the essence" or "lacking coherence," restricted primarily to intellectual comprehension and discourse analysis.
* **要領を得ない** → Fixed idiom functioning as a single predicate; replacing *eru* with other verbs or modifying the direct object destroys the idiomatic cohesion and shifts the semantics to literal acquisition.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_156 words, 5 bullets, 1987 ms — judge: fit 2/5, acc 4/5 — The explanation is mostly correct but uses grammar like であろう that is too advanced for an N5 learner._

* **〜ている** (te-iru) → Add this to an action verb to show someone is doing it right now, just like adding "-ing" in English. Here, it means "is living."
* **〜のだが** (no da ga) → A connective piece attached to the end of a clause to add context or a background fact before stating the main point, similar to saying "although" or "given that."
* **〜を** (o) → The object marker (a small word marking the noun's role), showing the target of an action. It tells us what receives the verb's action, marking "habitat" as what is being lost.
* **〜する** (suru) → A common action verb meaning "to do," which also turns many nouns or base verb forms into full actions, like "to die out" (**絶滅する**).
* **〜であろう** (de aruō) → A formal, polite way to express a guess or prediction about the future, similar to saying "probably will" or "is likely to" in English.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_67 words, 3 bullets, 1753 ms — judge: fit 5/5, acc 5/5 — The explanation accurately captures the nuances of ている, のだ, and であろう appropriate for an N1 learner._

- **〜ている** → Indicates an inherent ecological characteristic or generalized state rather than a continuous action, framing the predicate as a timeless biological fact.
- **〜のだ/んだ** → Functions in explanatory discourse to ground a proposition in shared context or objective reality before shifting to a subjective prediction.
- **〜であろう** → Epistemic modal expressing formal, high-probability conjecture in written or literary discourse, distinct from conversational supposition like *だろう*.


## gemma-4-31b-it (gemini)

### N5 — もう３ページ残っている。
_96 words, 4 bullets, 67873 ms — judge: fit 4/5, acc 5/5 — Explanation is mostly correct and appropriate for N5, though the note on omitted が may be slightly nuanced for beginners._

* **もう** $\rightarrow$ used here to mean "more" or "additional" when talking about a remaining amount.
* **Number + Counter** $\rightarrow$ in Japanese, you must use a counter (a specific word used to count certain objects) immediately after the number.
* **〜ている** $\rightarrow$ added to a verb to show a state that is currently true. This is similar to the English "-ing" form, like saying something "is remaining."
* **Omitted Particle** $\rightarrow$ a particle (a small word marking the noun's role) like が is often left out in casual speech when the meaning is already clear.

### N1 — もう３ページ残っている。
**ERROR** `empty`

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
**ERROR** `RuntimeError: Gemini request failed across retries`

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
**ERROR** `empty`

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
**ERROR** `empty`

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
**ERROR** `empty`

### N5 — 関税申告書が必要になります。
_84 words, 4 bullets, 111851 ms — judge: fit 4/5, acc 3/5 — The explanation covers basic particles but oversimplifies に and misses the typical 「～が必要になる」 pattern, making it only partially accurate for N5._

* **が** → a particle (a small word marking the noun's role) that identifies the subject of the sentence.
* **必要** → a word describing a state of being. Here, it represents the condition of being "necessary."
* **に** → a particle used here to point toward the result of a change.
* **なります** → the polite form of the verb "to become." Together with に, it describes a transition into a new state, similar to saying "will become" or "will be" in English.

### N1 — 関税申告書が必要になります。
**ERROR** `empty`

### N5 — この本には美しい挿絵が入っている。
_80 words, 4 bullets, 49253 ms — judge: fit 4/5, acc 4/5 — The explanation covers most basic elements but could better clarify the specific role of 入っている and simplify the particle descriptions for N5._

* **〜に** → A particle (a small word marking a noun's role) that shows the location of something.
* **〜は** → A particle that marks the topic, letting the listener know what the sentence is about.
* **〜い (adjectives)** → Describing words that come directly before the noun they describe.
* **〜ている** → A verb form used to describe a current state or result. It is similar to the English "-ing" form when describing a situation that is currently true.

### N1 — この本には美しい挿絵が入っている。
**ERROR** `empty`

### N5 — 彼女は宝石を得意げに見せびらかした。
**ERROR** `empty`

### N1 — 彼女は宝石を得意げに見せびらかした。
**ERROR** `empty`

### N5 — 彼の福祉の概念はかなり観念的だ。
**ERROR** `RuntimeError: Gemini request failed across retries`

### N1 — 彼の福祉の概念はかなり観念的だ。
**ERROR** `empty`

### N5 — この岩は何に似ていますか。
_75 words, 4 bullets, 61204 ms — judge: fit 4/5, acc 2/5 — Explanation misses key points (は, 似て, います) and misdescribes particles, so it’s only partly suitable for N5 and not fully accurate._

* **この** → Used before a noun to point to something close to the speaker.
* **に** → A particle (a small word marking the noun's role) that identifies the thing being compared.
* **〜ている** → A verb ending that describes a current state. It is similar to using "-ing" in English to show something is ongoing.
* **か** → A particle placed at the end of a sentence to turn it into a question.

### N1 — この岩は何に似ていますか。
**ERROR** `empty`

### N5 — この報告書は要領をえていない。
**ERROR** `empty`

### N1 — この報告書は要領をえていない。
**ERROR** `empty`

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_94 words, 4 bullets, 31484 ms — judge: fit 2/5, acc 2/5 — The explanation uses concepts (like であろう and verb‑stem linking) that are beyond N5 and misdescribes parts of the sentence._

* **〜ている** → Shows an ongoing state or action. It is similar to adding "-ing" in English to describe something currently happening.
* **〜のだが** → A combination of particles (small words that connect ideas) used to give background information before introducing the main point.
* **Verb Stem (connecting)** → The base of a verb (the part before *masu*). Using the stem instead of a full ending lets you link two actions together like a comma.
* **〜であろう** → A formal way to express a guess or a prediction about the future, meaning "probably will."

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
**ERROR** `empty`


## command-a-plus-05-2026 (cohere)

### N5 — もう３ページ残っている。
_144 words, 5 bullets, 3356 ms — judge: fit 4/5, acc 4/5 — The explanation is mostly appropriate for N5 and largely correct, though the nuance of もう could be clarified and the period isn’t a particle._

- **もう** – an adverb that shows something is still left or remaining; it works like “still” or “more” in English when you talk about how much is left.  
- **〜ている** – the present progressive form (verb‑ing) that shows an ongoing action or state; here it tells us the pages are still “remaining” right now, similar to “are left” in English.  
- **名詞 + 残っている** – a noun followed by the verb “残っている” creates a phrase meaning “the noun is still remaining”; it’s like saying “there are X left” in English.  
- **数量 + 単位** – a number plus a counter (ページ) shows how many of something; this pattern is used to count items, just like “three pages” in English.  
- **文末の「。」** – the sentence ends with the period particle, which marks the end of a statement, similar to a full stop in English.

### N1 — もう３ページ残っている。
_44 words, 2 bullets, 1293 ms — judge: fit 4/5, acc 3/5 — Explanation is fairly appropriate for N1 but slightly misinterprets もう as ‘already’ rather than ‘still/only’, missing nuance of the residual meaning._

- **もう～残っている** – emphasizes the residual quantity after prior consumption; “already” + “remaining” conveys “only X left.”  
- The structure attaches a numeral phrase to a noun and uses the progressive *残っている* to stress current state, often with a sense of urgency or completion.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_123 words, 5 bullets, 2917 ms — judge: fit 5/5, acc 4/5 — The explanation is clear and appropriate for N5, but it mislabels は as the subject and oversimplifies the second と, which is part of the phrase と一緒に rather than another simple “and.”_

- **は** – topic marker. It shows the subject of the sentence. In English, it’s like “He” at the start of a sentence.  
- **と** – “and” for listing items. It connects “サラダ” (salad) and “ロールパン” (rolls) the same way we might say “salad and rolls.”  
- **一緒に** – adverb meaning “together with.” It tells us the chicken was eaten at the same time as the salad and rolls, similar to “along with” in English.  
- **を** – direct object marker. It points to what is being eaten: “鶏肉” (chicken). Think of it as the “object” sign before the verb.  
- **た** – past tense ending for verbs. It changes “食べる” (eat) to “食べた” (ate), just like adding “ed” to “eat” in English.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_72 words, 3 bullets, 1525 ms — judge: fit 5/5, acc 5/5 — The explanation accurately and appropriately uses N1‑level terminology to describe the functions of は, と…と一緒に, and the past verb form._

- **は** – Topic marker; foregrounds 彼 as the subject of the entire clause, allowing the rest to be comment rather than new information.  
- **と…と一緒に** – “together with”; サラダとロールパン forms a coordinated noun phrase, and 一緒に attaches to indicate simultaneous accompaniment of the main action.  
- **V+た** – Past transitive completion; 食べた marks a completed act of eating, with 鶏肉 as the direct object, and the preceding with-phrase as an adjunct.

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_162 words, 5 bullets, 2415 ms — judge: fit 4/5, acc 4/5 — The explanation is mostly clear and appropriate for N5, though a few terms are slightly beyond the basic level and the particle usage could be refined._

- **〜を外す** – “to remove something.” The verb “外す” means to take off or detach, and the particle **を** marks the object being removed. Think of it like “take the lid off” in English.

- **〜で吸い上げる** – “to draw up something using a tool.” The verb “吸い上げる” means to pull liquid up, and **で** shows the instrument used, similar to “with a dropper” or “using a spoon.”

- **〜へ滴下する** – “to drip something onto something.” The verb “滴下する” means to let liquid fall in drops, **へ** points to the destination, like “onto the marker’s core” in English.

- **〜し、〜、そして〜** – “and then do several actions in order.” This pattern links a series of verbs (removing, drawing, dripping) without a subject, just like saying “remove the cap, fill the dropper, and then drip the ink.”

- **〜適量** – “an appropriate amount.” This is a noun phrase that modifies the verb, telling how much should be dripped, similar to “the right amount” in English.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_57 words, 3 bullets, 2662 ms — judge: fit 5/5, acc 5/5 — The explanation correctly uses advanced grammatical terms appropriate for N1 and accurately describes each construction in the sentence._

- **〜の…を外す**: modifies a noun phrase indicating the object being removed; here, *インキ補充瓶のキャップ* “the cap of the ink refill bottle.”
- **〜で…を吸い上げる**: instrumental particle indicating the tool used for the action; *スポイトでインキを吸い上げ* “draw ink up with a dropper.”
- **〜へ…を滴下する/してください**: destination particle marking where the action is directed; *マーカーの吸収体へ適量を滴下してください* “drip an appropriate amount onto the marker’s core.”

### N5 — 関税申告書が必要になります。
_157 words, 5 bullets, 3558 ms — judge: fit 4/5, acc 3/5 — The explanation covers the basics but mixes up the polite ending and over‑explains the になります pattern for an N5 learner._

- **～が必要** – “～ is necessary.” This is a simple pattern where a noun (関税申告書) followed by the particle **が** and the word **必要** (noun meaning “necessity”) shows that something is required. Think of it like “A is needed” in English.  

- **～になります** – “～ becomes.” This pattern uses a noun or adjective before **に** and **なり** + **ます** to show a change into a new state. In our sentence, 必要 (necessary) changes to “necessary” for the customs declaration. It’s similar to “it becomes necessary.”  

- **～が** – particle indicating the subject of a sentence. In “関税申告書が…,” the customs declaration is the thing that is becoming required.  

- **です** – polite ending particle that makes the statement polite and complete. It follows the whole phrase after the verb pattern.  

- Comparison: “A is required” (English) corresponds to **～が必要になります** (Japanese), where the noun + **が** + **必要** + **になります** shows the same meaning in a polite, step‑by‑step way.

### N1 — 関税申告書が必要になります。
_37 words, 2 bullets, 2159 ms — judge: fit 5/5, acc 5/5 — Explanation correctly describes the grammar and is appropriate for an N1 learner._

- **必要になります**: resultative construction; noun + になります marks the onset of a required state, often used in formal notices.  
- **が**: subject particle linking the preceding noun to the predicate, here emphasizing the item that becomes required.

### N5 — この本には美しい挿絵が入っている。
_138 words, 5 bullets, 3994 ms — judge: fit 4/5, acc 4/5 — The explanation is largely correct and appropriate for N5, though it slightly over‑explains the role of は and could be simpler._

- **〜には** – The particle **には** shows where something exists or is included. In “この本に” it means “in this book.” Think of it like “in this book” in English.
- **は** – The topic marker **は** tells us what the sentence is about. After “本” it signals “the book” is the subject we’re talking about.
- **美しい** – An adjective that directly modifies the noun that follows, just like “beautiful” before “illustrations” in English.
- **〜が入っている** – The verb “入る” (to enter, to be included) with **〜ている** shows a continuous state, meaning “are included” or “are present.” It’s similar to saying “has … inside” in English.
- **が入っている** – The **が** is the subject marker inside the verb phrase, linking the noun “挿絵” (illustrations) to the verb “入っている.” It works like “the illustrations” in “the illustrations are included.”

### N1 — この本には美しい挿絵が入っている。
_49 words, 2 bullets, 2147 ms — judge: fit 5/5, acc 5/5 — The explanation correctly matches N1 expectations and accurately describes the grammar of には…が入っている and the 美しい＋名詞 attributive construction._

- **には...が入っている**: subject‑location marker *には* marks the location or container; the verb phrase *が入っている* denotes inclusion or presence, often omitted in translation as “contains” or “has”.  
- **形容詞＋名詞**: pre‑nominal adjective *美しい* directly modifies noun *挿絵* without a linking verb, a standard attributive construction indicating a property of the noun.

### N5 — 彼女は宝石を得意げに見せびらかした。
_155 words, 5 bullets, 3480 ms — judge: fit 2/5, acc 1/5 — The explanation contains several factual errors (misplaced を, incorrect te‑form claim) and uses vocabulary beyond typical N5 level._

- **は (topic marker)** – Shows the subject of the sentence. It works like “She” in English, but it tells the listener what the sentence is about before giving the verb.  
- **を得意げに** – A compound adverb meaning “proudly.” It combines the noun “得意” (good at) with the particle “に” to make a feeling-based manner. Think of it as “with pride” in English.  
- **見せびらかした** – Past tense of the verb “見せびらかす” (to show off). The “〜た” ending means the action is already done, similar to English “displayed.”  
- **を (object particle)** – Marks the direct object of the verb. Here it tells us that “宝石” (jewels) is what is being shown off, just like “her jewels” in English.  
- **て形 (te-form)** – A verb form used to connect actions or show continuation. In “見せびらかした,” the te-form “見せて” links the idea of showing to the overall action, comparable to “showing off” before the final result.

### N1 — 彼女は宝石を得意げに見せびらかした。
_58 words, 2 bullets, 2585 ms — judge: fit 5/5, acc 5/5 — The explanation accurately and appropriately details the nuance of 得意げに and the colloquial, ostentatious sense of 見せびらかす for an N1 learner._

- **得意げに**: suffix *げ* attaches to *得意* to form an adverbial phrase indicating a self‑satisfied, showy manner; it conveys arrogance or pride in the speaker's action, often with a negative connotation.  
- **見せびらかした**: past tense of *見せびらかす* (verb *見せる* + *びらかす*), a colloquial, slightly vulgar pattern meaning “to display ostentatiously”; it emphasizes deliberate flaunting rather than simple showing.

### N5 — 彼の福祉の概念はかなり観念的だ。
_105 words, 5 bullets, 4733 ms — judge: fit 3/5, acc 5/5 — The explanation is correct but includes terminology (e.g., “na‑adjective”) that is a bit advanced for an N5 learner._

- **の（possessive particle）** – attaches to a noun to show it belongs to something; e.g., “福祉の概念” = “concept of welfare.”  
- **は（topic marker）** – puts the preceding noun at the start of the sentence as the topic; e.g., “彼の…は” = “His … is.”  
- **かなり（adverb）** – adds the meaning “pretty” or “quite” before an adjective; it works like “pretty abstract” in English.  
- **観念的だ（na‑adjective + copula）** – a na‑adjective (“観念的”) ends the predicate with the copula “だ,” similar to “is abstract” in English.  
- **だ（copula）** – a simple linking verb that connects the subject to the adjective; it is the basic “is/are” for non‑verb predicates.

### N1 — 彼の福祉の概念はかなり観念的だ。
_61 words, 4 bullets, 3072 ms — judge: fit 5/5, acc 5/5 — The explanation correctly and appropriately covers each grammatical point for an N1 learner._

- **の**: Links a noun to its modifier, forming a compound noun; here it makes 「福祉」 modify 「概念」.  
- **は**: Marks the topic of the sentence, indicating what the comment 「かなり観念的だ」 applies to.  
- **かなり**: Degree adverb intensifying the predicate, indicating a notable level of abstraction.  
- **だ**: Copula attaching to the adjectival noun 「観念的」 to predicate it about the topic.

### N5 — この岩は何に似ていますか。
_136 words, 5 bullets, 2730 ms — judge: fit 5/5, acc 5/5 — The explanation is clear, appropriately simple for N5, and accurately describes each element of the sentence._

- **この** – demonstrative word meaning “this.” It points to something near the speaker, like “this rock” in English.  
- **は** – topic marker particle (particle = a small word that shows the role of the noun). It tells us the subject of the sentence is “this rock.”  
- **何に** – question word “what” + particle “に” that shows the object of similarity. It asks “what” the rock looks like, similar to asking “What does it look like?” in English.  
- **似ています** – present continuous form of the verb “似る” (to resemble). It means “looks like” or “is similar to,” and works like “is looking like” in English when you describe appearance.  
- **か** – sentence-ending particle that makes the whole sentence a question, just like adding a “?” at the end of an English question.

### N1 — この岩は何に似ていますか。
_62 words, 2 bullets, 2734 ms — judge: fit 4/5, acc 2/5 — The explanation contains several inaccuracies about the 似ている construction and the question pattern, making it only partly suitable for an N1 learner._

- **～は何に～ていますか** – interrogative construction placing the question word *何に* before a simile verb to ask for a comparison target; the copula *です* attaches to the predicate, and the question particle *か* finalizes the inquiry.  
- **～に似ています** – simile construction using the auxiliary verb *います* (present progressive) to indicate a visual resemblance; the preceding noun functions as the subject of the simile.

### N5 — この報告書は要領をえていない。
_155 words, 5 bullets, 4445 ms — judge: fit 3/5, acc 2/5 — The explanation contains several inaccuracies (e.g., misdescribing を and the verb 得る) and the sentence itself is missing the correct spelling of 得ていない, making it only partially suitable for an N5 learner._

- **〜は** – the particle は marks what the sentence is about (topic). Think of it like “As for this report…”.  
- **〜を** – the particle を shows the direct object of the verb, similar to “(something) in English” when you say “I read a book.” Here it marks “要領” as what is being gotten.  
- **〜ていない** – this is the negative form of the present progressive (something is not happening). It works like “is not …ing” in English; for example, “I am not eating” becomes 食べていない.  
- **〜ている** (present progressive) – when you add て to a verb stem, it means the action is ongoing. In our sentence the verb is “to get” (得る), and ていない tells us “is not getting.”  
- **〜ない（negative)** – adding ない after a verb or adjective makes it negative, comparable to “not …” in English. In えていない, the ない part gives the “not” meaning to the whole progressive form.

### N1 — この報告書は要領をえていない。
_66 words, 3 bullets, 2461 ms — judge: fit 5/5, acc 4/5 — Explanation is generally appropriate for N1 but misstates the verb spelling and oversimplifies nuances of 要領を得ていない._

- **要領をえていない**: negative present progressive of *える* “to obtain,” indicating a lack of acquisition; used with abstract nouns to denote failure to grasp an essence.  
- **は** topicalizer marking the report as the specific entity being evaluated, implying a contrast with other possible reports.  
- The construction *XはYをえていない* functions as a formal, objective critique, often in written or official contexts, conveying a nuanced judgment of incompleteness.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_161 words, 5 bullets, 4698 ms — judge: fit 2/5, acc 3/5 — The explanation uses many advanced terms and forms beyond N5 and contains minor inaccuracies about the grammar points._

- **〜は...に住んでいる** – This shows a subject living in a place. 「北極熊は極地の氷原に住んでいる」 means “The polar bear lives on the polar ice‑cap.” It works like “The cat lives in the house.”

- **のだが** – A connector that adds a reason or contrast after a statement. It is like “but” or “however.” Here it links the fact about the bear’s home to the result that follows.

- **生息地を失い** – The verb 「失う」（lose) is changed to 「失い」 to show an action happening now or as a result. It’s similar to “loses its home” in English, but the form 「〜i」 tells us it’s a non‑past, non‑questioning action.

- **絶滅するであろう** – 「であろう」 is a helper that shows a guess or prediction about the future. 「絶滅する」 means “to become extinct.” Together they mean “will probably die out,” like “will likely become extinct.”

- **〜ていない/ている** – In 「住んでいる」, the 「いて」 part is the present progressive form, meaning the action is ongoing. It’s like “is living” rather than “lived.”

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_60 words, 3 bullets, 1604 ms — judge: fit 5/5, acc 3/5 — Explanation is appropriate for N1 but lacks some nuance, especially regarding the formal register of 「であろう」 and the precise function of 「のだが」 as a contrastive connective._

- **〜ている** in 「住んでいる」: present progressive, indicating ongoing state; with 「のだが」 it introduces a concessive clause that contrasts with the subsequent result.
- **〜のだが** as a concessive connective: links the premise clause to the consequence, often used in formal or literary registers.
- **〜だろう** in 「絶滅するであろう」: modal suffix expressing future prediction based on present evidence, with a degree of certainty.
