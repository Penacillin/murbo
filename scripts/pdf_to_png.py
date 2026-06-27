#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf"]
# ///

import argparse
from pathlib import Path

import fitz  # pymupdf


def pdf_to_png(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    doc = fitz.open(pdf_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for i, page in enumerate(doc):
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        out = output_dir / f"{pdf_path.stem}_p{i + 1}.png"
        pix.save(out)
        outputs.append(out)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert PDF pages to PNG images')
    parser.add_argument('input', nargs='+', help='Input PDF file(s)')
    parser.add_argument('-o', '--output-dir', default='.', help='Output directory (default: current dir)')
    parser.add_argument('--dpi', type=int, default=150, help='Resolution in DPI (default: 150)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    for pdf in args.input:
        pages = pdf_to_png(Path(pdf), output_dir, dpi=args.dpi)
        for p in pages:
            print(p)


if __name__ == '__main__':
    main()
