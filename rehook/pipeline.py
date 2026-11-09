"""Конвеєр generate: склеює кроки 1–8 в одну функцію."""
import csv
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from rehook import export
from rehook.angles import NUM_ANGLES, build_angles
from rehook.claims import check_claims
from rehook.generate import (assign_ids, generate_all, generate_for_angle, next_hook_number, pick_examples,
                             variants_per_angle)
from rehook.llm import LLM
from rehook.parse_winner import parse_winner, read_winner
from rehook.rank import rank_variants
from rehook.report import load_ads
from rehook.rules import apply_rules
from rehook.select import select_top
from rehook.similarity import filter_similar, variant_text

MOCK_WINNER = "012"
MOCK_VARIANTS_PER_ANGLE = 5  # фікстури записані для --n 20
MIN_VARIANTS, MIN_ANGLES = 15, 5
HISTORY_COLUMNS = ["ad_name", "hook_vo", "on_screen_text"]
BRAND_KEYS = ["product", "offer", "price_rules", "facts", "banned_claims", "banned_words", "tone", "limits",
              "personas"]


def _read_csv(path: str | None, columns: list[str]) -> list[dict]:
    if not path:
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        return list(reader)


def _read_brand(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        brand = yaml.safe_load(f) or {}
    missing = [k for k in BRAND_KEYS if k not in brand]
    if missing:
        raise ValueError(f"{path}: missing keys {missing}")
    return brand


def needs_topup(kept: list[dict], angles: list[dict], n: int) -> dict[str, int]:
    """Які кути добрати і скільки: якщо всього менше n або в якомусь куті < 2.

    Добираємо лише кути, де лишилось менше ceil(n/6), — дефіцит + 2 про запас.
    """
    per_angle = {a["angle_id"]: 0 for a in angles}
    for v in kept:
        per_angle[v["angle_id"]] += 1
    if len(kept) >= n and min(per_angle.values()) >= 2:
        return {}
    target = math.ceil(n / len(angles))
    return {a: target - c + 2 for a, c in per_angle.items() if c < target}


def _check_and_score(llm: LLM, variants: list[dict], brand: dict, examples: dict, seed: int) -> None:
    """Кроки 4, 5 і 7. Обіцянки й оцінка — два незалежні виклики, тож паралельно."""
    apply_rules(variants, brand)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = pool.submit(check_claims, llm, variants, brand)
        rank = pool.submit(rank_variants, llm, variants, brand, examples, seed)
        claims.result()
        rank.result()


def _filter(variants: list[dict], history: list[dict], threshold: float) -> tuple[list[dict], list[dict]]:
    for v in variants:  # фільтр можна запускати повторно (після догенерації)
        v.pop("reason", None)
        v.pop("max_similarity", None)
    return filter_similar(variants, history, threshold)


def _avoid_texts(angle_id: str, variants: list[dict], history: list[dict]) -> list[str]:
    """Що модель не має повторювати: усі варіанти кута + запущені хуки, на які вони були схожі."""
    texts = [variant_text(v) for v in variants if v["angle_id"] == angle_id]
    launched = {h["ad_name"]: h for h in history}
    for v in variants:
        reason = v.get("reason", "")
        if v["angle_id"] == angle_id and reason.startswith("similar_to_launched:"):
            texts.append(variant_text(launched[reason.split(":", 1)[1]]))
    return texts


def run_generate(llm: LLM, winner_path: str, brand_path: str, history_path: str | None, ads_path: str | None,
                 n: int, out_dir: str, sim_threshold: float, seed: int) -> dict:
    winner = read_winner(winner_path)
    if llm.mock and winner["winner_id"] != MOCK_WINNER:
        raise ValueError(f"mock fixtures exist only for winner {MOCK_WINNER}")
    if llm.mock and variants_per_angle(n, NUM_ANGLES) != MOCK_VARIANTS_PER_ANGLE:
        raise ValueError("mock fixtures exist only for --n 20 (5 variants per angle)")
    brand = _read_brand(brand_path)
    history = _read_csv(history_path, HISTORY_COLUMNS)
    ads = load_ads(ads_path) if ads_path else []

    # Кроки 1–3
    parsed = parse_winner(llm, winner, brand)
    angles = build_angles(llm, brand, parsed)
    examples = pick_examples(ads, history)
    context = {"brand": brand, "parsed": parsed, "angles": angles, "examples": examples,
               "winner_id": winner["winner_id"], "body": winner["body"]}
    variants = generate_all(llm, angles, context, variants_per_angle(n, NUM_ANGLES))
    start_nn = next_hook_number(winner["winner_id"], [r["ad_name"] for r in history + ads])
    assign_ids(variants, winner["winner_id"], start_nn, 1)

    # Кроки 4, 5, 7, потім 6
    _check_and_score(llm, variants, brand, examples, seed)
    kept, rejected = _filter(variants, history, sim_threshold)

    # Один раунд догенерації для кутів, де після фільтра замало варіантів
    topup = needs_topup(kept, angles, n)
    if topup and llm.mock:
        raise ValueError("this mock run needs a top-up round, which has no fixtures; use the default --sim-threshold")
    if topup:
        short = [a for a in angles if a["angle_id"] in topup]
        with ThreadPoolExecutor(max_workers=len(short)) as pool:
            batches = list(pool.map(
                lambda a: generate_for_angle(llm, a, context, topup[a["angle_id"]],
                                             avoid=_avoid_texts(a["angle_id"], variants, history), step="topup"),
                short))
        new = [v for batch in batches for v in batch]
        assign_ids(new, winner["winner_id"], start_nn + len(variants), len(variants) + 1)
        _check_and_score(llm, new, brand, examples, seed)
        variants += new
        kept, rejected = _filter(variants, history, sim_threshold)

    # Крок 8
    selected, below, warnings = select_top(kept, n, [a["angle_id"] for a in angles])
    rejected += below
    angles_used = len({v["angle_id"] for v in selected})
    if len(selected) < MIN_VARIANTS or angles_used < MIN_ANGLES:
        warnings.append(f"only {len(selected)} variants across {angles_used} angles after filtering "
                        f"(target: {MIN_VARIANTS}+ across {MIN_ANGLES}+)")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    export.write_variants_csv(selected, out / "variants.csv")
    export.write_rejected_csv(rejected, out / "rejected.csv")
    export.write_brief(out / "brief.md", winner, parsed, angles, selected, warnings)
    return {"winner": winner, "parsed": parsed, "angles": angles, "selected": selected, "rejected": rejected,
            "warnings": warnings, "generated": len(variants), "topup": topup}
