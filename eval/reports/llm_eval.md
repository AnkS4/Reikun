# LLM evaluation — level-aware vs generic grammar prompt

5 sentences x levels N5, N1 x 2 prompts. Judge = Groq (blind to prompt variant), scores 1-5.

generated=2026-10-22 10:57 UTC · version=0.8.0 · commit=8b492f1+dirty · model=openai/gpt-oss-120b · judge=groq · sentences=5

| Level | Prompt | avg words | avg jargon terms | analogy rate | judge: level fit | judge: accuracy |
|---|---|---|---|---|---|---|
| N5 | level-aware | 81 | 3.6 | 60% | 4.4 | 4.4 |
| N5 | generic | 161.2 | 7 | 20% | 3.8 | 4.4 |
| N1 | level-aware | 40 | 2.2 | 0% | 4.4 | 4.2 |
| N1 | generic | 145.6 | 7 | 20% | 4.2 | 4.2 |

## Side-by-side outputs

### ほとんど空なのでガソリンを入れなくてはなりません。

**N5 · level-aware** — fit 4/5, accuracy 4/5, 91 words, 5 jargon terms · *The explanation is mostly correct but slightly mislabels ほとんど as modifying a noun and uses some terminology a bit advanced for N5.*

- **ほとんど** (ほとんど) — “almost”; an adverb that modifies the following noun, indicating a large degree.  
- **なので** (空 + なので) — particle **な** + copula **だ** in plain form + **ので**; expresses reason “because” after a noun or na‑adjective.  
- **入れなくては** (入れ + なくて + は) — verb stem **入れ** + negative **ない** → **なくて** (conjunctive “not doing”) + particle **は**; forms the conditional “must” when followed by **ならない/なりません**.  
- **なりません** (なる + ません) — verb **なる** “to become” in polite negative **ません**; together with **…ては** expresses obligation “have to”.

**N5 · generic** — fit 4/5, accuracy 5/5, 175 words, 7 jargon terms · *The explanation is accurate and clear, though it uses slightly advanced terminology for an N5 learner.*

- **～ので** – a conjunctive particle that gives a reason or cause. It attaches to a plain‑form clause (here the adjective‑noun phrase ほとんど空) and means “because / since”. The sentence therefore starts with a causal clause.  
- **ほとんど** – an adverb meaning “almost / nearly”. When placed before a noun or adjective it modifies the predicate (ほとんど空 = “almost empty”). This is a lexical‑adverb pattern rather than a grammatical construction.  
- **～なくてはならない** – the “must / have to” construction. It is formed from the negative‑stem of a verb (入れ**な**く) + ては + ならない. The colloquial contraction is **入れなくては**. It expresses an obligatory action.  
- **Verb‑stem + なくては** – a shortened form of the full pattern that still retains the same meaning. In spoken Japanese the final ならない is often omitted when the context makes the obligation clear, but the grammar remains the same.  
- **Polite ending – です** – attaches to the whole predicate (入れなくてはなりません) to give a formal, polite tone. The underlying structure is the plain form 入れなくてはならない, which becomes the polite ません form.

**N1 · level-aware** — fit 5/5, accuracy 5/5, 25 words, 2 jargon terms · *The explanation correctly identifies the ので causal clause and the なくてはならない contraction, matching N1 expectations.*

- **なので** (空なので) — ので reason clause with copula, softens causal link, informal explanatory nuance.  
- **なくては** (入れなくては) — contraction of なくてはならない, expresses obligatory necessity.

**N1 · generic** — fit 4/5, accuracy 5/5, 143 words, 10 jargon terms · *The explanation is accurate and appropriate for N1, though it could use slightly more advanced terminology.*

- **～ので** – a conjunctive particle that gives a reason or cause. It attaches to a plain‑form clause (here the adjective‑noun phrase “ほとんど空”) and links it to the following statement, indicating “because / since”.  
- **ほとんど** – an adverb meaning “almost / nearly”. When placed before a noun or adjective it modifies the degree, turning “空” (empty) into “almost empty”.  
- **～なくてはならない** – the “must / have to” construction. It is formed from the negative‑te form of a verb (入れ**なくて**) + the auxiliary **は** + **ならない** (literally “it will not be acceptable”). The whole pattern expresses an obligatory action.  
- **Verb‑stem + なくては** – the “if‑not‑do” conditional part of the above pattern; the te‑form of the negative creates a conditional clause that the main clause (ならない) evaluates.  
- **です** – polite copula attached to the predicate “入れなくてはなりません” to give a formal, polite ending.

### あなたのサイトは、猫に興味のある人達にとって魅力的です。

**N5 · level-aware** — fit 4/5, accuracy 4/5, 97 words, 4 jargon terms · *The explanation is mostly correct and appropriate for N5, though the description of に and の could be clearer.*

- **は** (あなたのサイトは) — topic particle; marks “your site” as the thing being talked about, similar to “as for …” in English.  
- **に** (猫に) — particle indicating the target of interest, like “in/for cats”.  
- **の** (興味の) — possessive particle linking the noun “interest” to the following verb, equivalent to “’s” or “of”.  
- **ある** (ある) — plain form of the verb “to exist”; here it turns “interest” into a relative clause “interest that exists”.  
- **にとって** (にとって) — set phrase meaning “for” or “to (someone)”, showing the perspective of “people who are interested in cats”.

**N5 · generic** — fit 3/5, accuracy 5/5, 143 words, 9 jargon terms · *The explanation is grammatically correct but includes constructions (relative clause, にとって) that are a bit advanced for an N5 learner.*

- **は (topic marker)** – marks “あなたのサイト” as the topic of the sentence, indicating that the statement that follows is about your site.  
- **に興味のある** – a relative clause formed with the noun‑modifier pattern “Nに興味がある”. The particle **に** marks the object of interest (cats), and **ある** is conjugated to the attributive form **ある** to modify the following noun **人達**.  
- **人達にとって** – the expression “Nにとって” means “for N” or “as far as N is concerned”. Here it introduces the perspective of “people who are interested in cats”.  
- **魅力的です** – a **na‑adjective** (魅力的) followed by the polite copula **です**, stating that the site is attractive.  
- **の (possessive particle)** – connects “あなた” and “サイト” to show ownership (your site).  

These patterns together create the structure: *[Topic] は, [relative clause] にとって [predicate]*, meaning “Your site is attractive for people who are interested in cats.”

**N1 · level-aware** — fit 5/5, accuracy 3/5, 55 words, 4 jargon terms · *Explanation is appropriate for N1 but misdescribes the structure of 興味のある, calling it a の nominalization which is inaccurate.*

- **にとって** (にとって) — marks the standpoint of “people”; indicates that the site is attractive from the perspective of those individuals.  
- **のある** (興味のある) — relative clause using の to nominalize the adjective‑noun phrase, forming “people who have interest”.  
- **です** (です) — polite copula, linking the predicate “魅力的” to the subject; maintains formal register.

**N1 · generic** — fit 5/5, accuracy 4/5, 138 words, 9 jargon terms · *The explanation is well‑suited for N1 learners and mostly accurate, though calling の a ‘nominalizer’ is slightly imprecise.*

- **は (topic marker)** – Marks “あなたのサイト” as the topic of the sentence, indicating what is being talked about.  
- **に (target/beneficiary marker)** – Connects “猫に興味のある人達” to “とって”, showing the group for whom the statement holds true (the people interested in cats).  
- **の (nominalizer / relative clause connector)** – Links the relative clause “猫に興味のある” to the noun “人達”, turning the clause into an attributive modifier (“people who are interested in cats”).  
- **とって (〜にとって)** – A set phrase meaning “for …, as far as … is concerned”; it expresses the standpoint or relevance of the preceding noun phrase.  
- **です (copula, polite)** – Provides a polite declarative ending, equating the subject (your site) with the predicate “魅力的”.  
- **魅力的 (na‑adjective)** – Functions as a predicate adjective; when used with です, it forms the polite statement “is attractive/appealing”.

### 彼女は吠える犬を怖がる。

**N5 · level-aware** — fit 5/5, accuracy 5/5, 77 words, 3 jargon terms · *The explanation correctly matches N5 vocabulary and accurately describes each grammatical element.*

- **は** (彼女は) — topic particle; marks “she” as the topic of the sentence, similar to “as for …”.  
- **を** (犬を) — object particle; marks “barking dogs” as the direct object of the verb “to fear”.  
- **連体形** (吠える) — attributive form of the verb 吠える “to bark”; used before a noun to mean “barking”.  
- **辞書形** (怖がる) — dictionary (plain) form of the verb 怖がる “to be afraid of”; expresses a habitual or general state.

**N5 · generic** — fit 5/5, accuracy 5/5, 151 words, 5 jargon terms · *The explanation correctly matches N5 vocabulary and grammar, and accurately describes each particle and structure in the sentence.*

- **は (topic marker)** – Marks the noun *彼女* as the topic of the sentence, indicating “as for she…”. It is not the grammatical subject but the discourse focus.  
- **Relative clause before a noun** – *吠える* (present‑plain) directly modifies *犬*, forming the noun phrase *吠える犬* (“barking dog(s)”). This is a typical prenominal clause where the verb is in plain form and the noun follows.  
- **を (object marker)** – Marks the noun phrase *吠える犬* as the direct object of the verb *怖がる*. The construction “X を 怖がる” means “to be afraid of X”.  
- **怖がる (verb of feeling)** – A **感情動詞** that expresses the speaker’s emotional reaction toward the object marked by を. It follows the pattern “N を + 怖がる” for “to fear N”.  
- **Sentence‑final verb** – Japanese sentences end with the predicate; here *怖がる* appears at the end, giving the sentence its declarative mood without any copula.

**N1 · level-aware** — fit 5/5, accuracy 5/5, 40 words, 2 jargon terms · *The explanation correctly identifies the functions of は, を, and the relative clause 吠える犬, using appropriate N1‑level terminology.*

- **は** (彼女は) — topic marker, contrasts with other possible subjects.  
- **を** (犬を) — object marker for the verb 怖がる, indicating the feared entity.  
- **連体修飾** (吠える犬) — plain non‑past form 吠える directly modifies 犬, forming a relative clause.

**N1 · generic** — fit 4/5, accuracy 5/5, 138 words, 3 jargon terms · *The explanation is accurate and clear, though slightly basic for N1, it matches the learner’s level well.*

- **は (topic marker)** – Marks the noun before it (彼女) as the topic of the sentence, indicating “as for she…”.  
- **Relative clause before a noun** – The verb phrase 吠える directly modifies 犬, forming a relative clause “barking dog”. This is the typical “verb‑noun” modifier pattern where the verb is in plain form and precedes the noun it describes.  
- **を (object marker)** – Marks the noun phrase 吠える犬 as the direct object of the verb 怖がる, showing what is feared.  
- **怖がる (verb of feeling)** – A “‑がる” verb that expresses the speaker’s observation of someone’s emotional state; it takes a direct object marked by を.  
- **Subject‑object‑verb (SOV) order** – Japanese sentences typically place the subject/topic first, the object second, and the verb at the end, as seen in 彼女は … 犬を … 怖がる.

### 水を加えてペースト状になるまでかき回しなさい。

**N5 · level-aware** — fit 4/5, accuracy 5/5, 81 words, 3 jargon terms · *The explanation correctly identifies each grammatical element and its function, though a few terms could be simplified for a pure N5 audience.*

- **を** (水を) — object particle marking “water” as the thing being added.  
- **て** (加えて) — te‑form connective; links “add water” to the next action, similar to “and then”.  
- **になる** (ペースト状になる) — “to become”; attaches to a noun (ペースト状) to express a change of state.  
- **まで** (…になるまで) — “until”; indicates the point at which the preceding clause is completed.  
- **なさい** (かき回しなさい) — polite command form; attaches to the verb stem (かき回し) to tell the listener to “stir”.

**N5 · generic** — fit 4/5, accuracy 5/5, 164 words, 5 jargon terms · *The explanation is mostly correct but uses slightly advanced terminology for an N5 learner.*

- **て‑form (conjunctive)** – The verb *加える* is put into its て‑form (*加えて*) to link two actions, indicating that “adding water” is performed first and is followed by the next instruction.  

- **V‑るまで** – The clause *ペースト状になるまで* uses the pattern “verb‑dictionary form + まで” to mean “until it becomes a paste.” This sets a temporal limit for the subsequent action.  

- **Verb‑stem + なさい** – *かき回しなさい* is the polite imperative formed by attaching the suffix *‑なさい* to the verb stem *かき回し*. It commands the listener to “stir” (or “keep stirring”).  

- **Sequential instruction with て‑form + まで** – The overall structure *Vて … V‑るまで + V‑stemなさい* combines the て‑form linking and the “until” clause, giving a single instruction: first add water, then continue stirring **until** the mixture reaches the desired consistency.  

- **Implicit continuation** – Because the imperative follows the *まで* clause, the listener understands that the stirring should be continuous throughout the period “until it becomes a paste,” not a single brief action.

**N1 · level-aware** — fit 4/5, accuracy 5/5, 43 words, 2 jargon terms · *The explanation correctly covers the て‑form, まで, and なさい usage, though it could use slightly more advanced terminology for an N1 learner.*

- **〜て** (加えて) — て‑form of 加える linking sequential actions.  
- **〜まで** (になるまで) — “until” clause marking the point at which the preceding state is reached.  
- **〜なさい** (かき回しなさい) — polite imperative formed with the verb stem + なさい, giving a direct instruction.

**N1 · generic** — fit 5/5, accuracy 5/5, 143 words, 7 jargon terms · *The explanation accurately and appropriately details the grammar points for an N1 learner.*

- **て‑form connective (加えて)** – The verb *加える* is put in its て‑form to link actions, indicating that “adding water” is performed first and is followed by the next instruction.  
- **Verb‑stem + なさい (かき回しなさい)** – The polite imperative is formed by attaching *なさい* to the verb stem *かき回し* (from *かき回す*). This gives a gentle command “stir”.  
- **まで (ペースト状になるまで)** – The particle *まで* marks the limit of the preceding clause, meaning “until it becomes a paste”. It attaches to the plain‑form clause *ペースト状になる* (to become paste‑like).  
- **Resultative construction (なる)** – *なる* follows the noun *ペースト状* to express a change of state: “to turn into a paste”.  
- **Sequential ordering implied by て‑form + まで** – The combination of the て‑form clause and the *まで* clause creates a sequence: first add water, then continue stirring **until** the mixture reaches the desired consistency.

### いすをもっと火の近くに寄せなさい。

**N5 · level-aware** — fit 5/5, accuracy 4/5, 59 words, 3 jargon terms · *Explanation is clear and appropriate for N5, but omits noting that 近く is a noun plus に and that もっと modifies 寄せ, so slightly incomplete.*

- **を** (いすを) — particle that marks the direct object of a verb, here “chair”.  
- **に** (近くに) — particle indicating the target location where something is moved.  
- **もっと** — adverb that intensifies the following phrase, meaning “more”.  
- **なさい** (寄せなさい) — polite command form; attach to the verb stem (寄せ) to tell someone to do the action.

**N5 · generic** — fit 3/5, accuracy 2/5, 173 words, 9 jargon terms · *The explanation contains several inaccuracies (e.g., mislabeling 寄せる as causative) and uses terminology that is a bit advanced for an N5 learner.*

- **Direct Object Marker を** – marks the noun “いす” as the thing being acted upon by the verb “寄せる”.  
- **Degree Adverb もっと** – modifies the verb phrase, indicating “more” or “closer” compared with a previous state.  
- **Location Particle に** (after “近く”) – shows the target location where the action is directed: “near the fire”. The noun “近く” (near) takes に to become an adverbial phrase “近くに”.  
- **Verb Stem + せ (Causative) → 寄せる** – “寄せる” is the transitive form of “寄る” (to approach), meaning “to bring/put something closer”. The stem “寄せ” plus the verb ending “る” creates the causative‑like sense of moving an object toward a point.  
- **Imperative Polite Command ～なさい** – attaches to the verb stem “寄せ” to give a gentle command or instruction, often used by a superior speaking to a subordinate or a parent to a child.  
- **Placement of Modifiers** – the order “もっと … に寄せなさい” follows the typical Japanese pattern: degree adverb → location particle → verb‑imperative, keeping the sentence concise and directive.

**N1 · level-aware** — fit 3/5, accuracy 3/5, 37 words, 1 jargon terms · *The explanation covers the basic particles but omits important points like the role of もっと and the nuance of 寄せる, making it somewhat incomplete for N1 level.*

- **を** (いすを) — marks いす as the direct object of the verb.  
- **に** (近くに) — locative particle indicating the destination “near the fire.”  
- **〜なさい** (寄せなさい) — polite imperative, used to issue a direct command.

**N1 · generic** — fit 3/5, accuracy 2/5, 166 words, 6 jargon terms · *The explanation contains several inaccuracies (e.g., misdescribing 寄せる as a causative and the particle usage), making it only partially correct for an N1 learner.*

- **Direct Object Marker を** – marks “いす” as the thing being acted upon; the verb “寄せる” takes a direct object, so “いすを” indicates “the chair (to be moved).”

- **Degree Adverb もっと** – modifies the following location phrase, meaning “more” or “closer”; it intensifies the spatial relationship expressed by “近くに.”

- **Location Particle に** (used twice) – first after “近く” to indicate the target location (“near the fire”), and second after “火の” to mark “fire” as the reference point for “近く.” The structure “火の近くに” = “to the vicinity of the fire.”

- **Verb Stem + させる → 寄せる** – “寄せる” is the transitive form of “寄る” (to approach/bring near). The pattern “V‑stem + せる” creates a causative meaning, here “to bring (something) close.”

- **Imperative Polite Command なさい** – attaches to the verb stem “寄せ” to give a gentle command or instruction. The pattern “V‑stem + なさい” is used by a speaker of higher status (e.g., parent, teacher) to tell the listener to do something.
