<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
</script>

<svelte:head>
	<title>{t('aboutTitle')}</title>
	<meta name="description" content={t('aboutMeta')} />
</svelte:head>

<nav class="about-nav"><a href="/">← Reikun</a></nav>

<article class="about">
	<div class="about-title-row">
		<img
			src="/icons/emblem.svg"
			alt=""
			class="brand-icon about-brand-icon"
			aria-hidden="true"
		/>
		<h1>{t('aboutTitle')}</h1>
	</div>
	<p class="lede">{t('aboutLede')}</p>

	<section>
		<h2>{t('whatItDoes')}</h2>
		<ul>
			<li><strong>{t('search')}</strong> — {t('searchText')}</li>
			<li><strong>{t('breakdownBold')}</strong> — {t('breakdownText')}</li>
			<li><strong>{t('kanjiBold')}</strong> — {t('kanjiText')}</li>
			<li><strong>{t('grammarBold')}</strong> — {t('grammarText')}</li>
		</ul>
	</section>

	<section>
		<h2>{t('howItWorks')}</h2>
		<p>{t('howText')}</p>
	</section>

	<section>
		<h2>{t('dataSources')}</h2>
		<p>
			{t('dataBefore')}<a
				href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"
				target="_blank"
				rel="noopener noreferrer">JMdict</a
			>{t('dataAnd')}<a
				href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project"
				target="_blank"
				rel="noopener noreferrer">KANJIDIC2</a
			>{t('dataAfter')}<a
				href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus"
				target="_blank"
				rel="noopener noreferrer">Tanaka Corpus</a
			>{t('dataAfter2')}<a
				href="https://kanjivg.tagaini.net/"
				target="_blank"
				rel="noopener noreferrer">KanjiVG</a
			>{t('dataAfter3')}
		</p>
	</section>

	<section>
		<h2>{t('privacy')}</h2>
		<p>{t('privacyText')}</p>
		<p>{t('llmProviderText')}</p>
	</section>

	<section>
		<h2>{t('source')}</h2>
		<p>
			{t('sourceBefore')}<a
				href="https://github.com/AnkS4/Reikun"
				target="_blank"
				rel="noopener noreferrer">{t('sourceLink')}</a
			>{t('sourceAfter')}
		</p>
	</section>
</article>

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

	.about-title-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0 0 1rem;
	}

	.about-brand-icon {
		width: clamp(2rem, 5vw, 2.5rem);
		height: clamp(2rem, 5vw, 2.5rem);
		border-radius: 22%;
		flex-shrink: 0;
	}

	.about h1 {
		font-family: var(--font-display);
		font-size: clamp(1.8rem, 5vw, 2.4rem);
		font-weight: 500;
		margin: 0;
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
