"""Step 8: pick the top n while keeping angle variety."""
import math
from collections import Counter


def select_top(variants: list[dict], n: int, angle_ids: list[str]) -> tuple[list[dict], list[dict], list[str]]:
    """Returns (selected by descending score, the rest with reason=below_top_n, warnings).

    Rule: at least 2 and at most ceil(n / angles) + 1 variants per angle.
    First take the best 2 from each angle, then fill up by score.
    """
    cap = math.ceil(n / len(angle_ids)) + 1
    ordered = sorted(variants, key=lambda v: v["score"], reverse=True)

    selected, per_angle, warnings = [], Counter(), []
    # Go over all planned angles, including those with nothing left after the filter.
    for angle in angle_ids:
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
