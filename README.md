# Murbo

Murder-mystery × Sudoku puzzles (per `stripped-game-guide.md`). Drop in a (possibly
blurry) PNG → the system parses it into clean structured puzzle data → a polished native
web UI lets you play it from a gallery.

```
PNG → extract (LLM vision) → structured JSON → solve (constraint solver) → baked puzzle → native UI
```

The source image is **input only** — the game renders its own faithful flat-vector UI from
the clean data, and the answer used to grade the player comes from a **constraint solver**
over typed clues (never trusted to the model). The solver also proves each puzzle is
well-formed by asserting a **unique** solution.

## Setup

Everything is `uv`-managed. No manual venv/pip.

```bash
uv sync
```

## CLI (`murbo`)

```bash
# PNG -> structured puzzle JSON via an LLM vision provider (needs an API key)
uv run murbo extract input-puzzles/processed/car-repair-color_p1.png \
    --provider claude -o web/puzzles/car-repair.json   # or --provider minimax | openai
uv run murbo extract <png> --provider claude --review     # optional 2nd self-correction pass

# Solve: assert a unique solution and bake `solution` + `murdererId` into the JSON.
# Fails loudly on 0 or >1 solutions (a signal that extraction was malformed).
uv run murbo solve web/puzzles/car-repair.json

# Static fallback manifest for plain file hosting (serve auto-lists without it).
uv run murbo build-manifest

# Play: serves web/ at http://localhost:8000 with GET /api/puzzles auto-listing.
uv run murbo serve
```

Vision providers (`src/murbo/providers.py`): Claude (`ANTHROPIC_API_KEY`), MiniMax
(`MINIMAX_API_KEY`, Anthropic-compatible — default model `MiniMax-M3`), and OpenAI
(`OPENAI_API_KEY`), behind one interface. The extraction prompt
(`src/murbo/prompts/extract_guide.md`) carries the game-guide vocabulary so the model emits
the typed, solver-checkable clues.

Keys are read from the environment. Copy `.env.example` to `.env` and fill in whichever
provider you use (`.env` is git-ignored). `murbo extract` **auto-loads `.env`** from the
working directory on any OS — no shell setup needed. (Real environment variables still take
precedence, so you can also just export the key directly:
`export ANTHROPIC_API_KEY=...` on macOS/Linux, `$Env:ANTHROPIC_API_KEY="..."` in PowerShell.)

## Layout

```
src/murbo/        the pipeline package (one CLI, subcommands)
  cli.py          extract | solve | build-manifest | serve
  schema.py       puzzle JSON schema + validation
  providers.py    Claude + OpenAI vision backends
  extract.py      PNG -> structured puzzle JSON
  solver.py       backtracking constraint solver; bakes the unique solution + murderer
  manifest.py     scan web/puzzles/*.json -> manifest.json
  serve.py        static server + /api/puzzles
web/              static frontend (no build step): gallery + game, procedural SVG avatars/icons
  puzzles/        extracted + solved puzzle JSON
input-puzzles/    drop-in source images (unchanged)
```

## Typed clue vocabulary

`on_object` · `beside_object` / `not_beside_object` · `in_room` · `alone_in_room` ·
`in_row` (incl. `top`/`bottom`) · `in_column` · `directional_person` {target,dir,distance} ·
`object_offset` {object,dRow,dCol} · `room_requires_accessory` · `room_min_people_self` ·
`corner` / `not_corner` · `beside_room` · `either_or` · `alone_with_murderer` (victim).
General: `empty_rows_with_object`, `room_min_people`.

Note on **directional person clues** ("two rows north of X"): only the named axis is
constrained — the perpendicular axis must differ anyway, since two suspects can never share
a row or column. (The guide's "same column" phrasing applies to object clues.)

## Tests

```bash
uv run pytest
```

`tests/` covers the solver (a minimal board per clue type), schema validation, and the
extraction plumbing (JSON parsing + provider abstraction, no API key needed). It also keeps
its own copy of example puzzles under `tests/fixtures/puzzles/` as integration fixtures —
each is re-solved from scratch to prove the pipeline still yields the same unique solution
and murderer. (These are independent of `web/puzzles/`, so the app gallery can be changed
freely without touching the tests.)
