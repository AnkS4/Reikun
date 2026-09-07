# LLM evaluation — level-aware vs generic grammar prompt

5 sentences × levels N5, N1 × 2 prompts. Judge = Cohere (blind to prompt variant), scores 1–5.

| Level | Prompt | avg words | avg jargon terms | analogy rate | judge: level fit | judge: accuracy |
|---|---|---|---|---|---|---|
| N5 | level-aware | 69.6 | 0.6 | 100% | 4.4 | 4.2 |
| N5 | generic | 83.4 | 2.8 | 0% | 3.4 | 3.8 |
| N1 | level-aware | 107 | 3.2 | 40% | 4.8 | 4.4 |
| N1 | generic | 86.6 | 5.4 | 0% | 4.4 | 4.4 |

## Side-by-side outputs

### もっと果物を食べるべきです。

**N5 · level-aware** — fit 5/5, accuracy 4/5, 63 words, 2 jargon terms · *The explanation is well‑suited for N5 learners and mostly accurate, though it could clarify that もっと modifies the verb, not directly the quantity of the object.*

- **～べきです** – shows a recommendation or duty; like “you ought to” in English.  
- **もっと** – means “more”; it adds the idea of increasing quantity before the verb.  
- **～を** – object particle; marks what is being acted upon, similar to “fruit” in “eat fruit.”  
- **～です** – polite sentence‑ending copula; makes the statement polite, like adding “sir” or “please” in English.

**N5 · generic** — fit 4/5, accuracy 5/5, 61 words, 1 jargon terms · *Explanation is clear and mostly correct, though some terminology may be slightly advanced for N5.*

- **もっと** – adverb indicating a greater quantity; modifies the following verb phrase to suggest doing something more.
- **果物を食べる** – verb phrase with **を** marking the direct object; the base form of the verb follows the object.
- **べきです** – modal auxiliary expressing recommendation or mild obligation; attaches to the base verb form and ends the sentence with polite assertion.

**N1 · level-aware** — fit 5/5, accuracy 5/5, 108 words, 2 jargon terms · *The explanation is precise, covers all elements, and is appropriately detailed for an N1 learner.*

- **もっと...** – Emphasizes a comparative increase; functions as an intensifier similar to “more” in English, modifying the following noun phrase.  
- **べき** – Modal suffix expressing a strong recommendation or moral obligation; conveys “should” with a formal, objective tone.  
- **です** – Polite copula ending that softens statements and aligns with the deferential register; often omitted in informal contexts.  
- **Plain verb 食べる** – Base form of the verb “to eat,” used here in its non‑past, non‑negative form to describe a general action without aspectual nuance.  
- **Object particle を** – Marks 果物 as the direct object of the verb, a standard transitive marker in Japanese syntax.

**N1 · generic** — fit 5/5, accuracy 4/5, 90 words, 6 jargon terms · *The explanation is well-suited for N1 learners but slightly mislabels '食べる' as intransitive and should note 'べきです' as a polite obligation construction.*

- **もっと** – adverb indicating an increase in quantity, placed before the verb phrase to modify the degree of action.  
- **を** – object particle marking “果物” as the direct object of the transitive verb “食べる”.  
- **食べる** – base form of the intransitive verb “to eat”, functioning as the main predicate in the clause.  
- **べき** – auxiliary suffix expressing recommendation or moral obligation, attaching to the verb stem to indicate what should be done.  
- **です** – polite copula ending that finalizes the sentence in a deferential register.

### ワシが空を飛んでいる。

**N5 · level-aware** — fit 4/5, accuracy 4/5, 73 words, 0 jargon terms · *The explanation is mostly correct and appropriate for N5, but the description of を as the thing that "receives the action" is slightly misleading for a location phrase.*

- **が** – shows who or what does the action, like “the eagle” in “The eagle is flying.”  
- **を** – marks the thing that receives the action, similar to “the sky” in “The eagle flies through the sky.”  
- **〜ている** – means an action is happening now or continuously, just like “is flying” in English.  

These three parts together tell us who is doing what, where, and that it’s happening right now.

**N5 · generic** — fit 4/5, accuracy 3/5, 82 words, 1 jargon terms · *The explanation is mostly understandable for N5 learners but misidentifies the object and incorrectly describes the verb form.*

- **Subject marker (が)**: Marks the subject “ワシ” (eagle), indicating it performs the action.  
- **Object marker (を)**: Marks the direct object “空” (sky), showing what the action is performed on.  
- **Verb base form**: The verb “飛ぶ” (to fly) appears in its dictionary form before the auxiliary, indicating the action being described.  
- **Present progressive (ている)**: Attaches to the verb base to express an ongoing action happening now (“is flying”).  
- **Sentence order**: Typical Japanese SOV structure: [Subject]が [Object]を [Verb phrase]ている.

**N1 · level-aware** — fit 5/5, accuracy 4/5, 105 words, 2 jargon terms · *The explanation is mostly accurate and well-suited for N1, though it slightly misstates the role of を in the verb phrase.*

- **ている** – present progressive/ongoing state; attaches to the base of a verb to show that the action is currently happening or the resulting condition persists.  
- **を** – direct‑object particle; marks the noun that receives the action of the verb (here, “空”).  
- **が** – subject particle; introduces the noun performing the action (here, “ワシ”).  
- **飛ぶ** – base (dictionary) form of a intransitive verb; when combined with **を** + noun, it creates a verb phrase describing the action performed on that noun.  
- **ワシが空を飛んでいる** combines subject + object + present‑progressive verb to convey a continuous action in the present, typical of narrative description.

**N1 · generic** — fit 4/5, accuracy 5/5, 86 words, 3 jargon terms · *The explanation is accurate but could be more concise for N1 learners.*

- **Subject‑Particle が**: The noun before が marks the subject of the sentence.  
- **Object‑Particle を**: The noun before を indicates the object being acted upon.  
- **Verb stem + ている**: The present progressive form shows an ongoing action; here, “飛ぶ” (to fly) becomes “飛んでいる”.  
- **Basic SOV structure**: Japanese typically follows Subject‑Object‑Verb order, illustrated by the sequence of subject, object, and verb phrase.  
- **Nominalization of action**: The ている form nominalizes the verb, allowing it to function as a noun phrase describing the current state.

### 私たちの学校には立派な図書館があります。

**N5 · level-aware** — fit 5/5, accuracy 5/5, 55 words, 0 jargon terms · *The explanation is perfectly suited for N5 learners and accurately breaks down each component of the sentence.*

- **〜の** – shows possession; like “our school” = “私たちの学校”.  
- **〜には** – marks the place or topic of existence; think “in our school, there is”.  
- **立派な〜** – “nice/large/ impressive” before a noun; works like the English adjective “nice”.  
- **〜があります** – “there is/are”; used for non‑human things, similar to “we have a …”.

**N5 · generic** — fit 3/5, accuracy 4/5, 91 words, 5 jargon terms · *Explanation is mostly accurate but a bit overly detailed for N5 learners.*

- **の** – Nominalizer linking a noun to a possessor; forms a possessive phrase (“our school”).  
- **には** – Topic marker for a location, indicating the place where something exists; combines the particle **に** (location) with **は** (topic emphasis).  
- **な** – Attributive particle linking an adjective to a noun; turns the adjective “立派” into a modifier of “図書館”.  
- **が** – Subject marker introducing the entity that exists; precedes the existence verb.  
- **あります** – Polite existence verb indicating the presence of something; used with a subject introduced by **が**.

**N1 · level-aware** — fit 4/5, accuracy 4/5, 113 words, 2 jargon terms · *Explanation is mostly accurate and suitable for N1, though some nuance about は and the role of の could be clarified.*

- **〜は** – marks the topic of the sentence; the element before は is what the speaker is commenting on (our school).  
- **〜に** – indicates a location where something exists; it attaches to the place noun and is followed by the existence verb.  
- **〜があります** – a polite, non‑subjective existence predicate; the subject is omitted and the noun phrase before に is the location, while the noun after があります is the thing that exists.  
- **〜の** – nominalizing particle forming a possessor‑possessed relationship; it turns the noun phrase into a modifier, linking 「私たち」 to 「学校」.  
- **〜な** – connects an adjective to a noun, forming a compound noun; here 「立派」 modifies 「図書館」.

**N1 · generic** — fit 3/5, accuracy 4/5, 65 words, 2 jargon terms · *The explanation is mostly correct but could be more precise about the particle は and the overall structure.*

- **Possessive construction (たち + の)**: Forms a collective noun phrase indicating “our group’s school.”
- **Topic/location particle に + は**: Marks the location (“our school”) as the topic of the sentence.
- **Adjective + noun (立派な図書館)**: Combines a na-adjective “立派な” with a noun “図書館” to modify the object.
- **Existence verb (あります)**: Expresses that something exists in the location introduced by the previous particle.

### あなたは始発電車に間にあいましたか。

**N5 · level-aware** — fit 5/5, accuracy 4/5, 76 words, 0 jargon terms · *The explanation is well-suited for N5 learners but slightly oversimplifies the function of に and the meaning of 間にあいました.*

- **は** – shows the topic, like “you” in English.  
- **に** – marks the destination or target, similar to “to” before a place.  
- **〜ました** – polite past tense of a verb; think of it as “did/catched” with a polite tone.  
- **か** – turns a statement into a question, like adding “?” at the end.  

These pieces together form a polite question asking if the listener managed to reach the first train on time.

**N5 · generic** — fit 4/5, accuracy 4/5, 74 words, 3 jargon terms · *The explanation is mostly clear and suitable for N5, though the term "target particle" for に is a bit advanced.*

- **は (topic marker)** – Introduces the topic “you” at the start of the sentence.  
- **に (target particle)** – Marks the destination of the action, i.e., the first train.  
- **間に合う (verb)** – Expresses “to make it in time”; used in its past polite form **間にあいました** to indicate a completed action with respect to the listener.  
- **か (question particle)** – Attaches to the end of the sentence to form a yes‑no question.

**N1 · level-aware** — fit 5/5, accuracy 4/5, 75 words, 3 jargon terms · *The explanation is well-suited for N1 learners but slightly oversimplifies the polite form and the function of に.*

- **〜は** – Topic marker; marks 「あなたは」 as the subject of the sentence.  
- **〜に** – Indirect object particle; attaches to the noun phrase that indicates the target or destination, here 「始発電車」.  
- **動詞＋〜た** – Past descriptive form; forms the polite past tense 「間に合いました」.  
- **〜か** – Sentence-final interrogative particle; converts the statement into a polite question.  
- **丁寧語** – The entire construction uses polite language (ます‑form, です‑like endings), appropriate for formal or deferential address.

**N1 · generic** — fit 5/5, accuracy 5/5, 73 words, 3 jargon terms · *The explanation accurately identifies and explains each component for a N1 learner.*

- **Topic Marker は**: Marks the topic “あなた” (you) at the start of the sentence.  
- **Object Particle に**: Indicates the destination or target of the action, attaching to “始発電車” (first train).  
- **Verb 間に合う (past polite form)**: Expresses successfully reaching the train; “間にあいました” is the polite past tense of the intransitive verb “間に合う”.  
- **Question Particle か**: Suffixed to the verb to form a yes‑no question, giving the sentence its interrogative function.

### 自分が約束したことはちゃんと実行するように最善を尽くすべきだ。

**N5 · level-aware** — fit 3/5, accuracy 4/5, 81 words, 1 jargon terms · *The explanation is mostly correct but uses slightly advanced terminology for N5 learners.*

- **Xが** – shows who does the action. Think of “X is the one who…”.  
- **動詞た** – past tense of a verb, meaning “did”. Like “I promised”.  
- **こと** – turns a phrase into a noun, similar to “the thing that”.  
- **はちゃんと** – “properly” or “well”, a particle phrase that adds a sense of doing something right.  
- **ように** – “in order to”, like “to do something”.  
- **最善を尽くすべきだ** – “should do one’s best”, using the moral‑obligation pattern “べきだ”.

**N5 · generic** — fit 2/5, accuracy 3/5, 109 words, 4 jargon terms · *Explanation is somewhat accurate but uses overly technical terms and misses key N5-level details.*

- **「...は」**: Marks the noun phrase “自分が約束したことは” as the topic of the sentence.  
- **「...が...を...した」**: Relative clause where the subject (自分が) performs the action (約束した) on the object (約束), forming a noun phrase that serves as the topic.  
- **「...ように」**: Purpose/imperative construction indicating the intended manner of action; follows the verb “実行する” to mean “so that one executes properly.”  
- **「...ように最善を尽くすべきだ」**: Combined pattern of **「ように」** + verb phrase expressing a recommendation; “すべきだ” adds a modal sense of “ought to.”  
- **「最善を尽くす」**: Verb phrase meaning “to do one’s best,” functioning as the main predicate after the purpose clause.  
- **「だ」**: Copula ending the declarative sentence, giving a final, emphatic tone.

**N1 · level-aware** — fit 5/5, accuracy 5/5, 134 words, 7 jargon terms · *The explanation is precise, uses appropriate N1-level terminology, and fully captures the grammar and meaning of the sentence.*

- **約束したことは** – nominalizes a past action; “the things that were promised.” The clause functions as a noun phrase subject, with the topic marker *が* indicating the speaker’s own promises.  
- **ちゃんと実行するように** – *ように* attaches to the te-form *実行する* to express purpose or intention; “so as to properly carry out.” The adverb *ちゃんと* adds emphasis on thoroughness.  
- **最善を尽くすべきだ** – *べきだ* is a deontic auxiliary expressing moral obligation; “should.” *最善を尽くす* is a verb phrase meaning “to do one’s utmost,” and the *だ* ending provides a declarative, somewhat formal tone.  
- **自分が…ことは** – the *は* particle marks the whole nominalized clause as the topic, while *自分が* sets the speaker as the agent, creating a contrast between self‑reference and general expectation.  
- **〜だ** – final copula reinforces the statement’s assertiveness, suitable for formal or written contexts.

**N1 · generic** — fit 5/5, accuracy 4/5, 119 words, 13 jargon terms · *The explanation is well‑suited for N1 learners but has minor inaccuracies in describing the functions of は and ように.*

- **Relative clause**: 自分が約束した → nominalizes the action “promised” with the subject “I,” forming a noun phrase that functions as the antecedent for the following clause.  
- **Topic marker は**: follows the noun phrase 自分が約束したことで, marking it as the topic of the sentence.  
- **Nominalized clause ように**: attaches the te-form verb 実行する to the particle ように, creating a purpose clause meaning “in order to carry out.”  
- **Adverbial particle ちゃんと**: modifies the verb 実行する, indicating thorough or proper execution.  
- **Prepositional phrase 最善を尽くすべきだ**: uses the noun 最善 (best) + を + verb 尽くす (to exert) + auxiliary べきだ (should), forming a modal predicate that expresses obligation.  
- **Sentence-ending auxiliary だ**: attaches to the predicate to assert a declarative statement.
