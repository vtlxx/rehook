"""Генерує синтетичне вивантаження з Ads Manager: data/ads_export.csv.

Орієнтири з ТЗ: CPM ~$12, CTR ~1.2%, CPA ~$50. Більшість оголошень з малим
spend (їх вимкнули), кілька переможців з великим. Частка «дійшли до
масштабування» ~10% (реальний hit rate у Meta ~5%, але в демо має бути що показати).

Запуск: python scripts/make_ads_export.py (seed фіксований — результат відтворюваний).
"""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LTV = 68
UNDERCOUNT = 0.12
SLUGS = ["pain-lost-sock", "pain-odd-socks", "pain-sorting-time", "persona-parents",
         "persona-students", "emotion-humor", "frame-pov", "frame-before-after"]
# Додаткові оголошення — від старих переможців, щоб не зачепити нумерацію W012.
EXTRA_WINNERS = ["005", "019", "022"]


def make_names(launched: list[str], group: str, total: int) -> list[str]:
    names = [n for n in launched if f"_{group}_" in n]
    i = 0
    while len(names) < total:
        winner = EXTRA_WINNERS[i % len(EXTRA_WINNERS)]
        names.append(f"SL_W{winner}_{group}_H{i // len(EXTRA_WINNERS) + 1:02d}_{SLUGS[i % len(SLUGS)]}")
        i += 1
    return names


def plan_spend_and_romi(rng: random.Random, names: list[str], launched: set[str],
                        big_count: int, scaled_count: int) -> dict[str, tuple[float, float]]:
    """Кілька запущених оголошень отримують великий spend, з них частина — переможці."""
    candidates = [n for n in names if n in launched]
    rng.shuffle(candidates)
    big = candidates[:big_count]
    plan = {}
    for name in names:
        if name in big:
            spend = rng.uniform(500, 2500)
            romi = rng.uniform(1.3, 2.0) if big.index(name) < scaled_count else rng.uniform(0.6, 1.15)
        else:
            spend = rng.uniform(20, 350)
            romi = rng.uniform(0.3, 1.6)
        plan[name] = (round(spend, 2), romi)
    return plan


def main() -> None:
    rng = random.Random(7)
    with open(ROOT / "data" / "launched.csv", newline="", encoding="utf-8") as f:
        launched = [row["ad_name"] for row in csv.DictReader(f)]
    launched_set = set(launched)

    rows = []
    for group, big_count in (("AI", 6), ("MAN", 5)):
        names = make_names(launched, group, 40)
        plan = plan_spend_and_romi(rng, names, launched_set, big_count, scaled_count=4)
        for name in names:
            spend, romi = plan[name]
            # Покупки, які побачила Meta: ROMI = покупки/(1-недооблік) * LTV / spend.
            purchases = round(romi * spend / LTV * (1 - UNDERCOUNT))
            impressions = round(spend / 12 * 1000 * rng.uniform(0.85, 1.15))
            clicks = round(impressions * rng.uniform(0.010, 0.014))
            rows.append({"ad_name": name, "spend": f"{spend:.2f}", "purchases": purchases,
                         "impressions": impressions, "clicks": clicks})

    with open(ROOT / "data" / "ads_export.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ad_name", "spend", "purchases", "impressions", "clicks"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to data/ads_export.csv")


if __name__ == "__main__":
    main()
