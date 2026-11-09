"""Крок 8: відбір топ-n зі збереженням різноманітності кутів."""
import math
from collections import Counter


def select_top(variants: list[dict], n: int, num_angles: int) -> tuple[list[dict], list[dict], list[str]]:
    """Повертає (відібрані за спаданням оцінки, решта з reason=below_top_n, попередження).

    Правило: не менше 2 і не більше ceil(n / кути) + 1 варіантів на кут.
    Спершу беремо по 2 найкращі з кожного кута, потім добираємо за оцінкою.
    """
    cap = math.ceil(n / num_angles) + 1
    ordered = sorted(variants, key=lambda v: v["score"], reverse=True)

    selected, per_angle, warnings = [], Counter(), []
    angles = list(dict.fromkeys(v["angle_id"] for v in ordered))
    for angle in sorted(angles):
        best_two = [v for v in ordered if v["angle_id"] == angle][:2]
        selected += best_two
        per_angle[angle] = len(best_two)
        if len(best_two) < 2:
            warnings.append(f"angle {angle} has only {len(best_two)} variant(s) after filtering")

    for variant in ordered:
        if len(selected) >= n:
            break
        if variant in selected or per_angle[variant["angle_id"]] >= cap:
            continue
        selected.append(variant)
        per_angle[variant["angle_id"]] += 1

    selected.sort(key=lambda v: v["score"], reverse=True)
    rest = [v for v in ordered if v not in selected]
    for variant in rest:
        variant["reason"] = "below_top_n"
    return selected, rest, warnings
