// Looping typewriter: types a phrase, holds, vanishes, moves to the next.
// Returns reactive { text } — bind it to an input placeholder or render it.
export function typewriter(phrases: string[], typeMs = 55, holdMs = 1800) {
	let text = $state('');

	$effect(() => {
		if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
			text = phrases[0];
			return;
		}
		let i = 0,
			pos = 0;
		let t: ReturnType<typeof setTimeout>;
		const tick = () => {
			const p = phrases[i];
			if (pos === p.length) {
				// Held long enough — vanish, then start the next phrase.
				pos = 0;
				text = '';
				i = (i + 1) % phrases.length;
				t = setTimeout(tick, 350);
				return;
			}
			pos += 1;
			text = p.slice(0, pos);
			t = setTimeout(tick, pos === p.length ? holdMs : typeMs);
		};
		t = setTimeout(tick, 350);
		return () => clearTimeout(t);
	});

	return {
		get text() {
			return text;
		}
	};
}
