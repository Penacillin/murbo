"""Shared test helpers.

The two example puzzles double as **integration fixtures**: the tests load the
solved JSON the pipeline produced, strip the baked answer, and re-solve to prove
the solver still finds the same unique solution and murderer.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

# The integration fixtures own their own copy of the puzzles, so the app gallery
# (web/puzzles) can be added to / cleared without affecting the test suite.
FIXTURE_PUZZLE_DIR = Path(__file__).resolve().parent / "fixtures" / "puzzles"


def example_puzzle_files() -> list[Path]:
    return sorted(FIXTURE_PUZZLE_DIR.glob("*.json"))


def strip_solution(puzzle: dict) -> dict:
    """Return a copy with the baked answer removed, as if freshly extracted."""
    p = copy.deepcopy(puzzle)
    p.pop("solution", None)
    p.pop("murdererId", None)
    return p


def make_puzzle(*, rows, cols, rooms, objects, suspects, general=None, oob=None) -> dict:
    """Build a minimal puzzle dict for solver unit tests."""
    p = {
        "id": "t",
        "title": "T",
        "grid": {"rows": rows, "cols": cols},
        "rooms": rooms,
        "objects": objects,
        "generalClues": general or [],
        "suspects": suspects,
    }
    if oob:
        p["outOfBounds"] = oob
    return p


def suspect(sid, clues, *, victim=False, appearance=None):
    s = {
        "id": sid,
        "name": sid.capitalize(),
        "initial": sid[0].upper(),
        "clues": clues,
        "appearance": appearance or {},
    }
    if victim:
        s["isVictim"] = True
    return s


@pytest.fixture(params=example_puzzle_files(), ids=lambda p: p.stem)
def example_puzzle(request):
    import json

    return json.loads(request.param.read_text())
