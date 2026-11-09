"""Крок 8 (вивід): variants.csv, rejected.csv, brief.md для дизайнера і зведення в консоль."""
import csv
import io
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from rehook.llm import LLM

VARIANT_COLUMNS = ["variant_id", "winner_id", "angle_slug", "pain", "persona", "emotion", "frame_format",
                   "hook_type", "hook_vo", "on_screen_text", "first_frame", "bridge_line", "score",
                   "max_similarity", "rule_flags", "claim_ok", "claim_note"]
REJECTED_COLUMNS = ["variant_id", "angle_slug", "hook_vo", "on_screen_text", "score", "reason"]


def _csv_text(rows: list[dict], columns: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, "rule_flags": "; ".join(row.get("rule_flags", []))})
    return buffer.getvalue()


def _write_csv(rows: list[dict], path: Path, columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(_csv_text(rows, columns))


def variants_csv_text(variants: list[dict]) -> str:
    """Той самий variants.csv, але рядком: для кнопки «Завантажити» на сторінці."""
    return _csv_text(variants, VARIANT_COLUMNS)


def write_variants_csv(variants: list[dict], path: Path) -> None:
    _write_csv(variants, path, VARIANT_COLUMNS)


def write_rejected_csv(rejected: list[dict], path: Path) -> None:
    _write_csv(rejected, path, REJECTED_COLUMNS)


def variant_warnings(variant: dict) -> list[str]:
    notes = list(variant.get("rule_flags", []))
    if variant.get("claim_ok") is False:
        notes.append(f"claim: {variant.get('claim_note') or 'unsupported claim'}")
    return notes


def write_brief(path: Path, winner: dict, parsed: dict, angles: list[dict], selected: list[dict],
                warnings: list[str]) -> None:
    """Завдання дизайнеру: розбір переможця, незмінна частина, варіанти за кутами."""
    wa = parsed["winning_angle"]
    lines = [f"# Hook variants for winner {winner['winner_id']}", ""]
    if warnings:
        lines += ["> ⚠️ " + w for w in warnings] + [""]
    lines += ["## Why the winner works", "",
              f"- **Pain:** {wa['pain']}", f"- **Persona:** {wa['persona']}",
              f"- **Emotion:** {wa['emotion']}", f"- **Why:** {wa['why']}", ""]
    if parsed.get("segments"):
        lines += ["## Structure", "", "| Part | Time | VO | On-screen |", "|---|---|---|---|"]
        lines += [f"| {s['part']} | {s['timecode']} | {s.get('vo', '')} | {s.get('on_screen', '')} |"
                  for s in parsed["segments"]]
        lines.append("")
    lines += ["## Unchanged part (after 3s)", "", "```", winner["body"], "```", ""]

    for angle in angles:
        items = [v for v in selected if v["angle_id"] == angle["angle_id"]]
        if not items:
            continue
        kind = "safe" if angle.get("is_safe") else "bold"
        lines += [f"## {angle['angle_id']} · {angle['slug']} ({kind})", "",
                  f"Pain: {angle['pain']} · Persona: {angle['persona']} · Emotion: {angle['emotion']} · "
                  f"First frame: {angle['frame_format']}", ""]
        for v in items:
            lines += [f"### {v['variant_id']} — score {v['score']}", "",
                      f"- **Hook type:** {v['hook_type']}",
                      f"- **VO (0–3s):** {v['hook_vo']}",
                      f"- **On-screen:** {v['on_screen_text']}",
                      f"- **First frame:** {v['first_frame']}"]
            if v.get("bridge_line"):
                lines.append(f"- **Bridge line:** {v['bridge_line']}")
            for note in variant_warnings(v):
                lines.append(f"- ⚠️ **{note}**")
            lines.append("")

    lines += ["---", "",
              "_Score is ordering only, not a forecast: the test decides. "
              "Filtered-out variants and reasons: `rejected.csv`._", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(console: Console, result: dict, llm: LLM, elapsed: float) -> None:
    selected, rejected = result["selected"], result["rejected"]
    reasons = Counter(r["reason"].split(":")[0] for r in rejected)
    angles_used = len({v["angle_id"] for v in selected})
    console.print(f"[bold]Generated:[/bold] {result['generated']}  "
                  f"[bold]Rejected:[/bold] {len(rejected)} ({', '.join(f'{k}: {c}' for k, c in reasons.items()) or 'none'})  "
                  f"[bold]Selected:[/bold] {len(selected)} across {angles_used} angles")
    if result["topup"]:
        console.print(f"Top-up round for: {', '.join(f'{a} (+{n})' for a, n in result['topup'].items())}")
    flagged = sum(1 for v in selected if v.get("rule_flags") or v.get("claim_ok") is False)
    console.print(f"Flagged for designer review: {flagged}")
    for warning in result["warnings"]:
        console.print(f"[yellow]Warning: {warning}[/yellow]")

    table = Table(title="LLM usage")
    for col in ("Step", "Calls", "Input tokens", "Output tokens"):
        table.add_column(col, justify="left" if col == "Step" else "right")
    steps: dict[str, list] = {}
    for u in llm.usage:
        s = steps.setdefault(u["step"], [0, 0, 0])
        s[0] += 1
        s[1] += u["input_tokens"]
        s[2] += u["output_tokens"]
    for step, (calls, tin, tout) in steps.items():
        table.add_row(step, str(calls), f"{tin:,}", f"{tout:,}")
    console.print(table)
    console.print(f"[bold]Cost:[/bold] ${llm.cost():.3f}   [bold]Time:[/bold] {elapsed:.1f}s"
                  + ("   (mock: no API calls)" if llm.mock else ""))
    console.print("Note: score is ordering only, not a forecast — the test decides.")
