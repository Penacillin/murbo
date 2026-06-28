"""Constraint solver for Murbo puzzles.

Model: each suspect is assigned a distinct ``(row, col)`` such that no two share a
row or a column (the Sudoku rule). Each typed clue is a predicate over the board /
assignment. We enumerate all solutions via backtracking with forward checking; a
well-formed puzzle has **exactly one**. The solver bakes ``solution`` and the derived
``murdererId`` into the puzzle, and fails loudly on 0 or >1 solutions (a signal that
extraction produced a malformed board).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

Cell = tuple[int, int]
Assignment = dict[str, Cell]


class SolveError(RuntimeError):
    """Raised when a puzzle does not have exactly one solution."""


# --------------------------------------------------------------------------- #
# Board geometry
# --------------------------------------------------------------------------- #


@dataclass
class Board:
    """Static geometry derived from the puzzle: rooms, objects, adjacency, corners."""

    rows: int
    cols: int
    room_of: dict[Cell, str]
    room_cells: dict[str, set[Cell]]
    room_category: dict[str, str]
    objects_at: dict[Cell, set[str]]
    object_cells: dict[str, set[Cell]]
    blocked: set[Cell]
    occupiable: set[Cell]

    @classmethod
    def from_puzzle(cls, puzzle: dict[str, Any]) -> Board:
        rows = puzzle["grid"]["rows"]
        cols = puzzle["grid"]["cols"]
        room_of: dict[Cell, str] = {}
        room_cells: dict[str, set[Cell]] = {}
        room_category: dict[str, str] = {}
        for room in puzzle["rooms"]:
            name = room["name"]
            room_category[name] = room.get("category", "")
            cells = {(int(r), int(c)) for r, c in room["cells"]}
            room_cells[name] = cells
            for cell in cells:
                room_of[cell] = name

        objects_at: dict[Cell, set[str]] = {}
        object_cells: dict[str, set[Cell]] = {}
        blocked: set[Cell] = set()
        for obj in puzzle["objects"]:
            cell = (int(obj["cell"][0]), int(obj["cell"][1]))
            typ = obj["type"]
            objects_at.setdefault(cell, set()).add(typ)
            object_cells.setdefault(typ, set()).add(cell)
            if not obj.get("occupiable", True):
                blocked.add(cell)

        # Cells outside the (possibly non-rectangular) playable board: never occupiable.
        oob = {(int(r), int(c)) for r, c in puzzle.get("outOfBounds", [])}
        all_cells = {(r, c) for r in range(rows) for c in range(cols)}
        occupiable = all_cells - blocked - oob
        return cls(
            rows=rows,
            cols=cols,
            room_of=room_of,
            room_cells=room_cells,
            room_category=room_category,
            objects_at=objects_at,
            object_cells=object_cells,
            blocked=blocked,
            occupiable=occupiable,
        )

    def neighbors_same_room(self, cell: Cell) -> list[Cell]:
        """Orthogonal neighbours in the *same room* (walls block 'beside')."""
        r, c = cell
        room = self.room_of.get(cell)
        out = []
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < self.rows and 0 <= nc < self.cols and self.room_of.get((nr, nc)) == room:
                out.append((nr, nc))
        return out

    def neighbors_ortho(self, cell: Cell) -> list[Cell]:
        r, c = cell
        return [
            (nr, nc)
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= nr < self.rows and 0 <= nc < self.cols
        ]

    def is_corner_of(self, cell: Cell, room: str) -> bool:
        """A corner cell: inside the room with >=2 of its 4 sides outside the room."""
        if self.room_of.get(cell) != room:
            return False
        r, c = cell
        outside = 0
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if (
                not (0 <= nr < self.rows and 0 <= nc < self.cols)
                or self.room_of.get((nr, nc)) != room
            ):
                outside += 1
        return outside >= 2

    def rooms_in_category(self, category: str) -> list[str]:
        return [name for name, cat in self.room_category.items() if cat == category]


# --------------------------------------------------------------------------- #
# Clue interpretation
# --------------------------------------------------------------------------- #

_DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


def _has_accessory(suspect: dict[str, Any], accessory: str) -> bool:
    return bool(suspect.get("appearance", {}).get(accessory))


def _row_value(spec: Any, board: Board) -> int:
    if spec == "top":
        return 0
    if spec == "bottom":
        return board.rows - 1
    return int(spec)


def unary_ok(clue: dict[str, Any], cell: Cell, suspect: dict[str, Any], board: Board) -> bool:
    """Check a clue that depends only on the suspect's own cell.

    Relational clues (directional_person) and whole-board clues (alone_in_room,
    room_min_people, …) always return ``True`` here and are validated later.
    """
    t = clue["type"]
    r, c = cell

    if t == "on_object":
        return clue["object"] in board.objects_at.get(cell, set())
    if t == "beside_object":
        obj = clue["object"]
        return any(obj in board.objects_at.get(n, set()) for n in board.neighbors_same_room(cell))
    if t == "not_beside_object":
        obj = clue["object"]
        return not any(
            obj in board.objects_at.get(n, set()) for n in board.neighbors_same_room(cell)
        )
    if t == "in_room":
        return board.room_of.get(cell) == clue["room"]
    if t == "alone_in_room":
        # Unary part: the suspect must be inside the room (population checked later).
        return board.room_of.get(cell) == clue["room"]
    if t == "in_row":
        return r == _row_value(clue["row"], board)
    if t == "in_column":
        return c == int(clue["col"])
    if t == "corner":
        return board.is_corner_of(cell, clue["room"])
    if t == "not_corner":
        rooms = (
            board.rooms_in_category(clue["category"]) if clue.get("category") else [clue["room"]]
        )
        return not any(board.is_corner_of(cell, room) for room in rooms)
    if t == "beside_room":
        room = clue["room"]
        return any(board.room_of.get(n) == room for n in board.neighbors_ortho(cell))
    if t == "object_offset":
        obj = clue["object"]
        d_row = clue.get("dRow")
        d_col = clue.get("dCol")
        for orow, ocol in board.object_cells.get(obj, set()):
            if (d_row is None or orow == r + d_row) and (d_col is None or ocol == c + d_col):
                return True
        return False
    if t == "room_requires_accessory":
        # Self part: suspect is in the room AND wears the accessory.
        return board.room_of.get(cell) == clue["room"] and _has_accessory(
            suspect, clue["accessory"]
        )
    if t == "either_or":
        return any(unary_ok(sub, cell, suspect, board) for sub in clue["options"])

    # Relational / board-level clues are not unary.
    return True


# --------------------------------------------------------------------------- #
# Solver
# --------------------------------------------------------------------------- #


@dataclass
class _Suspect:
    id: str
    raw: dict[str, Any]
    is_victim: bool
    domain: list[Cell] = field(default_factory=list)


def _build_domains(puzzle: dict[str, Any], board: Board) -> list[_Suspect]:
    suspects = [
        _Suspect(id=s["id"], raw=s, is_victim=bool(s.get("isVictim"))) for s in puzzle["suspects"]
    ]

    # Global accessory restrictions: any room that requires an accessory excludes
    # suspects lacking it, regardless of whose clue introduced the requirement.
    required: dict[str, set[str]] = {}
    for s in puzzle["suspects"]:
        for clue in s["clues"]:
            if clue["type"] == "room_requires_accessory":
                required.setdefault(clue["room"], set()).add(clue["accessory"])

    for sus in suspects:
        cells = []
        for cell in board.occupiable:
            if not all(unary_ok(clue, cell, sus.raw, board) for clue in sus.raw["clues"]):
                continue
            room = board.room_of.get(cell)
            if room in required and not all(_has_accessory(sus.raw, acc) for acc in required[room]):
                continue
            cells.append(cell)
        sus.domain = sorted(cells)
    return suspects


def _board_constraints_ok(puzzle: dict[str, Any], board: Board, assign: Assignment) -> bool:
    """Validate clues that need the full assignment."""
    by_cell = {cell: sid for sid, cell in assign.items()}
    used_rows = {cell[0] for cell in assign.values()}

    def room_population(room: str) -> int:
        return sum(1 for cell in assign.values() if board.room_of.get(cell) == room)

    # Per-suspect relational / room clues.
    for s in puzzle["suspects"]:
        cell = assign[s["id"]]
        for clue in s["clues"]:
            t = clue["type"]
            if t == "directional_person":
                # Person-to-person clues constrain only the named axis; the
                # perpendicular axis must differ anyway (one suspect per row/col).
                tgt = assign[clue["target"]]
                d = int(clue.get("distance", 1))
                dr, dc = _DIRS[clue["dir"]]
                if dr and cell[0] != tgt[0] + dr * d:
                    return False
                if dc and cell[1] != tgt[1] + dc * d:
                    return False
            elif t == "alone_in_room":
                if room_population(clue["room"]) != 1:
                    return False
            elif t == "room_min_people":
                if room_population(clue["room"]) < int(clue["count"]):
                    return False
            elif t == "room_min_people_self":
                room = board.room_of.get(cell)
                if room is None or room_population(room) < int(clue["count"]):
                    return False
            elif t == "only_object":
                obj = clue["object"]
                for sid2, cell2 in assign.items():
                    if sid2 != s["id"] and obj in board.objects_at.get(cell2, set()):
                        return False
            elif t == "alone_with_murderer":
                if room_population(board.room_of.get(cell, "")) != 2:
                    return False

    # room_requires_accessory: every occupant of the room wears the accessory.
    for s in puzzle["suspects"]:
        for clue in s["clues"]:
            if clue["type"] == "room_requires_accessory":
                room, acc = clue["room"], clue["accessory"]
                for cell in board.room_cells.get(room, set()):
                    sid = by_cell.get(cell)
                    if sid is not None:
                        occ = next(x for x in puzzle["suspects"] if x["id"] == sid)
                        if not _has_accessory(occ, acc):
                            return False

    # General clues.
    for clue in puzzle.get("generalClues", []):
        t = clue["type"]
        if t == "empty_rows_with_object":
            empty_rows = [r for r in range(board.rows) if r not in used_rows]
            if len(empty_rows) != int(clue["count"]):
                return False
            obj = clue["object"]
            for r in empty_rows:
                if not any(orow == r for orow, _ in board.object_cells.get(obj, set())):
                    return False
        elif t == "room_min_people":
            if room_population(clue["room"]) < int(clue["count"]):
                return False
        elif t == "room_min_people_each_category":
            for room in board.rooms_in_category(clue["category"]):
                if room_population(room) < int(clue["count"]):
                    return False

    return True


def find_solutions(puzzle: dict[str, Any], *, limit: int = 2) -> list[Assignment]:
    """Return up to ``limit`` complete solutions."""
    board = Board.from_puzzle(puzzle)
    suspects = _build_domains(puzzle, board)
    # Most-constrained-first ordering speeds up search and early failure.
    order = sorted(range(len(suspects)), key=lambda i: len(suspects[i].domain))

    # Precompute directional links for incremental pruning.
    id_to_idx = {s.id: i for i, s in enumerate(suspects)}
    links: dict[int, list[tuple[int, int, int]]] = {}  # idx -> (target_idx, dr*d, dc*d)
    for i, s in enumerate(suspects):
        for clue in s.raw["clues"]:
            if clue["type"] == "directional_person":
                d = int(clue.get("distance", 1))
                dr, dc = _DIRS[clue["dir"]]
                links.setdefault(i, []).append((id_to_idx[clue["target"]], dr * d, dc * d))

    solutions: list[Assignment] = []
    used_rows: set[int] = set()
    used_cols: set[int] = set()
    placed: dict[int, Cell] = {}

    def link_ok(cell: Cell, tcell: Cell, dr: int, dc: int) -> bool:
        # axis-only: only the moved axis is pinned (see _board_constraints_ok)
        if dr and cell[0] != tcell[0] + dr:
            return False
        return not (dc and cell[1] != tcell[1] + dc)

    def consistent(idx: int, cell: Cell) -> bool:
        for tgt, dr, dc in links.get(idx, ()):
            if tgt in placed and not link_ok(cell, placed[tgt], dr, dc):
                return False
        # Reverse links: if a previously placed suspect points at this one.
        for j, cl in links.items():
            if j in placed:
                for tgt, dr, dc in cl:
                    if tgt == idx and not link_ok(placed[j], cell, dr, dc):
                        return False
        return True

    def backtrack(k: int) -> None:
        if len(solutions) >= limit:
            return
        if k == len(order):
            assign = {suspects[i].id: placed[i] for i in placed}
            if _board_constraints_ok(puzzle, board, assign):
                solutions.append(assign)
            return
        idx = order[k]
        for cell in suspects[idx].domain:
            if cell[0] in used_rows or cell[1] in used_cols:
                continue
            if not consistent(idx, cell):
                continue
            placed[idx] = cell
            used_rows.add(cell[0])
            used_cols.add(cell[1])
            backtrack(k + 1)
            del placed[idx]
            used_rows.discard(cell[0])
            used_cols.discard(cell[1])
            if len(solutions) >= limit:
                return

    backtrack(0)
    return solutions


def derive_murderer(puzzle: dict[str, Any], assign: Assignment) -> str:
    """The non-victim sharing the victim's room is the murderer."""
    board = Board.from_puzzle(puzzle)
    victim = next(s for s in puzzle["suspects"] if s.get("isVictim"))
    victim_room = board.room_of.get(assign[victim["id"]])
    sharers = [
        sid
        for sid, cell in assign.items()
        if sid != victim["id"] and board.room_of.get(cell) == victim_room
    ]
    if len(sharers) != 1:
        raise SolveError(
            f"victim's room '{victim_room}' must contain exactly the victim + murderer, "
            f"found {len(sharers)} other suspect(s)"
        )
    return sharers[0]


def solve_and_bake(puzzle: dict[str, Any]) -> dict[str, Any]:
    """Solve, assert uniqueness, and bake ``solution`` + ``murdererId`` into the puzzle."""
    sols = find_solutions(puzzle, limit=2)
    if len(sols) == 0:
        raise SolveError("no solution — the extracted board is over-constrained or malformed")
    if len(sols) > 1:
        raise SolveError(
            f"{len(sols)}+ solutions — the puzzle is under-constrained (extraction likely "
            "missed a clue or an object/room boundary)"
        )
    solution = sols[0]
    murderer = derive_murderer(puzzle, solution)
    puzzle = dict(puzzle)
    puzzle["solution"] = {sid: [r, c] for sid, (r, c) in solution.items()}
    puzzle["murdererId"] = murderer
    return puzzle


def summarize(puzzle: dict[str, Any], assign: Assignment) -> str:
    board = Board.from_puzzle(puzzle)
    lines = []
    for s in puzzle["suspects"]:
        r, c = assign[s["id"]]
        room = board.room_of.get((r, c), "?")
        tag = " (VICTIM)" if s.get("isVictim") else ""
        lines.append(f"  {s['name']:<10} -> r{r} c{c}  [{room}]{tag}")
    return "\n".join(lines)


def cells_iter(rows: int, cols: int) -> Iterable[Cell]:
    for r in range(rows):
        for c in range(cols):
            yield (r, c)
