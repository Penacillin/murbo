"""PNG → structured puzzle JSON via an LLM vision provider.

The image is *input only*; the model reasons about it (handling blur/warp) and emits the
clean typed puzzle. The result is validated against the schema by the caller, then handed
to the solver to bake the answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from murbo.providers import get_provider

_PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_guide.md"

_INSTRUCTION = (
    "Extract this Murbo puzzle sheet into the structured JSON described in your instructions. "
    "Reason carefully about the grid lines, room walls and colours, every object cell, and "
    "each suspect's portrait accessories. Emit ONLY the JSON object."
)

_REVIEW_INSTRUCTION = (
    "Here is structured JSON you produced for this puzzle image. Re-examine the image and "
    "correct any mistakes: missed objects, wrong room boundaries, wrong cell coordinates, "
    "miscounted grid size, or clue mistypings. Emit the corrected JSON object only.\n\n"
)


def extract_puzzle(
    image_path: str | Path,
    *,
    provider: str = "claude",
    model: str | None = None,
    review: bool = False,
) -> dict[str, Any]:
    from murbo.providers import encode_image

    system = _PROMPT_PATH.read_text()
    image_b64 = encode_image(image_path)
    vp = get_provider(provider, model)

    puzzle = vp.extract(system=system, instruction=_INSTRUCTION, image_b64=image_b64)

    if review:
        puzzle = vp.extract(
            system=system,
            instruction=_REVIEW_INSTRUCTION + json.dumps(puzzle, indent=2),
            image_b64=image_b64,
        )
    return _normalize(puzzle)


def _normalize(puzzle: dict[str, Any]) -> dict[str, Any]:
    """Tidy harmless model quirks before schema validation.

    Models often emit explicit ``null`` for optional fields they chose not to set (e.g. a
    room's ``category``); the schema treats a missing key and ``null`` differently, so drop
    such top-level optional nulls. Nulls *inside* clues are meaningful (e.g. ``object_offset``
    uses ``null`` for an unconstrained axis), so those are left untouched.
    """
    for room in puzzle.get("rooms", []):
        if isinstance(room, dict) and room.get("category") is None:
            room.pop("category", None)
    return puzzle
