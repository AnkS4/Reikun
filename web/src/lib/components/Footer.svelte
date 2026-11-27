<script lang="ts">
	// NOTE: The footer is intentionally NOT localized — it stays in English even
	// when the UI language is set to Japanese. Legal/credit lines (copyright,
	// license name, data-source attribution) should remain untranslatable, so do
	// not run these strings through t() or add them to the i18n dictionaries.
	//
	// The DATA credits differ per edition (each site attributes the sources it
	// actually serves); the design and the brand lines stay identical.
	import { currentPack } from '#lib/lang/pack.ts';

	const pack = currentPack();
</script>

<footer class="footer">
	<div class="footer-content">
		<p class="footer-license">
			Reikun © 2026 Aniket Satbhai ·
			<a href="/about">About</a> ·
			<a href="/privacy">Privacy</a> ·
			<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">GitHub</a> ·
			<a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">Apache-2.0</a>
		</p>
		{#if pack === 'es'}
			<p class="footer-data">
				Dictionary data from <a
					href="https://es.wiktionary.org/"
					target="_blank"
					rel="noopener noreferrer">Wiktionary</a
				> (Wikimedia contributors, CC BY-SA 4.0), extracted with <a
					href="https://github.com/tatuylonen/wiktextract"
					target="_blank"
					rel="noopener noreferrer">wiktextract</a
				>. Sentences from <a
					href="https://tatoeba.org/"
					target="_blank"
					rel="noopener noreferrer">Tatoeba</a
				> (CC-BY 2.0 FR). Frequency data from <a
					href="https://github.com/rspeer/wordfreq"
					target="_blank"
					rel="noopener noreferrer">wordfreq</a
				> (MIT).
			</p>
		{:else}
			<p class="footer-data">
				Dictionary data powered by <a
					href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"
					target="_blank"
					rel="noopener noreferrer">JMdict</a
				> and <a
					href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project"
					target="_blank"
					rel="noopener noreferrer">KANJIDIC2</a
				> (EDRDG, CC BY-SA 4.0). Sentences from <a
					href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus"
					target="_blank"
					rel="noopener noreferrer">Tanaka Corpus</a
				> (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams from <a
					href="https://kanjivg.tagaini.net/"
					target="_blank"
					rel="noopener noreferrer">KanjiVG</a
				> (Ulrich Apel, CC BY-SA 3.0).
			</p>
		{/if}
	</div>
</footer>
