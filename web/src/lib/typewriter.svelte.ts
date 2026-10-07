// Looping typewriter: types a phrase, holds, backspaces it away, moves on.
// Returns reactive { text } — bind it to an input placeholder or render it.
// `phrases` is a getter so callers can stop the loop reactively (return []).
const prefersReducedMotion = typeof window !== 'undefined'
	? matchMedia('(prefers-reduced-motion: reduce)')
	: null;

export function typewriter(phrases: () => readonly string[], typeMs = 55, holdMs = 1800) {
	let text = $state('');

	$effect(() => {
		const list = phrases().filter(Boolean);
		if (!list.length) return;
		if (prefersReducedMotion?.matches) {
			text = list[0];
			return;
		}
		let i = 0,
			pos = 0,
			dir = 1;
		let t: ReturnType<typeof setTimeout>;
		const tick = () => {
			const p = list[i];
			const chars = Array.from(p);
			pos += dir;
			text = chars.slice(0, pos).join('');
			if (pos === chars.length) {
				dir = -1;
				t = setTimeout(tick, holdMs);
			} else if (pos === 0) {
				dir = 1;
				i = (i + 1) % list.length;
				t = setTimeout(tick, 400);
			} else {
				t = setTimeout(tick, dir === 1 ? typeMs : 30);
			}
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
