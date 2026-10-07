# LLM evaluation — level-aware vs generic grammar prompt

5 sentences x levels N5, N1 x 2 prompts. Judge = Groq (blind to prompt variant), scores 1-5.

| Level | Prompt | avg words | avg jargon terms | analogy rate | judge: level fit | judge: accuracy |
|---|---|---|---|---|---|---|
| N5 | level-aware | 83.2 | 3.4 | 40% | 4 | 4.4 |
| N5 | generic | 143.2 | 4.2 | 40% | 4 | 4.6 |
| N1 | level-aware | 39 | 1.8 | 0% | 4.4 | 4 |
| N1 | generic | 152.4 | 4.8 | 40% | 4.4 | 4.2 |

## Side-by-side outputs

### ほとんど空なのでガソリンを入れなくてはなりません。

**N5 · level-aware** — fit 3/5, accuracy 4/5, 83 words, 4 jargon terms · *The explanation is mostly correct but uses some intermediate terminology (e.g., 連用形) that may be a bit advanced for an N5 learner.*

- **ほとんど** (ほとんど) — adverb meaning “almost”; placed before an adjective or noun to show a high degree.  
- **なので** (空なので) — “because …”; formed from the copula だ → 連用形 (だ→で) + ので, linking a noun‑adjective clause to the reason for the next statement.  
- **を** (ガソリンを) — particle marking the direct object of the verb, showing what is being put in.  
- **入れなくてはなりません** (入れなくてはなりません) — “must …”; negative verb stem + ては + ならない in polite present, expressing an unavoidable obligation.

**N5 · generic** — fit 5/5, accuracy 5/5, 179 words, 5 jargon terms · *The explanation is spot‑on for an N5 learner and accurately describes each grammatical element.*

- **～ので** – a conjunctive particle that gives a reason or cause. It attaches to a plain‑form clause (here the adjective 空だ → 空なので) and means “because / since”. It is softer and more explanatory than から.  
- **ほとんど** – an adverb meaning “almost / nearly”. When placed before a noun or adjective it modifies the degree (ほとんど空 = “almost empty”). It is not a verb form but a lexical adverb that works like an intensifier.  
- **～なくてはならない** – the “must / have to” construction. It is formed from the negative ない → なくて + the particle は + the copula なる in the plain present ならない. The pattern literally means “if it is not done, it will not become acceptable”, i.e., “it is necessary to do”.  
- **入れなくては** – the negative‑te form of the verb 入れる (入れなくて) followed by the contrastive particle は, marking the condition for the following obligation.  
- **なりません** – the polite negative present of なる, completing the idiom ～なくてはならない in its polite form. It conveys the same “must” meaning while keeping the sentence polite.

**N1 · level-aware** — fit 4/5, accuracy 3/5, 45 words, 3 jargon terms · *Explanation is mostly appropriate for N1, but misstates that ほとんど modifies a noun and incorrectly describes なくてはならない as a past‑negative form.*

- **ほとんど** (ほとんど) — adverbial intensifier meaning “almost”; modifies the following noun.  
- **〜なので** (空なので) — explanatory reason clause; copula だ in 連用形 + ので, indicating “because it is …”.  
- **〜なくてはならない** (入れなくてはなりません) — formal necessity; negative て-form + は + ならない, polite past‑negative‑required construction.

**N1 · generic** — fit 4/5, accuracy 3/5, 148 words, 6 jargon terms · *The explanation uses appropriate N1 terminology but contains several inaccuracies about the formation and polite form of ～なくてはならない.*

- **～ので** – a conjunctive particle that gives a reason or cause. It connects a plain‑form clause (ほとんど空) to the following statement, meaning “because/since it is almost empty.”  
- **ほとんど** – an adverb meaning “almost, nearly.” When placed before a noun or adjective it modifies it directly (ほとんど空 = “almost empty”).  
- **～なくてはならない** – the “must / have to” construction. It is formed from the negative plain form of a verb (入れない) → なくて, followed by the particle は and the copula ならない. The whole pattern expresses an obligatory action: “must put in gasoline.”  
- **Verb‑stem + なくては** – the “if not” conditional nuance within the obligatory pattern; it implies that if the action is not done, an undesirable situation results.  
- **Polite ending – です** – attaches to the obligatory phrase (ならない) to make the sentence polite, yielding ならな**い**です → なら**ません**. This keeps the overall statement formal.

### あなたのサイトは、猫に興味のある人達にとって魅力的です。

**N5 · level-aware** — fit 4/5, accuracy 5/5, 99 words, 2 jargon terms · *The explanation is accurate and clear, though a few terms are slightly above the typical N5 vocabulary.*

- **は** (あなたのサイトは) — topic particle; marks “your site” as the thing being talked about, similar to “as for …”.  
- **にとって** (人達にとって) — “for …”; attaches to a noun to show the viewpoint or benefit, like “to/for the people”.  
- **のある** (興味のある) — relative clause; の links the noun “interest” to the verb ある (to exist), forming “who have interest”.  
- **たち** (人達) — plural suffix; adds たち to a noun to indicate “people” rather than a single person.  
- **魅力的です** (魅力的です) — na‑adjective + です; “魅力的” is a na‑adjective meaning “attractive”, and です makes it polite present.

**N5 · generic** — fit 3/5, accuracy 5/5, 133 words, 6 jargon terms · *The explanation is grammatically correct but includes constructions (e.g., にとって, relative clause) that are slightly beyond typical N5 material.*

- **は (topic marker)** – marks 「あなたのサイト」 as the topic of the sentence, indicating that the statement that follows is about “your site.”  
- **の (possessive/genitive)** – connects 「あなた」 and 「サイト」 to show ownership (“your site”).  
- **に興味のある** – a relative clause formed with the noun 「興味」 plus the particle 「に」 (target of interest) and the attributive form of the verb 「ある」, modifying 「人達」 to mean “people who are interested in cats.”  
- **にとって** – a dative expression meaning “for …” or “as far as … is concerned,” used here to indicate the perspective of the interested people.  
- **魅力的です** – the na‑adjective 「魅力的」 (attractive/appealing) followed by the polite copula 「です」, stating the predicate “is attractive.”  

These patterns together construct the meaning “Your site is attractive to people who are interested in cats.”

**N1 · level-aware** — fit 5/5, accuracy 5/5, 43 words, 2 jargon terms · *The explanation correctly and appropriately covers the N1‑level grammar points in the sentence.*

- **にとって** (人達にとって) — “as for …”, marks the standpoint or relevance of the preceding noun.  
- **魅力的です** (魅力的です) — na‑adjective + です; polite present copula stating a quality.  
- **は** (あなたのサイトは) — topic particle indicating contrast or focus, typical in expository statements.

**N1 · generic** — fit 4/5, accuracy 5/5, 153 words, 7 jargon terms · *The explanation is accurate and clear, though it could include slightly more advanced nuances for an N1 learner.*

- **は (topic marker)** – Marks “あなたのサイト” as the topic of the sentence, indicating that the statement that follows is about the site.  
- **の (possessive/nominalizer)** – Connects “あなた” and “サイト” to show ownership (“your site”), and also links “興味” and “ある” in the relative clause “猫に興味のある”.  
- **に (target/indirect object)** – In “猫に興味”, the particle に indicates the object of interest (the cats) that the people are interested in.  
- **にとって (for, from the viewpoint of)** – Forms the expression “人達にとって”, meaning “for the people”, showing the perspective or relevance of the statement to that group.  
- **興味のある (relative clause)** – Uses the adjective‑like noun “興味” plus the copular の and the verb ある to create a relative clause that modifies “人達” (“people who have an interest in cats”).  
- **魅力的です (na‑adjective + です)** – “魅力的” is a na‑adjective meaning “attractive/appealing”; です adds politeness and functions as the predicate, completing the sentence.

### 彼女は吠える犬を怖がる。

**N5 · level-aware** — fit 4/5, accuracy 5/5, 84 words, 3 jargon terms · *The explanation is accurate and mostly appropriate for N5, though terms like 連体形 may be slightly advanced.*

- **は** (彼女は) — topic particle; marks “she” as the topic of the sentence, similar to “as for …”.  
- **を** (犬を) — object particle; marks “dog” as the direct object of the verb that follows.  
- **連体形** (吠える犬) — attributive form of a verb; the verb 吠える is in its plain “‑る” form and directly modifies the noun 犬, meaning “barking dog”.  
- **怖がる** (怖がる) — verb “to be afraid of”; the “‑がる” ending shows a feeling that the subject experiences toward something.

**N5 · generic** — fit 4/5, accuracy 5/5, 121 words, 3 jargon terms · *The explanation is accurate and clear, though it uses some intermediate terms that may be a bit advanced for a pure N5 learner.*

- **は (topic marker)** – Marks the noun before it (彼女) as the topic of the sentence, indicating that the statement is about her.  
- **連体修飾 (noun‑modifying clause)** – The verb 吠える directly precedes 犬, forming a relative clause that describes “dogs that bark.”  
- **を (object marker)** – Indicates the direct object of the verb 怖がる; here the object is the noun phrase 吠える犬 (“barking dogs”).  
- **がる (psychological‑state verb suffix)** – The verb 怖がる is a “‑がる” construction used to express a speaker’s observation of someone else’s feeling (her being afraid).  
- **SはOをV (topic‑object‑verb pattern)** – The overall structure follows the common Japanese pattern where the topic (彼女) is followed by the object (吠える犬) and then the verb (怖がる).

**N1 · level-aware** — fit 4/5, accuracy 2/5, 47 words, 2 jargon terms · *The explanation misidentifies the particle for the feared object (should be が, not を) and thus is inaccurate despite being roughly appropriate for N1.*

- **は** (彼女は) — topic marker, foregrounds “she” as the experiencer, often contrastive.  
- **を** (犬を) — object marker used with the psych‑verb **がる**, marking the stimulus of fear.  
- **〜がる** (怖がる) — auxiliary expressing the speaker’s inference of the subject’s feeling; here “to be afraid (of)”.

**N1 · generic** — fit 5/5, accuracy 5/5, 177 words, 4 jargon terms · *The explanation is well‑suited to an N1 learner and accurately describes the grammar of the sentence.*

- **は (topic marker)** – Marks *彼女* as the topic of the sentence, indicating that the statement is about her rather than being the grammatical subject of the verb.  
- **Verb‑modifying relative clause** – *吠える* directly modifies *犬* to form *吠える犬* (“barking dog”). In Japanese, a plain‑form verb placed before a noun creates a relative clause without any extra particles.  
- **を (object marker)** – Here *を* follows the noun phrase *吠える犬*, showing that the dog is the direct object of the verb *怖がる*. Although *怖がる* is often used with *が* to express “to be afraid of,” it can also take *を* when treated as a transitive verb meaning “to fear.”  
- **怖がる (intransitive/verb of emotion)** – The verb expresses the speaker’s emotional reaction. When used with *が*, it means “to feel fear toward X”; with *を* (as in this sentence) it functions similarly, treating the feared entity as a direct object.  
- **Sentence structure (Topic‑Object‑Verb)** – The overall order is **Topic (彼女は) – Object (吠える犬を) – Predicate (怖がる)**, which is the typical SOV pattern of Japanese.

### 水を加えてペースト状になるまでかき回しなさい。

**N5 · level-aware** — fit 4/5, accuracy 4/5, 93 words, 4 jargon terms · *Overall appropriate for N5, but the explanation of になる is slightly inaccurate and could be clearer.*

- **を** (水を) — particle marking “water” as the direct object of the verb “add”.  
- **て** (加えて) — te‑form connecting verbs; here it links “add” and “stir”, meaning “and then”.  
- **になる** (ペースト状になる) — “to become”; formed from the dictionary verb なる plus になる, showing a change of state.  
- **まで** (になるまで) — particle meaning “until”; attaches to the clause “become a paste” to set the point where the action stops.  
- **なさい** (かき回しなさい) — polite command form; attaches to the verb stem (かき回す → かき回し) to tell the listener to “stir”.

**N5 · generic** — fit 4/5, accuracy 4/5, 150 words, 5 jargon terms · *The explanation is mostly correct and clear, but a few nuances (e.g., the role of the te‑form) are slightly oversimplified for an N5 learner.*

- **Te‑form (～て)** – “加えて” links the first action (add water) to the following clause, showing a sequential or concurrent action. The te‑form also creates a soft command when followed by another verb.  
- **Verb‑stem + なさい** – “かき回しなさい” is the polite imperative formed by attaching **なさい** to the verb stem “かき回し”. It gives a direct instruction in a courteous tone.  
- **まで** – The particle “まで” after “ペースト状になる” marks the endpoint of the action: continue stirring **until** the mixture becomes paste‑like.  
- **Verb‑dictionary form + になる** – “ペースト状になる” uses “なる” to express a change of state (“become paste‑like”). The noun “ペースト状” functions as a nominal adjective describing the resulting state.  
- **Compound verb construction** – The sentence combines two clauses (water addition and stirring) with the te‑form, then adds a purpose clause with “まで” before issuing the final command, illustrating how Japanese strings multiple actions into a single instruction.

**N1 · level-aware** — fit 5/5, accuracy 5/5, 42 words, 2 jargon terms · *The explanation correctly identifies the functions of て, まで, and なさい and is suitably detailed for an N1 learner.*

- **て** (加えて) — conjunctive て linking sequential actions, here “add water and …”.  
- **になるまで** (ペースト状になるまで) — “until it becomes …”; まで attaches to the result clause.  
- **なさい** (かき回しなさい) — polite imperative formed from verb stem + なさい, commanding “stir”.

**N1 · generic** — fit 4/5, accuracy 3/5, 140 words, 5 jargon terms · *Explanation is mostly appropriate for N1 but misstates the form of かき回す (it appears as stem+なさい, not plain) and is slightly simplistic.*

- **～て (te-form) + ください / なさい** – The te‑form links actions and is followed by the imperative 「なさい」 to give a polite command: “do X and then Y.”  
- **～まで** – A particle indicating the limit or endpoint of an action; here it marks the point at which the stirring should continue (“until it becomes a paste”).  
- **～になる** – The copular construction 「なる」 expresses a change of state; combined with a noun (ペースト状) it means “to become a paste‑like consistency.”  
- **Verb‑stem + かき回す** – The verb 「かき回す」 (to stir, mix) appears in its plain form after the te‑linked clause, showing the second step of the instruction.  
- **Verb‑stem + て** – The first verb 「加える」 is put into its te‑form 「加えて」 to connect it to the subsequent action, creating a sequential command (“add water and then stir”).

### いすをもっと火の近くに寄せなさい。

**N5 · level-aware** — fit 5/5, accuracy 4/5, 57 words, 4 jargon terms · *Explanation is clear and appropriate for N5, but it omits the role of もっと and could note that 近くに marks the location rather than direction.*

- **を** (いすを) — particle marking the direct object “chair”.  
- **に** (近くに) — particle indicating the target location “near the fire”.  
- **寄せ** (寄せ) — verb stem of 寄せる “to bring close”; used before certain endings.  
- **なさい** (寄せなさい) — polite command formed by attaching なさい to a verb stem, telling someone to do the action.

**N5 · generic** — fit 4/5, accuracy 4/5, 133 words, 2 jargon terms · *Explanation is mostly correct and appropriate for N5, but the description of もっと and the nuance of 近くに could be clearer.*

- **を (direct‑object marker)** – marks the noun いす as the thing being acted upon by the verb 寄せる.  
- **もっと (comparative adverb)** – modifies the location phrase, indicating “more” or “closer” relative to a reference point.  
- **に (locative particle)** – attaches to 近く, turning the noun “nearby” into a location “to the fire’s vicinity,” showing where the chair should be moved.  
- **近くに (noun + に for location)** – the noun 近く (“nearby”) combined with に expresses the target area “near the fire.”  
- **～なさい (polite imperative)** – attaches to the verb stem 寄せ, forming a gentle command “please bring/put (it) …”. It is used for giving instructions, especially to someone of lower status or a child.  

These patterns together convey the instruction to move the chair closer to the fire.

**N1 · level-aware** — fit 4/5, accuracy 5/5, 18 words, 0 jargon terms · *The explanation correctly identifies ～なさい as a polite imperative, suitable for an N1 learner though a bit brief.*

- **～なさい** (寄せなさい) — polite imperative; commands the listener to perform the action of 寄せる (to bring close).

**N1 · generic** — fit 5/5, accuracy 5/5, 144 words, 2 jargon terms · *The explanation accurately and appropriately details the grammar for an N1 learner.*

- **Direct Object Marker を** – marks “いす” as the thing being acted upon; the verb “寄せる” takes a direct object, so the chair is the object of the action.  
- **Degree Adverb もっと** – modifies the location phrase “火の近くに,” indicating a greater extent (“more”/“closer”). It intensifies the spatial relationship.  
- **Location Particle に** – attaches to “火の近く” to indicate the target location where the chair should be moved; the structure “X に Y を 〜” shows “move Y to X.”  
- **Noun + の + Noun (火の近く)** – a genitive construction where “火の” (fire’s) modifies “近く” (nearby), forming “the vicinity of the fire.”  
- **Imperative Form ～なさい** – polite command form derived from the verb stem “寄せ” + “なさい,” used to give instructions or orders in a gentle but firm tone.  

These patterns combine to express “move the chair more toward the fire.”
