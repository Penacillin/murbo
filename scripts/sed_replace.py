#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import argparse
import re

SED_PATTERN = 's/Murdoku/Murbo/gi'


def parse_sed_pattern(pattern: str) -> tuple[str, str, str]:
    parts = pattern.split(pattern[1])
    if len(parts) != 4 or parts[0] != 's':
        raise ValueError(f"Invalid sed pattern: {pattern!r}")
    _, search, replace, flags = parts
    return search, replace, flags


def apply(text: str, search: str, replace: str, flags: str) -> str:
    re_flags = re.IGNORECASE if 'i' in flags else 0
    count = 0 if 'g' in flags else 1
    return re.sub(search, replace, text, count=count, flags=re_flags)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input file')
    parser.add_argument('-o', '--output', help='Output file (default: overwrite input)')
    args = parser.parse_args()

    search, replace, flags = parse_sed_pattern(SED_PATTERN)

    with open(args.input, encoding='utf-8') as f:
        content = f.read()

    result = apply(content, search, replace, flags)

    out_path = args.output or args.input
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(result)


if __name__ == '__main__':
    main()
