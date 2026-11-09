"""Команда report: порівняння AI-модифікацій з ручними за вивантаженням з Ads Manager."""
import csv
import math
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

AD_NAME_RE = re.compile(r"^SL_W(\d+)_(AI|MAN)_H(\d+)(?:_(.+))?$")
GROUPS = ["AI", "MAN"]
REPORT_COLUMNS = ["group", "angle_slug", "ads", "scaled", "scaled_share", "ci_low", "ci_high",
                  "spend", "purchases_adj", "cpa", "romi"]
MIN_GROUP_SIZE = 30


def parse_ad_name(name: str) -> dict | None:
    """SL_W012_AI_H03_pain-lost-sock → переможець, група (AI/MAN), номер хука, slug кута."""
    match = AD_NAME_RE.match(name.strip())
    if not match:
        return None
    winner_id, group, nn, slug = match.groups()
    return {"winner_id": winner_id, "group": group, "nn": int(nn), "slug": slug or ""}


def adjusted_purchases(purchases: float, undercount: float) -> float:
    """Meta бачить на ~12% менше покупок, ніж бекенд, тому додаємо втрачене."""
    return purchases / (1 - undercount)


def ad_romi(row: dict, ltv: float, undercount: float) -> float:
    """ROMI = LTV-виручка / spend (1.35 = 135%, так рахує команда)."""
    if row["spend"] == 0:
        return 0.0
    return adjusted_purchases(row["purchases"], undercount) * ltv / row["spend"]


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% довірчий інтервал Вілсона для частки k/n — коректний і на малих вибірках."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load_ads(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in ("spend", "purchases", "impressions", "clicks"):
            row[key] = float(row[key] or 0)
    return rows


def _group_row(group: str, slug: str, ads: list[dict], ltv: float, min_spend: float,
               min_romi: float, undercount: float) -> dict:
    """Один рядок звіту. Середні зважені за spend рахуємо як відношення сум."""
    spend = sum(a["spend"] for a in ads)
    purchases_adj = sum(adjusted_purchases(a["purchases"], undercount) for a in ads)
    scaled = sum(1 for a in ads if a["spend"] >= min_spend and ad_romi(a, ltv, undercount) >= min_romi)
    ci_low, ci_high = wilson_interval(scaled, len(ads))
    return {
        "group": group,
        "angle_slug": slug,
        "ads": len(ads),
        "scaled": scaled,
        "scaled_share": scaled / len(ads) if ads else 0.0,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "spend": spend,
        "purchases_adj": purchases_adj,
        "cpa": spend / purchases_adj if purchases_adj else None,
        "romi": purchases_adj * ltv / spend if spend else 0.0,
    }


def summarize(rows: list[dict], ltv: float, min_spend: float, min_romi: float, undercount: float) -> dict:
    by_group = {g: [] for g in GROUPS}
    ignored = 0
    for row in rows:
        parsed = parse_ad_name(row["ad_name"])
        if parsed is None:
            ignored += 1
            continue
        by_group[parsed["group"]].append({**row, "slug": parsed["slug"]})

    params = (ltv, min_spend, min_romi, undercount)
    result = [_group_row(g, "ALL", by_group[g], *params) for g in GROUPS]
    # Розбивка за кутами — лише для AI.
    for slug in sorted({a["slug"] for a in by_group["AI"]}):
        ads = [a for a in by_group["AI"] if a["slug"] == slug]
        result.append(_group_row("AI", slug or "-", ads, *params))

    small = [g for g in GROUPS if len(by_group[g]) < MIN_GROUP_SIZE]
    return {"rows": result, "ignored": ignored, "small_groups": small}


def _fmt(value, digits=2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def write_report_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row[k] is None else row[k]) for k in REPORT_COLUMNS})


def print_report(summary: dict, console: Console) -> None:
    table = Table(title="AI vs MAN modifications")
    for col in ("Group", "Angle", "Ads", "Scaled", "Share", "95% CI", "Spend", "CPA", "ROMI"):
        table.add_column(col, justify="left" if col in ("Group", "Angle") else "right")
    for r in summary["rows"]:
        table.add_row(
            r["group"], r["angle_slug"], str(r["ads"]), str(r["scaled"]),
            f"{r['scaled_share']:.0%}", f"{r['ci_low']:.0%}–{r['ci_high']:.0%}",
            f"${r['spend']:,.0f}", "—" if r["cpa"] is None else f"${r['cpa']:.2f}", _fmt(r["romi"]),
        )
    console.print(table)
    console.print(f"Ignored rows (not SL_W..._AI/MAN_...): {summary['ignored']}")
    for group in summary["small_groups"]:
        console.print(f"[yellow]Warning: fewer than {MIN_GROUP_SIZE} ads in group {group}: "
                      f"differences may be random.[/yellow]")


def run_report(args) -> None:
    rows = load_ads(args.ads)
    summary = summarize(rows, args.ltv, args.min_spend, args.min_romi, args.meta_undercount)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_report_csv(summary["rows"], out_dir / "report.csv")
    console = Console()
    print_report(summary, console)
    console.print(f"Saved {out_dir / 'report.csv'}")
