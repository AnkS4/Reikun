#!/usr/bin/env python3
# LOCAL USE ONLY — personal demo-recording helper, not part of the app/CI.
# Do not commit; do not reference it from docs or other code.
#
# Converts a recorded .mp4 to a GIF played back at 1.5x speed
# (setpts=0.5*PTS), 15 fps, 960px wide, using ffmpeg's two-pass
# palette workflow for decent quality. Crops --trim seconds off
# each end (default 2 — cuts the page-load head and dead tail).
#
# Usage:
#   python scripts/autorecord/video_to_gif.py docs/videos/demo_v2.mp4
#   python scripts/autorecord/video_to_gif.py docs/videos/demo_v2.mp4 \
#       -o docs/videos/demo_v2.gif --speed 2 --fps 15 --trim 2

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def duration_of(src: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(src)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path, help="input video (mp4/webm)")
    ap.add_argument("-o", "--out", type=Path, help="output .gif (default: <src>.gif)")
    ap.add_argument("--speed", type=float, default=1.5, help="playback speed multiplier (default: 1.5x)")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--width", type=int, default=960, help="output width in px; height auto")
    ap.add_argument("--crop", type=str, default=None, metavar="WxH+X+Y",
                    help="crop region before scaling — for the 9:16 vertical video,"
                         " 974x1732+0+16 keeps the full card column + hover tips and"
                         " drops the dead tail (content ends ~y1477 of 1920)")
    ap.add_argument("--trim", type=float, default=2.0,
                    help="seconds cropped from EACH end (default: 2; 0 disables)")
    args = ap.parse_args()

    out = args.out or args.src.with_suffix(".gif")
    keep = duration_of(args.src) - 2 * args.trim
    if keep <= 0:
        sys.exit(f"trim {args.trim}sx2 exceeds the {duration_of(args.src):.1f}s video")
    cut = ["-ss", str(args.trim), "-t", str(keep)] if args.trim else []
    speed = f"setpts={1 / args.speed:.4f}*PTS"
    crop = ""
    if args.crop:
        m = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", args.crop)
        if not m:
            sys.exit(f"--crop expects WxH+X+Y, got {args.crop!r}")
        crop = f"crop={m[1]}:{m[2]}:{m[3]}:{m[4]},"
    vf = f"{crop}{speed},fps={args.fps},scale={args.width}:-1:flags=lanczos"

    with tempfile.TemporaryDirectory() as td:
        palette = Path(td) / "palette.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", *cut, "-i", str(args.src),
                        "-vf", f"{vf},palettegen", str(palette)], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", *cut, "-i", str(args.src), "-i", str(palette),
                        "-lavfi", f"{vf} [x]; [x][1:v] paletteuse", str(out)], check=True)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
