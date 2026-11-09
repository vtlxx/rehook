import csv
from collections import Counter
from pathlib import Path

import yaml

from rehook.report import ad_romi, load_ads, parse_ad_name


def launched_rows():
    with open("data/launched.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_winners_have_ids_and_hook_lines():
    for wid in ("012", "027", "031"):
        text = Path(f"data/winner_{wid}.txt").read_text()
        assert text.startswith(f"WINNER_ID: {wid}") and "[0-3s]" in text


def test_brand_matches_spec():
    b = yaml.safe_load(Path("data/brand.yaml").read_text())
    assert b["price_rules"] == ["$29"]
    assert b["limits"] == {"hook_vo_max_words": 12, "on_screen_max_words": 7}
    assert len(b["personas"]) == 4


def test_launched_and_ads_consistent():
    launched = launched_rows()
    names = {r["ad_name"] for r in load_ads("data/ads_export.csv")}
    assert 28 <= len(launched) <= 35 and all(r["ad_name"] in names for r in launched)
    assert {f"SL_W012_AI_H{i:02d}" for i in range(1, 11)} <= {r["ad_name"][:14] for r in launched}


def test_ads_export_shape():
    ads = load_ads("data/ads_export.csv")
    groups = Counter(parse_ad_name(r["ad_name"])["group"] for r in ads)
    assert groups == {"AI": 40, "MAN": 40}
    scaled = Counter(parse_ad_name(r["ad_name"])["group"] for r in ads
                     if r["spend"] >= 500 and ad_romi(r, 68, 0.12) >= 1.25)
    assert 3 <= scaled["AI"] <= 6 and 3 <= scaled["MAN"] <= 6
    launched = {r["ad_name"] for r in launched_rows()}
    assert sum(1 for r in ads if r["ad_name"] in launched and r["spend"] >= 500) >= 10
    impressions = sum(r["impressions"] for r in ads)
    assert 10 <= sum(r["spend"] for r in ads) / impressions * 1000 <= 14
    assert 0.010 <= sum(r["clicks"] for r in ads) / impressions <= 0.014
