#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

TOP_LEFT_W = 450
TOP_LEFT_H = 200

BOTTOM_RIGHT_W = 550
BOTTOM_RIGHT_H = 130


def whiteout(img_path: Path, output_path: Path) -> None:
    img = Image.open(img_path).convert('RGB')
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, TOP_LEFT_W, TOP_LEFT_H], fill='white')

    w, h = img.size
    draw.rectangle([w - BOTTOM_RIGHT_W, h - BOTTOM_RIGHT_H, w, h], fill='white')

    img.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description='White out top-left and bottom-right corners of PNG images')
    parser.add_argument('input', nargs='+', help='Input PNG file(s)')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: overwrite input)')
    args = parser.parse_args()

    for inp in args.input:
        src = Path(inp)
        dst = Path(args.output_dir) / src.name if args.output_dir else src
        if args.output_dir:
            Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        whiteout(src, dst)
        print(dst)


if __name__ == '__main__':
    main()
