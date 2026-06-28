"""Murbo command-line interface — one CLI, four subcommands.

murbo extract <image.png> [--provider claude|minimax|openai] [--model ...] [-o OUT]
murbo solve   <puzzle.json> [--in-place]
murbo build-manifest
murbo serve   [--host H] [--port P]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from murbo import __version__

# Default location of baked puzzles served by the web UI.
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
PUZZLES_DIR = WEB_DIR / "puzzles"


def _cmd_extract(args: argparse.Namespace) -> int:
    from murbo.env import load_dotenv
    from murbo.extract import extract_puzzle

    load_dotenv()  # pick up API keys from a local .env (cross-platform; real env wins)

    out = Path(args.output) if args.output else PUZZLES_DIR / f"{Path(args.image).stem}.json"
    puzzle = extract_puzzle(
        args.image, provider=args.provider, model=args.model, review=args.review
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    from murbo.schema import dump_puzzle, validate_puzzle

    validate_puzzle(puzzle)
    dump_puzzle(puzzle, out)
    print(f"extracted -> {out}")
    print("  next: murbo solve", out)
    return 0


def _cmd_solve(args: argparse.Namespace) -> int:
    from murbo.schema import dump_puzzle, load_puzzle
    from murbo.solver import SolveError, find_solutions, solve_and_bake, summarize

    path = Path(args.puzzle)
    puzzle = load_puzzle(path)
    try:
        baked = solve_and_bake(puzzle)
    except SolveError as exc:
        print(f"✗ {path.name}: {exc}", file=sys.stderr)
        # Show how many solutions were found, to aid debugging.
        sols = find_solutions(puzzle, limit=3)
        print(f"  (solver found {len(sols)} solution(s))", file=sys.stderr)
        for i, s in enumerate(sols[:2]):
            print(f"  solution {i + 1}:\n{summarize(puzzle, s)}", file=sys.stderr)
        return 1

    murderer = next(s for s in baked["suspects"] if s["id"] == baked["murdererId"])
    sol = {sid: tuple(rc) for sid, rc in baked["solution"].items()}
    print(f"✓ {path.name}: unique solution found")
    print(summarize(baked, sol))
    print(f"\n  murderer: {murderer['name']}")

    out = path if args.in_place else path
    dump_puzzle(baked, out)
    print(f"  baked solution -> {out}")
    return 0


def _cmd_build_manifest(args: argparse.Namespace) -> int:
    from murbo.manifest import build_manifest

    manifest = build_manifest(PUZZLES_DIR)
    n = len(manifest["puzzles"])
    print(f"wrote manifest with {n} puzzle(s) -> {PUZZLES_DIR / 'manifest.json'}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from murbo.serve import serve

    serve(WEB_DIR, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="murbo", description=__doc__)
    parser.add_argument("--version", action="version", version=f"murbo {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ex = sub.add_parser("extract", help="PNG -> structured puzzle JSON (LLM vision)")
    p_ex.add_argument("image", help="input PNG (may be blurry/warped)")
    p_ex.add_argument("--provider", choices=["claude", "minimax", "openai"], default="claude")
    p_ex.add_argument("--model", default=None, help="override the provider's default model")
    p_ex.add_argument("-o", "--output", default=None, help="output JSON path")
    p_ex.add_argument("--review", action="store_true", help="run a second self-correction pass")
    p_ex.set_defaults(func=_cmd_extract)

    p_so = sub.add_parser("solve", help="solve, assert uniqueness, bake solution + murderer")
    p_so.add_argument("puzzle", help="puzzle JSON path")
    p_so.add_argument("--in-place", action="store_true", help="(default) write back to same file")
    p_so.set_defaults(func=_cmd_solve)

    p_bm = sub.add_parser("build-manifest", help="scan web/puzzles/*.json -> manifest.json")
    p_bm.set_defaults(func=_cmd_build_manifest)

    p_sv = sub.add_parser("serve", help="serve web/ + GET /api/puzzles auto-listing")
    p_sv.add_argument("--host", default="localhost")
    p_sv.add_argument("--port", type=int, default=8000)
    p_sv.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
