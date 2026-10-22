#!/usr/bin/env python3
# LOCAL USE ONLY — personal demo-recording helper, not part of the app/CI.
# Do not commit; do not reference it from docs or other code.
#
# Records a ~25s demo of the SvelteKit app (国 example pill → Explain
# grammar → sentence parse → 店 hover tip → NL-question search) via
# Playwright's video capture, then converts the .webm to .mp4 with ffmpeg.
#
# Prereqs (not project deps): playwright browser (`uv run --with playwright
# playwright install chromium` once) and ffmpeg on PATH. The stack must
# already be running: `uv run uvicorn app.api:app` (:8000) and
# `cd web && npm run dev` (:5173).
#
# Usage:
#   uv run --with playwright python local/autorecord/record_video.py
#   uv run --with playwright python local/autorecord/record_video.py --portrait \
#       --out docs/videos/demo_v4_vertical.mp4
#   # then: python local/autorecord/video_to_gif.py docs/videos/demo_v4.mp4

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# --portrait records a native 9:16 clip for TikTok/Shorts/Reels at a true
# 1080x1920. The viewport must equal the video size: Playwright only
# downscales into record_video_size — a smaller viewport is pasted 1:1 in
# the top-left and the rest is padded grey (no upscale). zoom reflows the
# layout at a narrower CSS width so fonts stay readable on phone-size
# playback (the app column then fills the frame edge-to-edge and the page
# becomes scrollable — the wheel-scroll beat also works in portrait).
LANDSCAPE = {"viewport": (1920, 1080), "video": (1920, 1080), "zoom": 1.0}
PORTRAIT = {"viewport": (1080, 1920), "video": (1080, 1920), "zoom": 1.9}


def record(url: str, video_dir: Path, geom: dict) -> Path:
    """Drive the demo flow in a headless browser; returns the .webm path."""
    vw, vh = geom["viewport"]
    rw, rh = geom["video"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": vw, "height": vh},
            record_video_dir=str(video_dir),
            record_video_size={"width": rw, "height": rh},
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        # zoom must be set after navigation — an init script gets clobbered
        # before hydration, and a fresh page reflows once anyway.
        if geom.get("zoom", 1.0) != 1.0:
            page.evaluate(
                f"document.documentElement.style.zoom = '{geom['zoom']}'")
            # At full-bleed width the centered hover tip overflows the left
            # frame edge — anchor it to the kanji's left edge instead.
            page.add_style_tag(
                content=".kanji-tip-body { left: 0 !important; "
                        "transform: none !important; }")
            time.sleep(0.3)
        page.wait_for_selector('input[aria-label="Search"]', timeout=30000)
        page.wait_for_selector(".pill", timeout=30000)
        time.sleep(0.5)

        # Right edge, mid-height — parking here keeps the cursor off any
        # kanji-tip while results/cards render (otherwise a stray tooltip
        # opens). Lands just past the column's right edge in portrait.
        def park():
            page.mouse.move(int(vw * 0.92), int(vh * 0.48))

        box = page.locator('input[aria-label="Search"]')

        # 1. 国 example pill — commits ?q=国 → kanji card on top + results.
        page.locator(".pill", has_text="国").click()
        page.wait_for_selector(".stats-line", timeout=30000)
        park()  # the pill's spot lands inside a result once they render
        time.sleep(1.5)

        # 2. First "Explain grammar" on the first result → streamed bullets.
        #    Wheel-scroll the card under the sticky bar first — it sits below
        #    the 国 kanji card, so the stream renders off-screen otherwise.
        #    (A programmatic scrollIntoView gets canceled by the scroll that
        #    Playwright performs as part of the click; wheel deltas don't.)
        first = page.locator(".result-card").first
        dy = max(0, int(first.evaluate("el => el.getBoundingClientRect().top")) - 72)
        for _ in range(6):
            page.mouse.wheel(0, dy // 6)
            time.sleep(0.08)
        time.sleep(0.3)
        first.get_by_role("button", name="Explain grammar").first.click()
        page.wait_for_selector(".explain-out", timeout=30000)
        time.sleep(2.0)  # explanation streams in over a few seconds

        # 3. Sentence search → parsed-segment chips on top.
        #    Select-all+type, not fill("") — the input is bound to ?q=.
        box.click()
        box.press("ControlOrMeta+a")
        box.press_sequentially("あの店のサービスは素晴らしいです。", delay=90)
        time.sleep(0.5)
        page.locator("button.search-go").click()
        park()  # the input position lands on a result's kanji-tip otherwise
        page.wait_for_selector(".seg-row", timeout=30000)
        time.sleep(0.2)

        # 4. Hover 店 — its headword kanji-tip in the results — CSS tip.
        #    The wait must stay short: while the cursor is on the char the
        #    :hover tip stays open, so a long timeout holds it open the whole
        #    time (observed: tip visible ~8s when the /kanji batch was slow).
        page.locator(".kanji-tip", has_text="店").first.hover()
        try:
            page.wait_for_selector(".kanji-tip-body", state="visible", timeout=2000)
        except PlaywrightTimeoutError:
            pass  # tip data still loading — the hold below covers it
        time.sleep(1.2)
        park()
        time.sleep(0.5)

        # 5. NL question into the box → rewrite caption + チーズ on top.
        box.click()
        box.press("ControlOrMeta+a")
        box.press_sequentially("how to say cheese in japanese", delay=40)
        time.sleep(0.4)
        page.locator("button.search-go").click()
        park()  # the input position lands on a result's kanji-tip otherwise
        page.wait_for_selector(".stats-line", timeout=30000)
        time.sleep(1.0)

        ctx.close()  # video is flushed on context close
        browser.close()

    vids = sorted(video_dir.glob("*.webm"), key=lambda f: f.stat().st_mtime)
    if not vids:
        sys.exit("no .webm produced")
    return vids[-1]


def to_mp4(webm: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(webm),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
         "-movflags", "+faststart", "-an", str(out)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=5173, help="web dev server port (default: 5173)")
    ap.add_argument("--out", type=Path, default=Path("docs/videos/demo_v4.mp4"))
    ap.add_argument("--portrait", action="store_true",
                    help="record native 9:16 1080x1920 instead of 1920x1080")
    ap.add_argument("--keep-webm", action="store_true")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        webm = record(f"http://localhost:{args.port}", Path(td),
                      PORTRAIT if args.portrait else LANDSCAPE)
        to_mp4(webm, args.out)
        if args.keep_webm:
            webm.rename(args.out.with_suffix(".webm"))
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
