"""Крок 5: перевірка обіцянок моделлю — чи є твердження поза фактами брифу або під забороною.

Короткі заборонені слова ("free", "lifetime") додатково ловить код (rules.py):
пропущена заборонена обіцянка коштує дорожче за зайвий прапорець.
"""
from rehook.llm import LLM


def model_view(variants: list[dict]) -> list[dict]:
    """Моделі передаємо лише короткий ключ і тексти — менше токенів, без прив'язки до нумерації."""
    return [{"key": v["key"], "hook_vo": v["hook_vo"], "on_screen_text": v["on_screen_text"],
             "bridge_line": v.get("bridge_line", "")} for v in variants]


def validate_claims(data: dict, keys: list[str]) -> None:
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("'results' must be a list")
    got = {r.get("key") for r in results}
    missing = [k for k in keys if k not in got]
    if missing:
        raise ValueError(f"missing results for keys: {missing}")
    for r in results:
        if not isinstance(r.get("claim_ok"), bool):
            raise ValueError(f"claim_ok must be true/false for {r.get('key')}")
        if not isinstance(r.get("claim_note", ""), str):
            raise ValueError(f"claim_note must be a string for {r.get('key')}")


def check_claims(llm: LLM, variants: list[dict], brand: dict) -> None:
    keys = [v["key"] for v in variants]
    variables = {"facts": brand["facts"], "offer": brand["offer"], "banned_claims": brand["banned_claims"],
                 "variants": model_view(variants)}
    data = llm.ask_json("claims", "claims", variables, lambda d: validate_claims(d, keys))
    by_key = {r["key"]: r for r in data["results"]}
    for v in variants:
        v["claim_ok"] = by_key[v["key"]]["claim_ok"]
        v["claim_note"] = by_key[v["key"]].get("claim_note", "")
