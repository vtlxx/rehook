"""Крок 1: розбір скрипту ролика-переможця."""
import re

from rehook.llm import LLM

PARTS = {"hook", "problem", "demo", "offer", "cta"}
ANGLE_KEYS = ("pain", "persona", "emotion", "why")
TIMECODE_RE = re.compile(r"^\[(\d+)-(\d+)s\]")


def read_winner(path: str) -> dict:
    """ID і «незмінна частина» беремо кодом: модель для цього не потрібна."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r"^WINNER_ID:\s*(\w+)", text, re.MULTILINE)
    if not match:
        raise ValueError(f"WINNER_ID line not found in {path}")
    # Основна частина — рядки, що починаються з 3-ї секунди і далі: її не міняємо.
    body = [line for line in text.splitlines()
            if (tc := TIMECODE_RE.match(line.strip())) and int(tc.group(1)) >= 3]
    return {"winner_id": match.group(1), "text": text, "body": "\n".join(body)}


def validate_parsed(data: dict) -> None:
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("'segments' must be a non-empty list")
    for seg in segments:
        if seg.get("part") not in PARTS:
            raise ValueError(f"segment part must be one of {sorted(PARTS)}, got {seg.get('part')!r}")
        if not str(seg.get("timecode", "")).strip():
            raise ValueError("every segment needs a 'timecode'")
    angle = data.get("winning_angle")
    if not isinstance(angle, dict) or any(k not in angle for k in ANGLE_KEYS):
        raise ValueError(f"'winning_angle' must have keys {list(ANGLE_KEYS)}")


def parse_winner(llm: LLM, winner: dict, brand: dict) -> dict:
    """Модель розмічає структуру ролика і пояснює, чому він спрацював."""
    return llm.ask_json("parse_winner", "parse_winner",
                        {"winner_text": winner["text"], "product": brand["product"]}, validate_parsed)
