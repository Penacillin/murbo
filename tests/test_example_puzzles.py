"""Integration test: the example puzzles must extract-validate and solve uniquely.

These are the real puzzles produced by the pipeline. Re-solving them from scratch
(answer stripped) proves the solver finds exactly one solution, that it matches the
baked answer, and that the derived murderer is stable — i.e. the scrape/solve output
is well-formed.
"""

from __future__ import annotations

from conftest import strip_solution

from murbo.schema import validate_puzzle
from murbo.solver import derive_murderer, find_solutions


def test_example_validates(example_puzzle):
    validate_puzzle(example_puzzle)


def test_example_has_unique_solution(example_puzzle):
    raw = strip_solution(example_puzzle)
    sols = find_solutions(raw, limit=5)
    assert len(sols) == 1, f"{example_puzzle['id']} should have exactly one solution"


def test_example_matches_baked_answer(example_puzzle):
    assert "solution" in example_puzzle, "fixture should carry a baked solution"
    raw = strip_solution(example_puzzle)
    [solution] = find_solutions(raw, limit=2)

    baked = {sid: tuple(rc) for sid, rc in example_puzzle["solution"].items()}
    assert solution == baked

    murderer = derive_murderer(raw, solution)
    assert murderer == example_puzzle["murdererId"]


def test_example_victim_room_has_exactly_two(example_puzzle):
    from murbo.solver import Board

    board = Board.from_puzzle(example_puzzle)
    solution = {sid: tuple(rc) for sid, rc in example_puzzle["solution"].items()}
    victim = next(s for s in example_puzzle["suspects"] if s.get("isVictim"))
    victim_room = board.room_of.get(solution[victim["id"]])
    occupants = [c for c in solution.values() if board.room_of.get(c) == victim_room]
    assert len(occupants) == 2  # victim + murderer, nobody else
