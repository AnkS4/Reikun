<script lang="ts">
	import Footer from '#lib/components/Footer.svelte';
</script>

<svelte:head>
	<title>About — Reikun</title>
	<meta
		name="description"
		content="About Reikun (例訓) — a free semantic Japanese dictionary: bilingual search, sentence breakdowns with furigana, kanji stroke order, and JLPT-calibrated grammar explanations."
	/>
</svelte:head>

<nav class="about-nav"><a href="/">← Reikun</a></nav>

<article class="about">
	<h1>About Reikun</h1>
	<p class="lede">
		Reikun (例訓) is a free, open-source Japanese reading assistant — a semantic dictionary that works in
		both English and Japanese.
	</p>

	<section>
		<h2>What it does</h2>
		<ul>
			<li>
				<strong>Search</strong> — look up words in English or Japanese; natural-language questions
				("how do you say X") are rewritten into dictionary terms automatically.
			</li>
			<li>
				<strong>Sentence breakdown</strong> — paste a Japanese sentence and it is split into word
				units with furigana, per-word glosses, and hover detail.
			</li>
			<li>
				<strong>Kanji</strong> — readings, meanings, common compounds, JLPT level, and animated
				stroke-order diagrams.
			</li>
			<li>
				<strong>Grammar explanations</strong> — concise explanations calibrated to a JLPT level
				(N5–N1), generated on demand.
			</li>
		</ul>
	</section>

	<section>
		<h2>How it works</h2>
		<p>
			Search runs hybrid retrieval — dense vector embeddings plus BM25 — fused in Qdrant, with query
			routing that picks the right plan for English words, English sentences, and Japanese input.
			Sentence parsing uses the Sudachi morphological analyzer; embeddings are quantized ONNX models
			running on CPU. The frontend is a static SvelteKit site; the API is a FastAPI service.
		</p>
	</section>

	<section>
		<h2>Data and sources</h2>
		<p>
			Dictionary data comes from <a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project" target="_blank" rel="noopener noreferrer">JMdict</a>
			and <a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project" target="_blank" rel="noopener noreferrer">KANJIDIC2</a> (<a href="https://www.edrdg.org/" target="_blank" rel="noopener noreferrer">EDRDG</a>,
			<a href="https://www.edrdg.org/edrdg/licence.html" target="_blank" rel="noopener noreferrer">CC BY-SA 4.0</a>). Example sentences are from the
			<a href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus" target="_blank" rel="noopener noreferrer">Tanaka Corpus</a> (Tatoeba, CC-BY 2.0 FR).
			Kanji stroke diagrams derive from <a href="https://kanjivg.tagaini.net/" target="_blank" rel="noopener noreferrer">KanjiVG</a> (Ulrich Apel,
			CC BY-SA 3.0).
		</p>
	</section>

	<section>
		<h2>Privacy</h2>
		<p>
			No cookies and no cross-site tracking. Queries are logged anonymously — stored only as hashes —
			to improve search quality.
		</p>
	</section>

	<section>
		<h2>Source</h2>
		<p>
			Reikun is built by Aniket Satbhai. The code is
			<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">on GitHub</a>
			under the Apache-2.0 license.
		</p>
	</section>
</article>

<Footer />

<style>
	.about-nav {
		padding-top: 1.5rem;
	}

	.about-nav a {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--text-muted);
		text-decoration: none;
	}

	.about-nav a:hover {
		color: var(--text);
	}

	.about {
		max-width: 38rem;
		margin: 2.5rem auto 0;
	}

	.about h1 {
		font-family: var(--font-display);
		font-size: clamp(1.8rem, 5vw, 2.4rem);
		font-weight: 500;
		margin: 0 0 1rem;
	}

	.lede {
		font-size: 1.05rem;
		line-height: 1.7;
		color: var(--text);
	}

	.about section {
		margin-top: 2.25rem;
	}

	.about h2 {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin: 0 0 0.75rem;
	}

	.about p,
	.about li {
		font-size: 0.95rem;
		line-height: 1.7;
		color: var(--text-muted);
	}

	.about ul {
		margin: 0;
		padding-left: 1.25rem;
	}

	.about li + li {
		margin-top: 0.4rem;
	}

	.about a {
		color: var(--primary);
		text-decoration: underline;
		text-decoration-color: var(--border);
	}

	.about a:hover {
		text-decoration-color: var(--text);
	}
</style>
