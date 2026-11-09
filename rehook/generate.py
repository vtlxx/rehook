"""Крок 3: генерація варіантів хука — один виклик моделі на кут, усі кути паралельно.

Чому не один виклик на все: 30 варіантів в одній відповіді — це 40–60 с і
повтор усього при збої. Усередині кута модель бачить свої варіанти разом,
тож сама уникає повторів; між кутами різницю задає сам кут.
"""
import math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from rehook.llm import LLM
from rehook.report import ad_romi, parse_ad_name

HOOK_TYPES = ["question", "confession", "bold-statement", "pov", "contrast", "number", "curiosity"]
REQUIRED = ("hook_type", "hook_vo", "on_screen_text", "first_frame")
ANGLE_FIELDS = ("angle_id", "pain", "persona", "emotion", "frame_format")


def variants_per_angle(n: int, num_angles: int = 6) -> int:
    """Генеруємо із запасом ×1.5: частина відсіється на перевірках."""
    return math.ceil(1.5 * n / num_angles)


def validate_variants(data: dict, k: int) -> None:
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) != k:
        raise ValueError(f"need exactly {k} variants")
    for v in variants:
        for field in REQUIRED:
            if not str(v.get(field, "")).strip():
                raise ValueError(f"'{field}' must be a non-empty string")
        if not isinstance(v.get("bridge_line", ""), str):
            raise ValueError("'bridge_line' must be a string (empty if not needed)")
        if v["hook_type"] not in HOOK_TYPES:
            raise ValueError(f"hook_type must be one of {HOOK_TYPES}, got {v['hook_type']!r}")
    # Різні типи хуків усередині кута — щоб не вийшло 5 перефразувань однієї думки.
    max_same = math.ceil(k / len(HOOK_TYPES))
    repeated = [t for t, c in Counter(v["hook_type"] for v in variants).items() if c > max_same]
    if repeated:
        raise ValueError(f"hook_type values must differ within the angle; repeated: {repeated}")


def pick_examples(ads: list[dict], launched: list[dict], ltv: float = 68, undercount: float = 0.12,
                  min_spend: float = 500, top: int = 5) -> dict:
    """Найкращі й найгірші хуки за ROMI — приклади для моделі.

    Лише оголошення зі spend ≥ min_spend: на малих сумах ROMI — це шум.
    """
    texts = {row["ad_name"]: row for row in launched}
    rated = []
    for row in ads:
        if row["ad_name"] in texts and row["spend"] >= min_spend:
            parsed = parse_ad_name(row["ad_name"])
            rated.append({
                "ad_name": row["ad_name"],
                "slug": parsed["slug"] if parsed else "",
                "hook_vo": texts[row["ad_name"]]["hook_vo"],
                "on_screen_text": texts[row["ad_name"]]["on_screen_text"],
                "romi": round(ad_romi(row, ltv, undercount), 2),
            })
    rated.sort(key=lambda r: r["romi"], reverse=True)
    best = rated[:top]
    # Якщо оголошень мало, той самий хук не має бути і «що працює», і «не повторюй».
    worst = [r for r in rated[::-1][:top] if r not in best]
    return {"best": best, "worst": worst}


def next_hook_number(winner_id: str, names: list[str]) -> int:
    """Продовжуємо нумерацію AI-хуків цього переможця, щоб не збігтися із запущеними."""
    numbers = [p["nn"] for p in map(parse_ad_name, names)
               if p and p["group"] == "AI" and p["winner_id"] == winner_id]
    return max(numbers, default=0) + 1


def assign_ids(variants: list[dict], winner_id: str, start_nn: int, start_key: int) -> None:
    """ID для Ads Manager (SL_W012_AI_H11_slug) і короткий ключ v1… для кроків 5 і 7."""
    for offset, variant in enumerate(variants):
        variant["variant_id"] = f"SL_W{winner_id}_AI_H{start_nn + offset:02d}_{variant['angle_slug']}"
        variant["key"] = f"v{start_key + offset}"


def _short_angle(angle: dict) -> dict:
    return {k: angle[k] for k in ("slug", "pain", "persona", "emotion", "frame_format")}


def generate_for_angle(llm: LLM, angle: dict, context: dict, k: int, avoid: list[str] | None = None,
                       step: str = "generate") -> list[dict]:
    brand = context["brand"]
    limits = brand["limits"]
    examples = context["examples"]
    variables = {
        "brand": {key: brand.get(key) for key in ("product", "offer", "facts", "banned_claims", "banned_words", "tone")},
        "parsed": context["parsed"],
        "body": context["body"],
        "angle": _short_angle(angle) | {"is_safe": angle.get("is_safe", False)},
        "other_angles": [_short_angle(a) for a in context["angles"] if a["angle_id"] != angle["angle_id"]],
        "k": str(k),
        "hook_types": HOOK_TYPES,
        "vo_max": str(limits["hook_vo_max_words"]),
        "onscreen_max": str(limits["on_screen_max_words"]),
        "best_examples": examples["best"] or "none",
        "worst_examples": examples["worst"] or "none",
        "avoid": avoid or "none",
    }
    data = llm.ask_json(step, "generate", variables, lambda d: validate_variants(d, k),
                        fixture=f"{step}_{angle['angle_id']}")
    result = []
    for v in data["variants"]:
        item = {field: angle[field] for field in ANGLE_FIELDS}
        item.update(angle_slug=angle["slug"], winner_id=context["winner_id"],
                    hook_type=v["hook_type"], hook_vo=v["hook_vo"].strip(),
                    on_screen_text=v["on_screen_text"].strip(), first_frame=v["first_frame"].strip(),
                    bridge_line=v.get("bridge_line", "").strip())
        result.append(item)
    return result


def generate_all(llm: LLM, angles: list[dict], context: dict, k: int) -> list[dict]:
    """Паралельні виклики (по потоку на кут); порядок результату = порядок кутів."""
    with ThreadPoolExecutor(max_workers=len(angles)) as pool:
        batches = list(pool.map(lambda a: generate_for_angle(llm, a, context, k), angles))
    return [v for batch in batches for v in batch]
