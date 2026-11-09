"""Крок 7: оцінка варіантів за рубрикою.

Це лише ПОРЯДОК у списку, а не прогноз: і люди, і моделі погано вгадують,
який хук виграє, — вирішує тест. Тому:
- модель ставить 1–5 за кожним із 5 критеріїв, підсумок рахує код
  (окремі критерії стабільніші за одну «загальну» оцінку);
- варіанти йдуть у перемішаному порядку з фіксованим seed (модель схильна
  вище ставити те, що стоїть першим).
"""
import random

from rehook.claims import model_view
from rehook.llm import LLM

CRITERIA = ["stop_scroll", "specificity", "clarity_3s", "tone_fit", "winner_likeness"]


def score_from_criteria(c: dict) -> float:
    """Сума 5…25 → шкала 1…10."""
    total = sum(c[name] for name in CRITERIA)
    return round(1 + (total - 5) * 9 / 20, 1)


def validate_rank(data: dict, keys: list[str]) -> None:
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("'results' must be a list")
    missing = [k for k in keys if k not in {r.get("key") for r in results}]
    if missing:
        raise ValueError(f"missing results for keys: {missing}")
    for r in results:
        for name in CRITERIA:
            value = r.get(name)
            if not isinstance(value, int) or not 1 <= value <= 5:
                raise ValueError(f"{name} must be an integer 1-5 for {r.get('key')}, got {value!r}")


def rank_variants(llm: LLM, variants: list[dict], brand: dict, examples: dict, seed: int) -> None:
    shuffled = list(variants)
    random.Random(seed).shuffle(shuffled)
    keys = [v["key"] for v in variants]
    variables = {
        "tone": brand["tone"],
        "best_examples": examples["best"] or "none",
        "worst_examples": examples["worst"] or "none",
        "variants": model_view(shuffled),
    }
    data = llm.ask_json("rank", "rank", variables, lambda d: validate_rank(d, keys))
    by_key = {r["key"]: r for r in data["results"]}
    for v in variants:
        v["score"] = score_from_criteria(by_key[v["key"]])
