<script lang="ts">
	import Header from '#lib/components/Header.svelte';

	// NOTE: This policy is deliberately NOT localized — like the footer, legal
	// text stays English in every locale (see the note in Footer.svelte). If it
	// ever needs a Japanese version, add a parallel document rather than
	// running these strings through t().
</script>

<svelte:head>
	<title>Privacy Policy · Reikun</title>
	<meta
		name="description"
		content="What Reikun records, what it never records, how long data is kept, and what is sent to third-party LLM providers."
	/>
</svelte:head>

<Header />

<nav class="policy-nav"><a href="/">← Reikun</a></nav>

<article class="policy">
	<h1>Privacy Policy</h1>
	<p class="lede">
		Reikun is free, needs no account, and works without cookies. This page describes exactly what
		the service records, what it never records, and how long it is kept. Last updated: November
		2026.
	</p>

	<section>
		<h2>What is never collected</h2>
		<ul>
			<li>No cookies, no accounts, no sign-in — the dictionary works fully anonymously.</li>
			<li>No cross-site tracking and no advertising: telemetry never records IP addresses or
				user-agent strings, and no third-party ad or analytics cookies are set.</li>
			<li>Cloudflare Web Analytics, when enabled, is a cookieless beacon that reports aggregate
				page-view metrics only.</li>
		</ul>
	</section>

	<section>
		<h2>What is recorded to improve the dictionary</h2>
		<p>
			Search requests are logged: the query text as you typed it, the rewritten/translated form
			used for retrieval, the search mode, result counts and latency. These logs train better
			embeddings and ranking. Kanji-detail views are logged the same way.
		</p>
		<p>
			Feedback (thumbs up/down) is tied to a one-way SHA-256 hash of the query, never its raw
			text. Grammar-explanation requests store the sentence only as a SHA-256 hash, alongside the
			JLPT level and latency.
		</p>
	</section>

	<section>
		<h2>What is stored in your browser</h2>
		<p>
			Recent searches and your interface-language choice are kept in your browser's local
			storage. They never leave your device and are not part of the server-side logs above.
		</p>
	</section>

	<section>
		<h2>Third-party LLM providers</h2>
		<p>
			Grammar explanations and English descriptive query rewrites are generated on demand by an
			external LLM provider. When you request an explanation, the Japanese sentence, its English
			translation and the selected JLPT level are sent to the provider; long English descriptive
			queries may also be sent for rewriting. Provider-side retention is governed by the
			provider's own terms.
		</p>
	</section>

	<section>
		<h2>Where data lives and how long it is kept</h2>
		<p>
			On the hosted deployment, telemetry goes to the platform's log store (Google Cloud
			Logging, which retains entries for 30 days by default). Self-hosted instances can persist
			events to a local SQLite database instead; there, rows are kept indefinitely by default —
			setting <code>TELEMETRY_RETENTION_DAYS</code> turns on an automatic purge of rows older
			than that window. Hashes cannot be reversed.
		</p>
	</section>

	<section>
		<h2>Questions</h2>
		<p>
			Open an issue or discussion at
			<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer"
				>github.com/AnkS4/Reikun</a
			>.
		</p>
	</section>
</article>

<style>
	.policy-nav {
		padding-top: 1.5rem;
	}

	.policy-nav a {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--text-muted);
		text-decoration: none;
	}

	.policy-nav a:hover {
		color: var(--text);
	}

	.policy {
		max-width: 38rem;
		margin: 2.5rem auto 0;
	}

	.policy h1 {
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

	.policy section {
		margin-top: 2.25rem;
	}

	.policy h2 {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-faint);
		margin: 0 0 0.75rem;
	}

	.policy p,
	.policy li {
		font-size: 0.95rem;
		line-height: 1.7;
		color: var(--text-muted);
	}

	.policy ul {
		margin: 0;
		padding-left: 1.25rem;
	}

	.policy li + li {
		margin-top: 0.4rem;
	}

	.policy code {
		font-family: var(--font-mono);
		font-size: 0.85em;
	}

	.policy a {
		color: var(--primary);
		text-decoration: underline;
		text-decoration-color: var(--border);
	}

	.policy a:hover {
		text-decoration-color: var(--text);
	}
</style>
