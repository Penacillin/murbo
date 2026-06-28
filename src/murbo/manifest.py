"""Build a static ``manifest.json`` listing all solved puzzles in ``web/puzzles``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def puzzle_summary(puzzle: dict[str, Any]) -> dict[str, Any]:
    """The lightweight record the gallery needs (no clues/solution leakage needed,
    but solution stays in the per-puzzle file, not the manifest)."""
    return {
        "id": puzzle["id"],
        "title": puzzle["title"],
        "theme": puzzle.get("theme", ""),
        "difficulty": puzzle.get("difficulty", "medium"),
        "grid": puzzle["grid"],
        "suspectCount": len(puzzle["suspects"]),
        "solved": "solution" in puzzle,
        "file": f"puzzles/{puzzle['id']}.json",
    }


def build_manifest(puzzles_dir: str | Path) -> dict[str, Any]:
    puzzles_dir = Path(puzzles_dir)
    summaries = []
    for path in sorted(puzzles_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            puzzle = json.loads(path.read_text())
            summaries.append(puzzle_summary(puzzle))
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"  skipping {path.name}: {exc}")
    manifest = {"puzzles": summaries}
    (puzzles_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
