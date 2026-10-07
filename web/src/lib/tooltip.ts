/**
 * Edge clamp for centre-anchored tooltips: sets --tip-shift on the anchor
 * so `translateX(calc(-50% + var(--tip-shift)))` keeps the tip inside the
 * viewport. The tip element is display:none until shown and can't be
 * measured — the shift is computed from the anchor rect and --tip-w,
 * treating the tip as its max width (tips narrower than that just sit
 * slightly off-centre, never clipped).
 */
const MARGIN = 8;

export function clampTip(node: HTMLElement) {
	function set() {
		const rect = node.getBoundingClientRect();
		const tipW = parseFloat(getComputedStyle(node).getPropertyValue('--tip-w')) || 290;
		const vw = document.documentElement.clientWidth;
		const half = Math.min(tipW, vw - MARGIN * 2) / 2;
		const cx = rect.left + rect.width / 2;
		const shift = Math.min(Math.max(cx, MARGIN + half), vw - MARGIN - half) - cx;
		node.style.setProperty('--tip-shift', `${shift.toFixed(1)}px`);
		// Vertical: when the sticky search bar is pinned to the viewport top
		// and the anchor is tucked under it, push the tip below the bar so
		// it doesn't render behind the translucent strip. Header bar items
		// sit above the search bar and render naturally with higher z-index.
		let dy = 0;
		if (!node.closest('.header-bar')) {
			const bar = document.querySelector('.search-row')?.getBoundingClientRect();
			if (bar && bar.top <= 1 && rect.top < bar.bottom) {
				dy = Math.max(0, bar.bottom + 4 - (rect.bottom + 6));
			}
		}
		node.style.setProperty('--tip-dy', `${dy.toFixed(1)}px`);
	}
	// pointerenter covers desktop hover; pointerdown/focusin cover tap/touch
	node.addEventListener('pointerenter', set);
	node.addEventListener('pointerdown', set);
	node.addEventListener('focusin', set);
	return {
		destroy() {
			node.removeEventListener('pointerenter', set);
			node.removeEventListener('pointerdown', set);
			node.removeEventListener('focusin', set);
		}
	};
}
