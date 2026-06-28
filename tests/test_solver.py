"""Unit tests for the constraint solver — one minimal board per clue type."""

from __future__ import annotations

import pytest
from conftest import make_puzzle, suspect

from murbo.solver import SolveError, find_solutions, solve_and_bake

ONE_ROOM_2x2 = [{"name": "R", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]}]


def only(puzzle):
    sols = find_solutions(puzzle, limit=5)
    assert len(sols) == 1, f"expected unique, got {len(sols)}"
    return sols[0]


def test_on_object_pins_to_object_cell():
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=ONE_ROOM_2x2,
        objects=[{"type": "chair", "occupiable": True, "cell": [0, 0]}],
        suspects=[suspect("a", [{"type": "on_object", "object": "chair"}]), suspect("b", [])],
    )
    sol = only(p)
    assert sol["a"] == (0, 0)


def test_beside_object_is_blocked_by_walls():
    # shelf in room A at (0,1); only its same-room neighbour (0,0) counts as "beside".
    rooms = [{"name": "A", "cells": [[0, 0], [0, 1]]}, {"name": "B", "cells": [[1, 0], [1, 1]]}]
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=rooms,
        objects=[{"type": "shelf", "occupiable": False, "cell": [0, 1]}],
        suspects=[suspect("a", [{"type": "beside_object", "object": "shelf"}]), suspect("b", [])],
    )
    sol = only(p)
    assert sol["a"] == (0, 0)  # not (1,1): that's across a wall


def test_not_beside_object():
    rooms = [{"name": "A", "cells": [[0, 0], [0, 1], [1, 0], [1, 1]]}]
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=rooms,
        objects=[{"type": "shelf", "occupiable": False, "cell": [0, 1]}],
        suspects=[
            suspect("a", [{"type": "not_beside_object", "object": "shelf"}]),
            suspect("b", []),
        ],
    )
    for sol in find_solutions(p, limit=5):
        assert sol["a"] != (0, 0) and sol["a"] != (1, 1)  # both border the shelf


def test_in_room_and_alone_in_room():
    rooms = [{"name": "A", "cells": [[0, 0], [0, 1]]}, {"name": "B", "cells": [[1, 0], [1, 1]]}]
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=rooms,
        objects=[],
        suspects=[
            suspect("a", [{"type": "alone_in_room", "room": "A"}]),
            suspect("b", [{"type": "in_room", "room": "B"}]),
        ],
    )
    for sol in find_solutions(p, limit=5):
        assert sol["a"][0] == 0  # in A
        assert sol["b"][0] == 1  # in B (so A has only A)


def test_directional_person_constrains_only_named_axis():
    # "two rows north of": brianna.row == finlay.row - 2, columns must DIFFER (Sudoku).
    p = make_puzzle(
        rows=3,
        cols=2,
        rooms=[{"name": "R", "cells": [[r, c] for r in range(3) for c in range(2)]}],
        objects=[],
        suspects=[
            suspect("finlay", []),
            suspect(
                "brianna",
                [{"type": "directional_person", "target": "finlay", "dir": "N", "distance": 2}],
            ),
        ],
    )
    sols = find_solutions(p, limit=10)
    assert sols, "should be satisfiable"
    for sol in sols:
        assert sol["brianna"][0] == sol["finlay"][0] - 2
        assert sol["brianna"][1] != sol["finlay"][1]  # NOT same column
    # both column arrangements are valid -> proves the column axis is free
    assert len(sols) == 2


def test_object_offset():
    rooms = [{"name": "R", "cells": [[r, c] for r in range(3) for c in range(3)]}]
    p = make_puzzle(
        rows=3,
        cols=3,
        rooms=rooms,
        objects=[{"type": "bear", "occupiable": False, "cell": [0, 0]}],
        suspects=[
            suspect("f", [{"type": "object_offset", "object": "bear", "dRow": -2, "dCol": 0}]),
            suspect("g", []),
            suspect("h", []),
        ],
    )
    for sol in find_solutions(p, limit=10):
        assert sol["f"] == (2, 0)  # bear sits at (f.row-2, f.col) = (0,0)


def test_room_requires_accessory_excludes_non_wearers():
    rooms = [{"name": "A", "cells": [[0, 0], [0, 1]]}, {"name": "B", "cells": [[1, 0], [1, 1]]}]
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=rooms,
        objects=[],
        suspects=[
            suspect(
                "clark",
                [{"type": "room_requires_accessory", "room": "A", "accessory": "glasses"}],
                appearance={"glasses": True},
            ),
            suspect("bob", [], appearance={"glasses": False}),
        ],
    )
    for sol in find_solutions(p, limit=5):
        assert sol["clark"][0] == 0  # clark in A
        assert sol["bob"][0] == 1  # bob (no glasses) kept out of A


def test_out_of_bounds_cell_is_never_used():
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=[{"name": "R", "cells": [[0, 1], [1, 0], [1, 1]]}],
        objects=[],
        suspects=[suspect("a", []), suspect("b", [])],
        oob=[[0, 0]],
    )
    sols = find_solutions(p, limit=5)
    assert sols
    for sol in sols:
        assert (0, 0) not in sol.values()


def test_empty_rows_with_object_general_clue():
    rooms = [{"name": "R", "cells": [[r, c] for r in range(3) for c in range(2)]}]
    p = make_puzzle(
        rows=3,
        cols=2,
        rooms=rooms,
        objects=[{"type": "bear", "occupiable": False, "cell": [1, 0]}],
        suspects=[suspect("a", []), suspect("b", [])],
        general=[{"type": "empty_rows_with_object", "count": 1, "object": "bear"}],
    )
    for sol in find_solutions(p, limit=10):
        used_rows = {c[0] for c in sol.values()}
        assert 1 not in used_rows  # row 1 (the one with a bear) stays empty


def test_alone_with_murderer_and_derive():
    # killer + victim share the single room; the killer is pinned to the chair.
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=ONE_ROOM_2x2,
        objects=[{"type": "chair", "occupiable": True, "cell": [0, 0]}],
        suspects=[
            suspect("killer", [{"type": "on_object", "object": "chair"}]),
            suspect("victim", [{"type": "alone_with_murderer"}], victim=True),
        ],
    )
    baked = solve_and_bake(p)
    assert baked["murdererId"] == "killer"
    assert baked["solution"]["killer"] == [0, 0]
    assert baked["solution"]["victim"] == [1, 1]


def test_zero_solutions_fails_loudly():
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=ONE_ROOM_2x2,
        objects=[],  # no chair, but a clue demands one
        suspects=[
            suspect("a", [{"type": "on_object", "object": "chair"}]),
            suspect("b", [], victim=True),
        ],
    )
    with pytest.raises(SolveError):
        solve_and_bake(p)


def test_multiple_solutions_fails_loudly():
    p = make_puzzle(
        rows=2,
        cols=2,
        rooms=ONE_ROOM_2x2,
        objects=[],
        suspects=[suspect("a", []), suspect("b", [], victim=True)],
    )
    with pytest.raises(SolveError):
        solve_and_bake(p)
