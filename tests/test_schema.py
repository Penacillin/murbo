"""Schema validation: well-formed puzzles pass, malformed ones fail loudly."""

from __future__ import annotations

import copy

import pytest

from murbo.schema import PuzzleValidationError, validate_puzzle

VALID = {
    "id": "demo",
    "title": "Demo",
    "difficulty": "easy",
    "grid": {"rows": 2, "cols": 2},
    "rooms": [{"name": "R", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]}],
    "objects": [{"type": "chair", "occupiable": True, "cell": [0, 0]}],
    "suspects": [
        {"id": "a", "name": "A", "initial": "A", "clues": []},
        {"id": "v", "name": "V", "initial": "V", "isVictim": True, "clues": []},
    ],
}


def test_valid_puzzle_passes():
    validate_puzzle(copy.deepcopy(VALID))


def test_requires_exactly_one_victim():
    p = copy.deepcopy(VALID)
    p["suspects"][1]["isVictim"] = False
    with pytest.raises(PuzzleValidationError, match="victim"):
        validate_puzzle(p)


def test_rejects_duplicate_suspect_ids():
    p = copy.deepcopy(VALID)
    p["suspects"][1]["id"] = "a"
    with pytest.raises(PuzzleValidationError, match="duplicate"):
        validate_puzzle(p)


def test_rejects_out_of_bounds_room_cell():
    p = copy.deepcopy(VALID)
    p["rooms"][0]["cells"].append([9, 9])
    with pytest.raises(PuzzleValidationError, match="out-of-bounds"):
        validate_puzzle(p)


def test_rejects_too_many_suspects_for_grid():
    p = copy.deepcopy(VALID)
    p["suspects"].extend(
        {"id": f"x{i}", "name": "X", "initial": "X", "clues": []} for i in range(3)
    )
    with pytest.raises(PuzzleValidationError, match="cannot fit"):
        validate_puzzle(p)


def test_rejects_off_grid_out_of_bounds():
    p = copy.deepcopy(VALID)
    p["outOfBounds"] = [[5, 5]]
    with pytest.raises(PuzzleValidationError, match="off the grid"):
        validate_puzzle(p)


def test_rejects_bad_structure():
    with pytest.raises(PuzzleValidationError):
        validate_puzzle({"id": "x"})  # missing grid/rooms/objects/suspects
