"""Step 2: angle matrix: 6 different "approaches" to the same ad."""
from itertools import combinations

from rehook.llm import LLM

NUM_ANGLES = 6
EMOTIONS = ["humor", "frustration", "relief", "curiosity"]
FRAME_FORMATS = ["close-up", "pov", "talking-head", "on-screen-text", "before-after"]
DIMENSIONS = ("pain", "persona", "emotion", "frame_format")
MIN_FORMATS = 4  # first frames must differ: Andromeda compares the image too


def _dims(angle: dict) -> tuple:
    return tuple(str(angle.get(d, "")).strip().lower() for d in DIMENSIONS)


def validate_angles(data: dict, personas: list[str]) -> None:
    angles = data.get("angles")
    if not isinstance(angles, list) or len(angles) != NUM_ANGLES:
        raise ValueError(f"need exactly {NUM_ANGLES} angles")
    for a in angles:
        # ValueError only: otherwise LLM.ask_json will not retry with the error text.
        missing = [k for k in ("angle_id", "slug") + DIMENSIONS if not str(a.get(k, "")).strip()]
        if missing:
            raise ValueError(f"angle is missing fields: {missing}")
        if a.get("persona") not in personas:
            raise ValueError(f"persona must be one of {personas}, got {a.get('persona')!r}")
        if a.get("emotion") not in EMOTIONS:
            raise ValueError(f"emotion must be one of {EMOTIONS}, got {a.get('emotion')!r}")
        if a.get("frame_format") not in FRAME_FORMATS:
            raise ValueError(f"frame_format must be one of {FRAME_FORMATS}, got {a.get('frame_format')!r}")
    for key in ("angle_id", "slug"):
        if len({a[key] for a in angles}) != NUM_ANGLES:
            raise ValueError(f"'{key}' values must be unique")
    if sum(1 for a in angles if a.get("is_safe") is True) != 1:
        raise ValueError("exactly one angle must have is_safe=true (close to the winner)")
    if len({a["frame_format"] for a in angles}) < MIN_FORMATS:
        raise ValueError(f"use at least {MIN_FORMATS} different frame_format values")
    for a, b in combinations(angles, 2):
        same = sum(x == y for x, y in zip(_dims(a), _dims(b)))
        if len(DIMENSIONS) - same < 2:
            raise ValueError(f"angles {a['angle_id']} and {b['angle_id']} must differ in at least 2 of {DIMENSIONS}")


def build_angles(llm: LLM, brand: dict, parsed: dict) -> list[dict]:
    variables = {
        "brand": {k: brand.get(k) for k in ("product", "offer", "facts", "tone")},
        "parsed": parsed,
        "personas": brand["personas"],
        "emotions": EMOTIONS,
        "frame_formats": FRAME_FORMATS,
    }
    data = llm.ask_json("angles", "angles", variables, lambda d: validate_angles(d, brand["personas"]))
    return data["angles"]
