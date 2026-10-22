# LLM comparison — grammar explanations

## Format adherence (level-aware prompts)

| model | level | n | bullets ok | words ok | bolded | leaks | errors | avg ms |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1186 |
| openai/gpt-oss-120b | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 1984 |
| openai/gpt-oss-20b | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 917 |
| openai/gpt-oss-20b | N5 | 10 | 10/10 | 9/10 | 10/10 | 0 | 0 | 743 |
| qwen/qwen3.8-27b | N1 | 10 | 7/8 | 8/8 | 8/8 | 0 | 2 | 15072 |
| qwen/qwen3.8-27b | N5 | 10 | 6/7 | 7/7 | 7/7 | 0 | 3 | 42593 |
| command-a-plus-05-2026 | N1 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 2109 |
| command-a-plus-05-2026 | N5 | 10 | 10/10 | 10/10 | 10/10 | 0 | 0 | 3126 |

## openai/gpt-oss-120b (groq)

### N5 — もう３ページ残っている。
_133 words, 5 bullets, 1487 ms_

- **もう** – used to show something that remains or has already happened; similar to English “already” or “still” when you talk about what’s left.  
- **～ている** – attaches to a verb stem to describe a continuing state or result of an action; like “is/are …‑ing” in English, but it can also mean “has … left.”  
- **残る** (verb) + **ている** → **残っている** – the verb “to remain” combined with **～ている** expresses “is remaining” or “there are still … left.” Think of it like “is remaining” in English.  
- **数 + 名詞** – placing a number directly before a noun (e.g., **３ページ**) counts the items; works like “three pages” in English.  
- **が** (particle) – marks the subject of a sentence, showing what has the property described; comparable to “subject‑marker” in English clauses.

### N1 — もう３ページ残っている。
_6 words, 3 bullets, 812 ms_

- **〜ている**：結果状態を表し、進行形と区別して「～が残っている」で残存量を示す。  
- **もう＋数詞＋名詞＋残っている**：残量を示す表現で、期待・焦燥感を暗示し、口語的ながら文脈次第で硬い語感を持つ。  
- **残る**の受動的用法：主体が暗示されず、客観的事実として残りを提示する際に使用。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_100 words, 5 bullets, 864 ms_

- **は** – topic particle; marks what the sentence is about, like “as for …” in English.  
- **と** – listing particle; connects nouns meaning “A and B”. It works like the English “and” when you list items.  
- **と一緒に** – “together with”; adds the idea of doing something in company with something else, similar to English “with … together”.  
- **を** – object particle; shows what the verb is acting on, comparable to the English direct‑object marker “(the)”.  
- **た** – past tense ending; turns a verb into its past form, just like adding “‑ed” to an English verb.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_13 words, 3 bullets, 820 ms_

- **～と** (列挙接続助詞) → 同格の名詞を等列化し、語順の自由度を保持しつつ、包括的に列挙する効果を持つ。  
- **～と一緒に** → 「共同行為」・「同時性」だけでなく、主語側の主体的同伴感覚を強調し、文体的に「共に」や「共鳴」のニュアンスを付加する。  
- **～を** → 他動詞の直接対象を示すが、文脈上の焦点化により、前置詞的に「主題化」された要素を際立たせ、情報の階層化を実現する。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_152 words, 6 bullets, 1139 ms_

- **の** – particle that shows possession or description, like “ink refill bottle’s cap.” Think of it as the English “’s” or “of.”
- **を** – particle that marks the direct object, the thing the action is done to. Similar to English “(something) …” after a verb, e.g., “cap **を** 外す” = “remove the cap.”
- **で** – particle indicating the means or tool used for an action. Works like “by” or “with” in English, e.g., “スポイトでインキを吸い上げ” = “suck ink **with** a dropper.”
- **へ** – particle showing direction toward a target, comparable to “to” in English. In “マーカーの吸収体へ適量滴下してください,” it points the ink toward the marker’s core.
- **て** – conjunctive form that links actions in order, similar to “and then” in English. The three verbs are connected as “外し、吸い上げ、滴下してください.”
- **ください** – polite request ending attached to the て‑form, meaning “please do ….” It turns the instruction into a courteous command.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_15 words, 3 bullets, 985 ms_

- **V‑て** (外し、吸い上げ) → 連用形で列挙し、同一主体の連続動作を示す。  
- **へ** (吸収体へ) → 方向性を示す格助詞で、目的地への到達よりも「向かう」イメージが強い。  
- **V‑てください** (滴下してください) → 丁寧命令形。依頼の柔らかさと同時に、前述の動作が完了した上での最終指示を示す。

### N5 — 関税申告書が必要になります。
_119 words, 5 bullets, 1114 ms_

- **が** – a particle that marks the thing doing the action or being described; think of it like “as for” in English.  
- **必要です** – a na‑adjective (adjectival noun) meaning “necessary”; it works like “is necessary” when you add the polite copula です.  
- **なる** – the verb “to become.” When you attach なる to an adjective or noun, it shows a change of state, similar to English “becomes.”  
- **～になります** – the polite present‑future form of なる (adding ます makes it polite). It is used like “will become” or “becomes” in a polite sentence.  
- **です** – the polite copula, a small word that makes a statement polite, comparable to adding “‑is” in a formal English sentence.

### N1 — 関税申告書が必要になります。
_4 words, 2 bullets, 1024 ms_

- **～になる**：判定形＋になるで状態の遷移を示す。ここでは「必要」という形容動詞語幹に助動詞「だ」の連体形が省略され、客観的必然性への転換を文体的に弱めつつ客観的事実化する。  
- **が**（主格）：「関税申告書」を主語化し、非人称・無生物の必然性を示す。対照的に「は」を用いると対比的焦点が付与され、ニュアンスが変化する。

### N5 — この本には美しい挿絵が入っている。
_103 words, 4 bullets, 669 ms_

- **に** – a particle that marks a location or direction; here it shows “in the book.” (similar to “in” in English)  
- **は** – a particle that makes the preceding word the topic of the sentence; it tells us what we’re talking about.  
- **が** – a particle that marks the subject, the thing that actually does or has something; think of it like “(the) … is …” in English.  
- **入っている** – the **～ている** form (verb + て + いる) expresses a continuing state; it means “is inside/has been placed.” This is like saying “is …ed” (e.g., “is written”) in English.

### N1 — この本には美しい挿絵が入っている。
_6 words, 2 bullets, 716 ms_

- **Vている** (状態・結果)：「入っている」は「入る」の継続的状態を示し、単に「入る」だけでなく「すでにそこにある」ことを強調する。  
- **N+には** (限定的指示)：「には」は「この本」という範囲を限定し、そこに限定された事実（美しい挿絵がある）を提示する。

### N5 — 彼女は宝石を得意げに見せびらかした。
_138 words, 6 bullets, 1750 ms_

- **は** – topic particle; marks what the sentence is about, like “as for …” in English.  
- **を** – object particle; shows the direct object of the verb, similar to the English “(verb) the …”.  
- **に** – adverbial particle; attaches to an adjective‑like word to indicate the manner of an action, comparable to “‑ly” in English (e.g., “proudly”).  
- **‑げ** – suffix that turns an adjective into a “‑like” feeling, meaning “seeming / appearing”. It adds the sense of “looking proud”.  
- **‑た** – past tense ending for verbs; puts the action in the past, like the English “‑ed”.  
- **見せびらかす** – a compound verb meaning “to show off”; the first part (見せ) means “to show”, and びらかす adds the nuance of flaunting.  

These points cover the main grammar pieces in the sentence without repeating it.

### N1 — 彼女は宝石を得意げに見せびらかした。
_59 words, 2 bullets, 1226 ms_

- **～げ**: attaches to adjectival stems (e.g., 得意) to form a na‑adverbial expressing the speaker’s inference of the subject’s apparent feeling; conveys nuance of “seeming” rather than confirmed state.  

- **V‑びらかす**: lexicalized compound verb meaning “to flaunt, to display ostentatiously”; the preceding verb (見せ) indicates the act being exhibited, while びらかす adds a connotation of showiness and slight provocation.

### N5 — 彼の福祉の概念はかなり観念的だ。
_97 words, 4 bullets, 1310 ms_

- **の** – a particle (small word that marks the noun’s role) used to show possession or connection, like the English “’s” in “his welfare”.  
- **は** – the topic particle that tells the listener what the sentence is about; it’s similar to saying “as for …” before the rest of the statement.  
- **だ** – the plain‑form copula, the informal version of です, used to state something directly, like “is” in English.  
- **かなり** – an adverb (a word that modifies a verb or adjective) meaning “quite” or “fairly”, used to intensify the adjective that follows.

### N1 — 彼の福祉の概念はかなり観念的だ。
_16 words, 4 bullets, 939 ms_

- **の** : 連体修飾の連体格助詞、所有・属性を示すだけでなく、抽象的概念同士の関係を示す際に硬質・学術的レジスターを付与する。  
- **は** : トピック化助詞、既知情報の提示と対比的焦点設定を同時に果たし、概念全体を議論の枠組みとして限定する機能を持つ。  
- **的** : 名詞＋的で形成される形容動詞語幹、抽象名詞を形容詞化し、客観的評価・学術的語感を付加する。  
- **だ** : 判定詞、形容動詞の終止形として硬式文体を保持し、断定的語調と客観性を強調する。

### N5 — この岩は何に似ていますか。
_84 words, 4 bullets, 817 ms_

- **は** – topic particle; marks what the sentence is about, like “as for …” in English.  
- **に** – particle that shows the target or direction of an action; here it indicates “what … looks like,” similar to “to” in “look to.”  
- **似ている** – verb 似る “to resemble” plus **ている**, which expresses a continuing state (like “is looking like”).  
- **か** – question particle; placed at the end to turn the statement into a question, comparable to adding “? ” in English.

### N1 — この岩は何に似ていますか。
_6 words, 3 bullets, 636 ms_

- **に似る**：他者との類似を示す静的比較。文脈次第で「～のように見える」より客観的評価を含む。  
- **は**：主題化で対象を限定し、質問文において情報焦点を「この岩」に置く。  
- **か**：疑問助詞。文末上昇調でない場合、礼儀的・形式的な質問として機能し、文全体を仮定的に提示する。

### N5 — この報告書は要領をえていない。
_144 words, 6 bullets, 9567 ms_

- **は** – particle that marks the topic, the thing we are talking about, similar to “as for …” in English.  
- **を** – particle that marks the direct object, the thing that receives an action, like “…the report **(object)** …”.  
- **～ている** – verb form showing a continuing state or result; think of it like the English “to be …‑ing” or “have …ed” (e.g., “is having”).  
- **～ていない** – negative of ～ている, meaning the state does **not** exist; comparable to “is not …‑ing” or “doesn't have …”.  
- **要領を得る** – set phrase where 得る (to obtain) combines with 要領 (the point/essence); the whole means “to get the point”. Using the ～ている form turns it into “has gotten the point (and continues to have it)”.  
- **要領を得ていない** – negative continuation, so it expresses “does not have the point” or “is not to the point”.

### N1 — この報告書は要領をえていない。
_70 words, 3 bullets, 2799 ms — judge: fit 5/5, acc 5/5 — The explanation uses sophisticated linguistic terminology appropriate for an N1 learner and accurately describes the resultative nuance of the phrase._

- **V‑ている** → resultative aspect; conveys a sustained state after the action of “得る” (to grasp), thus “要領を得ている” means “has the point”.  
- **V‑ている + ない** → negates the resultant state, implying the subject lacks the said condition rather than merely failing to perform the action.  
- **要領を得る** → idiomatic set phrase; using the resultative form emphasizes a qualitative assessment of the report’s completeness rather than a simple factual omission.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_127 words, 6 bullets, 1119 ms_

- **は** – particle that marks the topic (what we are talking about). Similar to “as for …” in English.  
- **に** – particle indicating location where something exists or happens. Works like “in/at” for static places.  
- **住んでいる** – verb + ている form; shows a continuing state (“is living”). Comparable to the English progressive “is living”.  
- **のだが** – combination of のだ (explanatory “you see”) and が (conjunction “but”). It adds a reasoned tone and then connects to a contrast, like “but” after an explanation.  
- **失い** – て‑form of 失う (to lose) used to link actions; functions like “and then” to show the next step.  
- **であろう** – polite conjecture form meaning “will probably”. It’s the formal guess version of だろう, similar to “will likely”.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_12 words, 4 bullets, 1900 ms_

- **住んでいる** 現在進行形の継続を示す助動詞「いる」の連用形に接続し、状態の継続や習慣的な存在を示す。文脈上は「現在もそうである」ことを強調。  
- **のだが** 「のだ」＋逆接助詞「が」の複合形。説明・根拠提示後に、予想外・対照的情報を導入する文学的・口語的逆接。  
- **失い** 連用形で接続し、後続の「絶滅するであろう」への因果関係を示す連続動作の省略形。  
- **であろう** 「である」の推量形。客観的根拠に基づく未来予測を、硬い文体で示す。


## openai/gpt-oss-20b (groq)

### N5 — もう３ページ残っている。
_164 words, 6 bullets, 833 ms_

- **〜ている** – This pattern shows an ongoing state or result of an action. It’s like the English “to be …ing” or “to have … (completed)”.  
- **残る (のこる)** – A verb that means “to remain”. When you say **残っている**, it means “is remaining” or “there are still left”.  
- **もう (もう)** – An adverb that means “already” or “more” depending on context. Here it signals that the pages left are “already” the remaining ones.  
- **３ページ** – A noun phrase “three pages”. The number comes before the counter **ページ** (pages).  
- **…がある** – Though not in the sentence, it’s useful to know that **がある** can also say “there are …” when talking about objects. In this sentence, **残っている** fills that role.  
- **～が** vs. **～を** – The particle **が** marks the subject that is doing or having the state (in this case, the pages). The particle **を** marks the direct object; here it isn’t needed because the verb “残る” doesn’t take an object.

### N1 — もう３ページ残っている。
_17 words, 4 bullets, 655 ms_

- **残る + ている**：状態動詞＋ているで「残っている」＝「残っている状態が続いている」。進行ではなく、現状が確立したことを表し、完了感を帯びる。  
- **もう + ている**：時間的余裕を示す副詞「もう」が先行し、残っている量が「もう足りない」ことを暗示。  
- **残る + ている** は「残る＋ていない」に対し、肯定的な状態を強調し、数が一定以上あるという客観的事実を提示。  
- この文では **残る＋ている** が「ページが減る過程ではなく、現在のページ数が一定以上残っている」ことを示し、読者へ「まだ多い」印象を与える。

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_199 words, 6 bullets, 699 ms_

- **〜と** – a particle that means “and” or “with” when listing things. It connects two or more nouns.  
  *English comparison:* like the word “and” in “apples **and** oranges.”

- **〜と一緒に** – a phrase meaning “together with” or “along with.”  
  It shows that the action happened together with the listed items.  
  *English comparison:* similar to saying “with” in “I went to the park **with** my friends.”

- **〜を** – a particle that marks the direct object of a verb, the thing that is acted upon.  
  It tells us what is being eaten, touched, etc.  
  *English comparison:* like the object of a verb in “I read **a book**.”

- **〜た** – the past tense ending for plain verbs. It turns an action into something that already happened.  
  *English comparison:* it’s the same role as “-ed” in “walked” or “ate.”

- **〜食べる** – the verb “to eat.”  
  The basic form that can change with tense or politeness.  
  *English comparison:* it’s the core action like “eat” in “I eat breakfast.”

- **〜です** – a polite copula meaning “is” or “are.” It is used to end a sentence politely when describing a state.  
  *English comparison:* similar to “is” in “She is a teacher.”

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_12 words, 4 bullets, 479 ms_

- **〜と**（並列）: 連体節で並列対象を列挙し、同一行為を示す。  
- **〜と一緒に**: 時間・空間的同時性＋協同行為を強調。  
- **〜を食べた**: 直接目的語を示す受動態的表現の中に並列動作を組み込む。  
- **〜と**＋**〜と**: 「と」の重複が並列関係を明示し、語順の柔軟性を利用。

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_142 words, 5 bullets, 586 ms_

- **〜を外し** – The verb **外す** means “to remove” or “to take off.”  
  Its **te‑form** (外し) links one action to the next, like “remove the cap, and then …” in English.

- **〜で** – This particle shows the *means* or *tool* used.  
  It’s similar to saying “with a dropper” or “using a dropper” in English.

- **〜吸い上げる** – The stem **吸い** + the auxiliary **上げる** forms a compound verb meaning “to suck up” or “to draw up.”  
  Think of it like “to draw up” in English; the action is completed in one phrase.

- **〜へ** – A particle that marks the *direction* of an action.  
  It’s like the English “to” in “to the marker’s core.”

- **〜してください** – An imperative form that politely asks someone to do something.  
  It’s equivalent to saying “please …” in English, but is more formal and respectful.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_12 words, 4 bullets, 489 ms_

- **〜て**（連用形連続）  
  連続した動作を順序立てて列挙し、原因と結果の関係を示す。

- **〜を**（目的語＋動作の対象）  
  「吸い上げ」「滴下」の対象を明確にし、動作の対象を限定する。

- **〜へ**（方向・移動先）  
  「適量」を「マーカーの吸収体へ」と指示し、動作の目的地を示す。

- **〜ように**（目的・結果）  
  「適量、滴下してください」で、動作の目的と所要量を設定する。

### N5 — 関税申告書が必要になります。
_162 words, 6 bullets, 842 ms_

- **が** – A particle that marks the subject of a sentence. It’s like the English word “who” or “what” when you say “The customs declaration **is** required.”  
- **です** – A polite copula that turns a noun or adjective into a statement. Think of it as “is/are” in English but with extra politeness.  
- **になる** – A verb meaning “to become” or “to turn into.” In this sentence, it shows a change from *not required* to *required*. It’s similar to saying “the customs declaration will **become** necessary.”  
- **必要** – A noun meaning “necessary.” It can be used alone, but when paired with になる it creates a phrase that says something will be needed.  
- **書** – The kanji for “paper” or “form.” Here it’s part of the compound word 申告書 (customs declaration form).  
- **関税** – The kanji for “customs duty.” Together they form the term for a customs declaration.  

These patterns combine to say “A customs declaration becomes necessary.”

### N1 — 関税申告書が必要になります。
_12 words, 4 bullets, 780 ms_

- **～になる**: 変化・結果を表し、状態の確定や必然性を示す。  
- **必要になる**: 物事が必須条件へと変わる際に使われる、受動的な必要性を表す。  
- **申告書が必要になる**: 主語が状態変化を経て「必要な状態」に転換することを示し、未来・必然性を暗示。  
- **が**: 主語を指し示し、必要性の主体を明確化することで、受動的な要請を強調する。

### N5 — この本には美しい挿絵が入っている。
_214 words, 6 bullets, 704 ms_

- **～に** – a particle that shows “in, on, or inside” something. It tells us where the action takes place. In English, it’s like saying “in this book” or “inside this book.”

- **～が** – a particle that marks the subject of a verb or adjective. Think of it as “the one that …” or simply “the … that” in English, which indicates who or what is doing the action.

- **～を** – a particle used for the direct object of a sentence, the thing that receives the action. In English, it’s often the “something” that gets acted upon, like “the picture” in “put the picture in the book.”

- **～入っている** – a verb form that uses the **～ている** pattern. This shows that an action is finished and the result remains. It’s similar to the English “is put” or “has been put.” Here, it means the illustrations have been placed inside the book and still are inside.

- **美しい** – an adjective that describes something as beautiful. In Japanese, adjectives can stand alone and act like “beautiful” in English before a noun, e.g., “beautiful book.”  

- **この本** – a noun phrase using **この** (this) + **本** (book). It’s a simple way to point out the item you’re talking about, like “this book” in English.

### N1 — この本には美しい挿絵が入っている。
_8 words, 4 bullets, 1807 ms_

- **入っている**：動詞「入る」の連体形＋現在完了形で、状態の継続性を示す。ここでは「挿絵が入っている」＝「挿絵が配置されており、その配置が現在も有効である」という意味。  
- **美しい**：形容詞の連体形で「挿絵が美しい」ことを表し、主語である「本」を修飾する形容詞連体修飾。  
- **この本には**：格助詞「に」に対して「は」で強調。ここでは「この本」への属性を指示し、読者に「本」自体に注目させる。  
- **が**：主語提示の助詞。挿絵が「この本」に「入っている」という構造を作り、挿絵を主語にして状態を述べる。

### N5 — 彼女は宝石を得意げに見せびらかした。
_282 words, 6 bullets, 919 ms_

- **～を** (object marker) – this small word shows the thing that receives the action. In the sentence, it tells us that the jewels are the object of the verb. It is similar to the English word “to” in “give to someone” when we want to show what is given, but here it is simply marking what is acted upon.

- **～た** (past tense) – the ending that turns an action into “did it”. It tells us that the showing of the jewels happened already. It works like the English past tense “displayed” or “showed”.

- **～げに** (adverbial form) – a word that describes how the action is performed. It means “with a certain feeling or manner”. Think of it as “proudly” in English. It is formed by adding the small “げ” to the verb stem and then “に” to turn it into an adverb.

- **見せびらかす** (verb) – a single verb that means “to flaunt, show off”. It is made of two parts: *見せる* “to show” and *びらかす* “to brag”. In Japanese we often combine small verbs like this to create a new meaning that is richer than each part alone, just like “to look after” in English adds “after” to “look”.

- **彼女は** (topic marker) – the particle **は** indicates who is being talked about. It sets *she* as the topic of the sentence, similar to the English “as for” or “speaking of”. The sentence is built around what she does, not who she is.

- **～した** (past form of *する*) – a helper verb that links the action to the sentence. In this context it simply confirms that the action of flaunting is finished, similar to “did” in English.

### N1 — 彼女は宝石を得意げに見せびらかした。
_10 words, 3 bullets, 661 ms_

- **得意げに**: 形容動詞＋‐げ＋接続助詞＋副詞化で、外見上自信や満足感を表す。語尾は動詞と同様に接続し、後に述語を修飾。  
- **見せびらかす**: 使役的語義を持つ自動詞＋過去形で、自己誇示の意図を強調。文末の「-した」で完了と意図を同時に示す。  
- **を**: 目的格助詞として直接目的語（宝石）を指示し、動作の対象を明確化。  

これらは語尾と助詞の細やかな意味転移で、N1レベルの微妙なニュアンスを捉える。

### N5 — 彼の福祉の概念はかなり観念的だ。
_129 words, 5 bullets, 575 ms_

- **〜の** – a particle that shows possession or description.  
  It works like “of” or the apostrophe‑s in English.  
  Example: 彼の福祉 – *his welfare*.

- **は** – a topic marker that introduces what you’re talking about.  
  Think of it as “as for” or “speaking of” in English.

- **〜かなり** – an adverb meaning “quite” or “pretty.”  
  It modifies the adjective that follows, just like “very” in English.

- **〜だ** – the plain copula used at the end of a sentence to state something as fact.  
  It’s similar to saying “is” in English, but it stays in the present plain form.

- **形容詞 + だ** – a pattern that turns an adjective into a sentence.  
  The adjective (観念的, meaning “abstract”) describes the subject, and だ links it to the topic.

### N1 — 彼の福祉の概念はかなり観念的だ。
_12 words, 4 bullets, 691 ms_

- **の**: 所有格・連体修飾で「彼の福祉の概念」＝「彼が持つ福祉に関する概念」  
- **かなり**: 範囲副詞で「かなり観念的だ」の程度を強調し、客観的評価を示す  
- **観念的だ**: 連体形＋判定詞で抽象性を語り、名詞的形容詞が名詞の直前で形容する  
- **だ**: 判定語で終止形をとり、文末で肯定的結論を提示する

### N5 — この岩は何に似ていますか。
_132 words, 6 bullets, 542 ms_

- **この** – a demonstrative adjective that means “this” and points to the noun that follows.  
- **は** – a topic particle that says “as for this rock, …”. In English it’s similar to the word “as” in “As for this rock…”.  
- **に** – a particle that shows the target of the comparison. In this sentence it links 何 (what) to the verb 似ている.  
- **似ている** – a verb meaning “to look like” or “to resemble”. It ends in 〜ている, so you can remember it as “〜ている” (the same pattern we learned for ongoing actions).  
- **です** – a polite copula that turns the verb into a sentence that can be answered.  
- **か** – a question particle that turns the whole statement into a question, like adding a question mark.

### N1 — この岩は何に似ていますか。
_8 words, 4 bullets, 1930 ms_

- **〜に似ている**：動作主体は比喩対象と同等の特性を示し、形容詞的な感覚を表す。  
- **〜に似ていますか**：疑問形で丁寧ながらも「相似」を客観的に求める。  
- **何に似ているか**：名詞化し、後続の修飾語や構造化された文脈に導入。  
- **この岩は何に似ていますか**：格助詞「は」で主語を強調し、比喩的比較の対象を限定。

### N5 — この報告書は要領をえていない。
_153 words, 6 bullets, 1062 ms_

- **は** — a particle that marks the topic of the sentence, similar to “as for” in English. It tells us what the rest of the sentence is about.  
- **この** — a demonstrative adjective meaning “this.” It directly modifies a noun just like “this book” or “this car.”  
- **報告書は** — “the report” becomes the topic with は, so the sentence focuses on that report.  
- **要領を** — the particle **を** marks the direct object of the verb. Here it shows that the report is *not* “to the point.”  
- **ない** — the plain negative suffix for adjectives and verbs, meaning “not.” It’s the opposite of “ある” (to have).  
- **〜ている** — a form that shows a state resulting from a completed action. In this sentence it tells us the report is *currently* not to the point. Think of it like “is not” in English (“the report is not to the point”).

### N1 — この報告書は要領をえていない。
_14 words, 4 bullets, 919 ms_

- **〜ている** (結果体) ― 動作の完了が現在の状態を示す。  
- **〜ていない** (否定継続体) ― 「まだ達成できていない」や「状態に欠けている」ニュアンスを強調。  
- 「要領をえていない」では「要領を取る」の連用形に**て**＋否定「いない」を結合し、報告書が「要領を取る」状態に欠けることを示す。  
- 文脈上は「要領を取れていない」と同義で、目的達成に必要な要領が欠如している点を指摘する。

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_135 words, 4 bullets, 667 ms_

- **住んでいる**  
  *Verb + ている* shows an ongoing action or a state that started in the past and continues now. Here it means “(is) living” as in “polar bears live on the ice.”

- **のだが**  
  The particle **の** turns a sentence into a statement, and **だ** is the plain copula (like “is”). Adding **が** after it gives a soft contrast, similar to the English “but.”  
  It is used to add extra information that may contrast with what follows.

- **失い**  
  This is the **て‑form** of the verb **失う** (“to lose”). The te‑form links clauses, like the English “and” when connecting actions: “loses” before the next clause.

- **であろう**  
  A polite, slightly speculative ending meaning “likely” or “probably.” It is similar to the English “will probably” or “might.”  
  It shows the speaker’s prediction about the future.

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_12 words, 4 bullets, 756 ms_

- **〜のだが**: 連体節＋のだで主語の説明を付与し、後続の対比や逆接を導く。文脈で「北極熊は…のだが」は「北極熊の存在とその事実を確定しつつ、後述する事象を提示」する論理的対立を示す。  
- **〜であろう**: 未来推量＋敬語体。推量の強度を高め、読者へ「恐るべき結果」を警告する。  
- **〜ているのだ**: 連体節＋のだで状態を確定し、感情や背景説明を暗示。ここでは「生息地を失い」後に「絶滅する」状態の推測を提示する。  
- **〜に住んでいる**: 目的格助詞＋動詞連用形＋いる。現在進行形ではなく「現在継続的状態」を示し、主語が「住み続ける」習慣的事実を明示。


## qwen/qwen3.8-27b (groq)

### N5 — もう３ページ残っている。
_142 words, 4 bullets, 20323 ms_

- **〜ている** — The main pattern here. Form: verb te-form + いる. It can mean "is doing" (action in progress) **or** "is in the resulting state" (something happened and still is). Here it's the second use: the pages were left and still are.
- English comparison: think of "I am tall" vs. "I grew tall." Japanese uses **〜ている** for both ongoing actions and settled states, so you'll see it everywhere even when no one is actively doing anything right now.
- **もう** — an adverb (a small word that adds information to the sentence, not tied to one noun). Here it means "still / more" — giving the feeling of "there are still three left."
- **残る** is intransitive (no を object). It just means "to remain / to be left over." The thing that remains is the subject of the sentence.

### N1 — もう３ページ残っている。
_58 words, 2 bullets, 1002 ms_

- **もう＋ている（継続・状態）**: Here もう marks residual quantity within an incomplete state, contrasting with its completive "already" reading (もう～た). The semantics require the state to be non-final.
- **残る（非自動詞）**: Intransitive framing — the pages *persist* rather than being *left behind* by an agent. Choosing 残う over 残す removes the causer from the event structure, typical of self-contained state descriptions.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
**ERROR** `empty`

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_66 words, 3 bullets, 1015 ms_

- **～と一緒に** — marks a secondary/accompanying object against a focal one (鶏肉). Creates a hierarchic 主従 structure, not a flat list.
- Contrast **～と～と～を** (flat co-equal enumeration) — the choice of に一緒に signals that chicken is the semantic head, salad/rolls are incidental accompaniments.
- **と** here is the listing conjunction (not the quotative); it sub-packages the accompanying items before に一緒に attaches them to the core VP.

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_142 words, 5 bullets, 1678 ms_

- **〜てください** — "Please do this." Take any verb, add てください, and you make a polite request. The closest English feel is "would you mind doing…?"
- **〜て chain** — The て form links actions in order: "remove… then fill… then drip…" It works like "and then" in English, showing one action follows another.
- **〜で (tool)** — Marking the tool or method: "with the dropper." You already know で as a location marker ("at/in"), but here it answers *how* or *with what* something is done.
- **〜へ (direction)** — Marks where something is going: "toward the marker's core." It's like "to" or "onto" in English, but it emphasizes the direction of movement rather than the endpoint.
- **〜を外す** — "Remove / take off." 外す means to take something out or off. The を before it marks exactly what is being removed.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_30 words, 2 bullets, 43321 ms_

- **て形 chain + ～てください** — canonical procedural pattern; the final verb carries the illocutionary force, earlier te-s are purely sequential.
- **適量、** — comma after an adverbial noun phrase

### N5 — 関税申告書が必要になります。
_168 words, 4 bullets, 174040 ms_

- **〜になる** — This is the verb なる (naru), meaning "to become." You stick it after a noun to say something "becomes" that state. Think of it like English "It *becomes* cold" — the noun follows "become" directly.
- **〜になります** — Just the polite (ます) form of になる. Same relationship as です → ます. You already know ですか is polite; here なる upgrades to になります for the same courtesy.
- **〜が必要になる** — Treat this as one memorizable chunk meaning "becomes necessary / is needed." Its pieces are: noun + が + 必要 (necessary) + になる (becomes). You don't need to master each part separately — just learn the whole block as a unit for now.
- **English comparison:** English says "A declaration *is required*" (passive). Japanese says "A declaration *becomes necessary*." The meaning is identical, but Japanese frames it as a change of state rather than a passive action. It's like the difference between "I am sad" and "I've become sad" — here Japanese picks the second angle.

### N1 — 関税申告書が必要になります。
_62 words, 3 bullets, 80658 ms_

- **必要がある / 〜が必要になる** — institutional/procedural necessity (rules, regulations, formal documents), not personal need; contrasts with なければならない (subjective obligation, speaker's stance).
- **〜になる** here marks a state transition into "necessity," typical of bureaucratic or institutional language; implies the situation *demands* it externally, not that the speaker wants it.
- Register: formal written notice, administrative prose. Colloquially one would say 必要だ or 届けてもらう.

### N5 — この本には美しい挿絵が入っている。
_123 words, 4 bullets, 70444 ms_

- **〜に入る** — A verb meaning "to be inside / to be contained in." The pictures are *in* the book, like objects in a box.
- **〜ている** — Sticks onto a verb to show the result of an action is still true now. Not "is happening," but "is in that state." Similar to English "The book *has* illustrations" — a fact right now.
- **〜には** — に marks the location ("inside"), は marks the topic. Together: "As for this book (topic), (inside) illustrations are contained." The は adds a "let's talk about this" feel.
- **美しい（i-adjective）** — A simple adjective ending in い. It sits directly before the noun it describes (挿絵 = pictures). No extra words needed — just place it before.

### N1 — この本には美しい挿絵が入っている。
_63 words, 2 bullets, 7360 ms_

- **〜ている** here encodes a **resultative stative**: the state is the outcome of an implicit agentive event (someone inserted the illustrations). Contrast with bare がある, which is a pure existential with no sense of prior causation.
- **入る** vs **ある**: 入る imposes a **part-whole containment constraint** (the illustration exists *within the boundary* of the book). This makes it the natural choice for illustrations

### N5 — 彼女は宝石を得意げに見せびらかした。
**ERROR** `empty`

### N1 — 彼女は宝石を得意げに見せびらかした。
**ERROR** `empty`

### N5 — 彼の福祉の概念はかなり観念的だ。
**ERROR** `empty`

### N1 — 彼の福祉の概念はかなり観念的だ。
**ERROR** `empty`

### N5 — この岩は何に似ていますか。
_161 words, 4 bullets, 1770 ms_

- **〜ている** — adds a "state" meaning to a verb. Here it doesn't mean an action is happening right now; it describes how something *appears* or *resembles* something. Think of it like English "looks like" — you're describing a current state, not an ongoing action.
- **に (comparison)** — a small word (called a particle) that marks a noun's role. In comparisons, に points to *what* something resembles — similar to "to" in "similar **to**."
- **何に** — 何 is "what." The particle に attaches to it, so together they ask "what (does it resemble?)."
- **か** — the question particle. It sits at the end of any sentence to turn it into a question. You already know ですね (friendly question); か is the neutral, textbook version.

So the sentence builds like this: 何に (what does it resemble?) + 似ている (has the appearance of) + か (question?). The verb part 似ている is simply 似る (to resemble) in its ている state form.

### N1 — この岩は何に似ていますか。
_80 words, 3 bullets, 912 ms_

- **〜に似ている** — に marks the *reference point* (model), not the subject of resemblance. Contrast with に in 「似合う」where に marks the *wearer/bearer*. The asymmetry is a common N1 trap.
- **似る** (un-prefixed, non-progressive) is literary/fixed-phrase register (e.g. 瓜二つに似る); in free syntax, 似ている is the only natural form. 似る in casual speech is a marked stylistic register.
- The interrogative form here (何に似て**いますか**) is neutral; 何に似て**いますか** (plain) would be flat/functional, while 何に似て**いる** (plain non-polite) can read as curt in writing.

### N5 — この報告書は要領をえていない。
_150 words, 4 bullets, 2000 ms_

- **〜ている** — A pattern that shows a state resulting from a completed action. Here it's in its negative form, **〜ていない**, meaning that state hasn't been reached yet. Think of it like English "hasn't gotten to" — the result doesn't exist.

- **〜をえる** — A fixed phrase (a set expression) meaning "to grasp the point or gist of something." You can't translate it word by word; it works as a unit. It pairs with abstract things like reports, plans, or ideas — not physical objects.

- **〜ていない** (negative of ている) — Adding ない to the verb tells us the state is *absent*. So the sentence says: the state of "having grasped the point" is not there → the report fails to convey anything clear.

- **Particle roles here** — は marks the topic (this report), を marks what is being "grasped" (the point/gist). Same particles, same jobs you already know.

### N1 — この報告書は要領をえていない。
_21 words, 1 bullets, 1124 ms_

- **要領を得ない**: Set expression (慣用表現), not a freely compositional V phrase; 得 here is える, not とう. Subject is the *text/s

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_50 words, 2 bullets, 2101 ms_

- **～ている** — verb te-form + いる. Shows an ongoing state, like English "is living" (happening now) instead of just "lives."
- **～のだが** — だが is a short form of だけれど, meaning "but / however." Important: this が is *not* the subject particle you already know. It's a connector word,

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_50 words, 2 bullets, 996 ms_

- **〜が** — Discourse-level adversative pivot; marks a rhetorical juxtaposition of a factual premise with an unfavorable consequence, creating a concessive *feel* without logical concession.
- **〜であろう** — Formal epistemic conjecture; literary register, significantly higher than だろう; carries a tone of solemn, quasi-prophetic assertion common in essays and formal commentary.


## command-a-plus-05-2026 (cohere)

### N5 — もう３ページ残っている。
_127 words, 5 bullets, 2884 ms_

- **もう** – means “already” or “still” and shows the speaker’s current situation; compare to “already” in “I already ate lunch.”
- **〜残っている** – a verb form meaning “is left” or “remains”; it tells what is still there, similar to “left” in “Three pages are left.”
- **Noun + 残っている** – when a noun follows this verb, it indicates how many of that thing are still remaining; e.g., “2 pages remaining.”
- **Particle は/が** – a small word that marks the subject of the sentence; “は” often marks the topic, like saying “As for the pages, three are left.”
- **Sentence ending 〜ている** – shows a continuous state; here it means the pages are still left now, just like “I am having three more pages to go.”

### N1 — もう３ページ残っている。
_59 words, 2 bullets, 1946 ms_

- **もう...残っている** – combines the adverb *もう* (already) with the progressive *残っている* to state the exact residual quantity; conveys that the speaker perceives the remaining amount as minimal and expects completion soon.  
- **残っている** – progressive form of *残る* emphasizing ongoing existence of the remainder; used with counters to quantify what is left, often in informal or conversational contexts.

### N5 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_141 words, 5 bullets, 2345 ms_

- **は (topic marker)** – Shows the subject of the sentence. It’s like saying “As for X…” in English. Here “彼は” means “As for him…”.

- **と (enumeration particle)** – Connects items in a list. It works like “and” when you’re naming things one after another. “サラダとロールパン” means “salad and rolls”.

- **一緒に (adverbial phrase)** – Means “together with” or “along with”. It tells how the action was done, similar to “together with” in English. “サラダとロールパンと一緒に” means “together with salad and rolls”.

- **を (object marker)** – Marks the direct object of the verb. It points out what is being acted on, like “chicken” in “ate chicken”. So “鶏肉を” means “chicken (as the thing eaten)”.

- **た (past tense ending)** – Shows the action happened in the past. It’s the past form of the verb “食べる” (to eat). “食べた” means “ate”.

### N1 — 彼はサラダとロールパンと一緒に鶏肉を食べた。
_34 words, 2 bullets, 1960 ms_

- **〜を食べた** – Past tense of transitive verb; indicates completed action with object marked by を.  
- **Xと一緒に** – Postpositional phrase denoting simultaneous participation; modifies the main clause, linking actions or states occurring together.

### N5 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_141 words, 5 bullets, 4388 ms_

- **〜の** – shows that one thing belongs to or is part of another (like “the cap of the ink bottle”). It connects a noun to another noun that modifies it.  
- **〜を外し** – “外し” is the masu‑form of the verb “外す” (to remove) with the object particle “を”. It means “remove the cap”.  
- **〜で吸い上げ** – “吸い上げ” is the masu‑form of “吸い上げる” (to draw up/suck up) using “で” to show the tool (the dropper). It means “draw up ink with the dropper”.  
- **〜へ適量、滴下** – “滴下” is the masu‑form of “滴下する” (to drip). “へ” marks the destination (onto the marker’s core), and “適量” means “appropriate amount”.  
- **〜てください** – a polite request form (like “please do something”). It is made from the te‑form of a verb plus “ください”. Here it asks the listener to perform the whole set of actions.

### N1 — インキ補充瓶のキャップを外し、スポイトでインキを吸い上げ、マーカーの吸収体へ適量、滴下してください。
_83 words, 4 bullets, 3085 ms_

- **〜し** – te-form of a transitive verb used to list sequential actions; each clause ends with し, linking without explicit conjunction.  
- **〜て** – connective particle after 吸い上げ indicating the next step follows the previous action; often omitted in rapid instructions.  
- **〜へ** – particle marking the destination of an action; here directing the ink onto the marker's core, not the source.  
- **〜ください** – polite imperative formed from the verb stem くれ; conveys a request to the listener, softening the directive.

### N5 — 関税申告書が必要になります。
_79 words, 4 bullets, 1756 ms_

- **〜になります** – shows that something will become a certain state; compare to “will be” in English. Here it tells us the customs declaration will become required.
- **必要** (noun meaning “necessary”) – used with **〜になります** to say something becomes necessary; the pattern “Xが必要になります” means “X will become necessary.”
- **が** (particle) – marks the subject “関税申告書” (the customs declaration) as what the sentence is about.
- **です** (copula) – ends the sentence politely, similar to “is” in English.

### N1 — 関税申告書が必要になります。
_49 words, 2 bullets, 1811 ms_

- **必要になります** – expresses a shift to a required state; the subject becomes obligatory, often used in formal notices or regulations.  
- The construction follows *[Noun] + が + 必要 + になります*, where the nominal subject is marked by が and the predicate is a stative verb indicating necessity.

### N5 — この本には美しい挿絵が入っている。
_125 words, 5 bullets, 2582 ms_

- **〜には** – shows the place or thing that contains something; think of “in this book” like “in this box” in English.  
- **〜は** – marks the topic of the sentence; it tells us what we are talking about, similar to “This book” at the start of a sentence.  
- **〜が** – works like “beautiful” describing a noun; it’s a short form of “beautiful illustrations” and is placed right before the noun.  
- **〜が入っている** – means “is inside” or “is included,” used for something that exists inside something else; compare to “are in” as in “the pictures are in the book.”  
- **〜ている** – shows a continuous state; here it tells us the book stays illustrated, just like saying “the book is illustrated” in English.

### N1 — この本には美しい挿絵が入っている。
_68 words, 2 bullets, 2499 ms_

- **には...が入っている** – topic marker *には* marks the container or location; the verb *入っている* (present progressive of *入る*) indicates that something is currently inside or part of it. The construction denotes inclusion, not merely existence.  
- **美しい挿絵** – the attributive adjective *美しい* directly modifies the noun *挿絵* without any copular verb, a standard pre-nominal modifier; its scope is limited to the noun phrase, not to the whole clause.

### N5 — 彼女は宝石を得意げに見せびらかした。
_131 words, 5 bullets, 3173 ms_

- **は (topic marker)** – Shows what the sentence is about. Think of it like “As for” in English: “As for her, she…”.  
- **を (object marker)** – Marks the thing that receives the action. It’s like the direct object in English: “displayed the jewels”.  
- **得意げに (adverbial phrase)** – Means “proudly.” It tells how the action is done, similar to “with pride” in English.  
- **見せびらかした (verb)** – A past tense verb meaning “showed off” or “displayed.” It combines “show” (見せる) with a suffix that adds the sense of doing it repeatedly or conspicuously.  
- **〜げ (suffix)** – Turns an adjective or feeling into an expression of that state, e.g., “proud” becomes “proudly.” It’s like adding “-ly” to an adjective in English, but it can also describe a visible attitude.

### N1 — 彼女は宝石を得意げに見せびらかした。
_55 words, 2 bullets, 1881 ms_

- **得意げに** – nominalized 得意 + げ, indicating a displayed, confident demeanor; a stative adverbial form used in narrative to convey the speaker’s perceived self-assurance.  
- **見せびらかした** – past tense of the compound verb 見せびらかす, formed from 見せる (show) + びらかす (scatter, display ostentatiously); denotes an exaggerated, showy presentation, often with negative connotation of flaunting.

### N5 — 彼の福祉の概念はかなり観念的だ。
_146 words, 5 bullets, 2971 ms_

- **所有格助詞「の」** – attaches a noun to another noun to show “of.” In *彼の福祉の概念*, it works like “his welfare’s concept,” meaning the concept belonging to him. Think of it as adding “’s” in English, but it can also connect two nouns.

- **名詞修飾「XのY」** – a noun phrase where the first noun (X) modifies the second noun (Y). *福祉の概念* is “concept of welfare,” similar to “welfare concept” in English, but the order is reversed.

- **副詞「かなり」** – an adverb meaning “quite.” It comes before an adjective to strengthen its meaning, as in *かなり観念的だ*.

- **な形容詞「観念的だ」** – a noun‑based adjective (called a *な形容詞*) that ends in *だ* after the stem. It describes something that is abstract or theoretical, like “abstract.” Compare to English “is abstract.”

- **述語構造「…だ」** – the copula *だ* ends a statement, linking the subject (*彼の福祉の概念*) to the description (*かなり観念的だ*). It works like “is” in English.

### N1 — 彼の福祉の概念はかなり観念的だ。
_33 words, 2 bullets, 1966 ms_

- **XのY** – genitive construction linking possessor X to noun Y; here 「彼の福祉の概念」 denotes "his concept of welfare."
- **かなりYだ** – intensifier 「かなり」 modifies the na-adjective 「観念的だ」 to express degree, yielding "pretty abstract."

### N5 — この岩は何に似ていますか。
_192 words, 6 bullets, 4014 ms_

- **何に** – “what” followed by the particle **に** (shows direction or comparison). It asks what the rock looks like, similar to “What does it look like?” in English, where “what” is the thing being compared to.

- **〜に似ています** – “is similar to”. This is a polite present‑continuous form meaning “looks like” or “resembles”. It is used to describe similarity, like saying “It looks like a dog” in English.

- **は/が/を/です** – basic particles and copula. **は** marks the topic (the rock), **が** can mark the subject in a question, **を** marks the object of the verb “似ています”, and **です** is the polite “is” used after nouns or na‑adjectives.

- **この** – a demonstrative adjective meaning “this”. It points to something near the speaker, just as “this” does in English before a noun.

- **岩** – a noun meaning “rock”. Nouns in Japanese usually stay unchanged and are followed by particles or the copula **です** when they act as the predicate.

- **か** – sentence‑ending particle that makes a question. It follows the verb phrase, turning a statement into a question, similar to adding “?” at the end of an English question.

### N1 — この岩は何に似ていますか。
_51 words, 2 bullets, 2356 ms_

- **～は何に～ていますか** – interrogative construction asking for the object of resemblance; the verb in the te-iru form follows the “what” noun phrase introduced by 「何に」.  
- **～ています** – present progressive/attributive form indicating a current state of similarity; used with the verb 似る to convey “looks like” in a literal, descriptive register.

### N5 — この報告書は要領をえていない。
_126 words, 5 bullets, 4575 ms_

- **は (topic marker)** – shows what the sentence is about; think of it like “as for X” in English.  
- **を (object particle)** – marks the thing that receives the action; similar to the direct object “the point” in “catch the point.”  
- **えていない (negative progressive)** – combines the verb “える” (to get) with “いない” to mean “is not doing”; it’s like “is not getting” or “has not gotten” in English, showing an ongoing lack.  
- **ない (negative suffix)** – added after a verb or adjective to make it negative; compare to adding “not” before a verb, e.g., “did not get.”  
- **全体構造 (sentence structure)** – a simple Subject‑Object‑Verb order: topic + object + verb; this mirrors English “This report does not get the point.”

### N1 — この報告書は要領をえていない。
_52 words, 2 bullets, 2149 ms — judge: fit 5/5, acc 5/5 — The explanation is precise and uses terminology appropriate for an N1 learner while correctly identifying the idiomatic usage._

- **〜ていない**: resultative negative of a verb, indicating a state that has not been achieved; here, the report has not succeeded in capturing the gist.  
- **要領をえる**: idiomatic expression meaning “to grasp the essential point”; the negative form negates the completeness of the action, implying a failure to be concise or relevant.

### N5 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_165 words, 5 bullets, 2567 ms_

- **〜は ... に住んでいる** – Shows where something lives. The subject (北極熊) is placed before は, then the place (極地の氷原) follows に, and the verb ends with ている (present progressive). *Like “The polar bear lives on the polar ice‑cap.”*

- **〜のだが** – Connects two sentences, the first giving background info and the second giving a result. It works like “but” or “however” in English. The だ after the noun makes it a statement.

- **〜を生息地を失い** – A verb phrase meaning “lose its habitat.” The verb 失う (lose) is used with the particle を and the noun 生息地 (habitat). The い at the end shows a completed action.

- **〜絶滅するであろう** – Predicts a future action: “will die out.” The verb 絶滅する (become extinct) is followed by the future‑predictive であろう, similar to “will” in English.

- **〜ていく** – Not present in this sentence, but often used after ている to show continuation; you can think of it as “keeps doing.” (Mentioned only as a brief note for comparison.)

### N1 — 北極熊は極地の氷原に住んでいるのだが、生息地を失い、絶滅するであろう。
_46 words, 2 bullets, 1433 ms_

- **〜ている** – nominalizes a present state; 「住んでいる」 conveys that polar bears currently inhabit the ice cap, not an action in progress.  
- **のだが** – concessive connective; introduces a contrast between the known fact of their habitat and the upcoming consequence, adding a formal, explanatory tone.
