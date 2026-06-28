"""Puzzle JSON schema + validation helpers.

The schema is intentionally strict on structure (grid, rooms, objects, suspects)
and permissive on the *internals* of typed clues — each clue is an object with a
``type`` string plus type-specific fields. The solver knows how to interpret the
clue types; the schema only guarantees the surrounding shape is well-formed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# A cell is a [row, col] pair.
_CELL = {
    "type": "array",
    "items": {"type": "integer", "minimum": 0},
    "minItems": 2,
    "maxItems": 2,
}

_CLUE = {
    "type": "object",
    "required": ["type"],
    "properties": {"type": {"type": "string"}, "raw": {"type": "string"}},
    # type-specific fields (object, room, dir, distance, …) are allowed through.
    "additionalProperties": True,
}

PUZZLE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "title", "grid", "rooms", "objects", "suspects"],
    "additionalProperties": True,
    "properties": {
        "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "title": {"type": "string"},
        "theme": {"type": "string"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "grid": {
            "type": "object",
            "required": ["rows", "cols"],
            "properties": {
                "rows": {"type": "integer", "minimum": 1},
                "cols": {"type": "integer", "minimum": 1},
            },
        },
        "rooms": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "cells"],
                "properties": {
                    "name": {"type": "string"},
                    "color": {"type": "string"},
                    "category": {"type": "string"},
                    "cells": {"type": "array", "items": _CELL},
                },
            },
        },
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "cell"],
                "properties": {
                    "type": {"type": "string"},
                    "occupiable": {"type": "boolean"},
                    "cell": _CELL,
                },
            },
        },
        "outOfBounds": {"type": "array", "items": _CELL},
        "generalClues": {"type": "array", "items": _CLUE},
        "suspects": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "name", "initial", "clues"],
                "properties": {
                    "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                    "name": {"type": "string"},
                    "initial": {"type": "string", "minLength": 1, "maxLength": 2},
                    "isVictim": {"type": "boolean"},
                    "appearance": {"type": "object"},
                    "clueRaw": {"type": "string"},
                    "clues": {"type": "array", "items": _CLUE},
                },
            },
        },
        # Added by the solver:
        "solution": {"type": "object"},
        "murdererId": {"type": "string"},
    },
}

_VALIDATOR = Draft202012Validator(PUZZLE_SCHEMA)


class PuzzleValidationError(ValueError):
    """Raised when a puzzle JSON fails structural or semantic validation."""


def validate_puzzle(puzzle: dict[str, Any]) -> None:
    """Validate structure (jsonschema) then cross-references (rooms/objects/cells).

    Raises :class:`PuzzleValidationError` with a readable message on failure.
    """
    errors = sorted(_VALIDATOR.iter_errors(puzzle), key=lambda e: e.path)
    if errors:
        msg = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors)
        raise PuzzleValidationError(msg)

    rows = puzzle["grid"]["rows"]
    cols = puzzle["grid"]["cols"]

    def in_bounds(cell: list[int]) -> bool:
        return 0 <= cell[0] < rows and 0 <= cell[1] < cols

    for room in puzzle["rooms"]:
        for cell in room["cells"]:
            if not in_bounds(cell):
                raise PuzzleValidationError(f"room '{room['name']}' has out-of-bounds cell {cell}")
    for obj in puzzle["objects"]:
        if not in_bounds(obj["cell"]):
            raise PuzzleValidationError(f"object '{obj['type']}' out of bounds at {obj['cell']}")
    for cell in puzzle.get("outOfBounds", []):
        if not in_bounds(cell):
            raise PuzzleValidationError(f"outOfBounds cell {cell} is off the grid")

    suspect_ids = [s["id"] for s in puzzle["suspects"]]
    if len(suspect_ids) != len(set(suspect_ids)):
        raise PuzzleValidationError("duplicate suspect ids")

    victims = [s for s in puzzle["suspects"] if s.get("isVictim")]
    if len(victims) != 1:
        raise PuzzleValidationError(f"expected exactly one victim, found {len(victims)}")

    n = len(suspect_ids)
    if n > rows or n > cols:
        raise PuzzleValidationError(
            f"{n} suspects cannot fit one-per-row/col on a {rows}x{cols} grid"
        )


def load_puzzle(path: str | Path, *, validate: bool = True) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    if validate:
        validate_puzzle(data)
    return data


def _compact_cells(text: str) -> str:
    """Collapse 2-integer arrays (cells / solution coords) onto a single line."""
    return re.sub(
        r"\[\s*(-?\d+),\s*(-?\d+)\s*\]",
        lambda m: f"[{m.group(1)}, {m.group(2)}]",
        text,
    )


def dump_puzzle(puzzle: dict[str, Any], path: str | Path) -> None:
    text = json.dumps(puzzle, indent=2)
    Path(path).write_text(_compact_cells(text) + "\n")
