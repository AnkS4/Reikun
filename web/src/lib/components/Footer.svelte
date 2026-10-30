<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
</script>

<footer class="footer">
	<div class="footer-content">
		<p class="footer-license">
			Reikun © 2026 Aniket Satbhai ·
			<a href="/about">{t('footerAbout')}</a> ·
			<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">GitHub</a> ·
			<a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">Apache-2.0</a>
		</p>
		<p class="footer-data">
			{t('footerDataBefore')}<a
				href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"
				target="_blank"
				rel="noopener noreferrer">JMdict</a
			>{t('footerDataAnd')}<a
				href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project"
				target="_blank"
				rel="noopener noreferrer">KANJIDIC2</a
			>{t('footerDataAfter')}<a
				href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus"
				target="_blank"
				rel="noopener noreferrer">Tanaka Corpus</a
			>{t('footerDataAfter2')}<a
				href="https://kanjivg.tagaini.net/"
				target="_blank"
				rel="noopener noreferrer">KanjiVG</a
			>{t('footerDataAfter3')}
		</p>
	</div>
</footer>
