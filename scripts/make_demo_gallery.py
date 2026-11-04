#!/usr/bin/env python3
"""Write a deterministic synthetic demo gallery for SelectIQ walkthroughs and Playwright tests.

The images are generated labeled color cards, not participant photographs, so they are
safe to share. Identical runs produce byte-identical files, which keeps seeded demo
proposals reproducible. An ``invalid/`` folder holds a corrupt JPEG and a PNG for
exercising upload errors.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

MOMENTS = [
    "start-line", "finish-sprint", "podium", "crowd-cheer", "coach-talk", "team-huddle",
    "goal-celebration", "bench", "warmup", "trophy-lift", "fans-banner", "tunnel-walkout",
    "handshake", "sideline-reaction", "jump-header", "dive-save", "free-kick", "anthem",
    "medal-bite", "rain-delay", "timeout", "victory-lap", "press-row", "final-whistle",
    "locker-room", "kickoff", "penalty", "substitution", "scoreboard", "team-photo",
]


def write_gallery(out: Path, count: int) -> list[Path]:
    if not 1 <= count <= len(MOMENTS):
        raise SystemExit(f"--count must be between 1 and {len(MOMENTS)}.")
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.jpg"):
        stale.unlink()
    paths = []
    for index, moment in enumerate(MOMENTS[:count]):
        color = (40 + index * 11 % 200, 90 + index * 23 % 150, 120 + index * 37 % 130)
        image = Image.new("RGB", (640, 427), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle([20, 20, 620, 407], outline="white", width=4)
        draw.text((40, 190), f"{index + 1:02d}  {moment}", fill="white", font_size=40)
        path = out / f"{index + 1:02d}-{moment}.jpg"
        image.save(path, format="JPEG", quality=90)
        paths.append(path)

    invalid = out / "invalid"
    invalid.mkdir(exist_ok=True)
    (invalid / "corrupt.jpg").write_bytes(b"\xff\xd8\xff\xe0 this is not a complete JPEG")
    Image.new("RGB", (32, 32), "white").save(invalid / "notes.png", format="PNG")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="Directory to write JPEGs into")
    parser.add_argument("--count", type=int, default=18, help="Number of JPEGs (default 18)")
    args = parser.parse_args()
    paths = write_gallery(args.out, args.count)
    print(f"Wrote {len(paths)} demo JPEGs and 2 invalid files to {args.out}")


if __name__ == "__main__":
    main()
