import pytest

from rehook.__main__ import main
from rehook.report import adjusted_purchases, ad_romi, parse_ad_name, summarize, wilson_interval


def test_parse_ad_name():
    assert parse_ad_name("SL_W012_AI_H03_pain-lost-sock") == {
        "winner_id": "012", "group": "AI", "nn": 3, "slug": "pain-lost-sock"}
    assert parse_ad_name("SL_W012_MAN_H07")["slug"] == ""
    assert parse_ad_name("BRAND_promo_1") is None


def test_adjusted_romi():
    row = {"spend": 2500.0, "purchases": 44.0}
    assert adjusted_purchases(44, 0.12) == pytest.approx(50.0)
    assert ad_romi(row, ltv=68, undercount=0.12) == pytest.approx(1.36)
    assert ad_romi(row, ltv=68, undercount=0) == pytest.approx(44 * 68 / 2500)


def test_wilson_interval_known_values():
    assert wilson_interval(8, 40) == pytest.approx((0.105, 0.348), abs=1e-3)
    assert wilson_interval(2, 40) == pytest.approx((0.014, 0.165), abs=1e-3)
    assert wilson_interval(0, 0) == (0.0, 0.0)


def rows(*items):
    return [{"ad_name": n, "spend": float(s), "purchases": float(p), "impressions": 0.0, "clicks": 0.0}
            for n, s, p in items]


def test_summarize_weighted_and_scaled():
    data = rows(("SL_W012_AI_H01_a", 1000, 17.6), ("SL_W012_AI_H02_b", 500, 4.4),
                ("SL_W012_MAN_H01_a", 100, 0), ("junk", 10, 1))
    s = summarize(data, ltv=68, min_spend=500, min_romi=1.25, undercount=0.12)
    ai = s["rows"][0]
    assert (ai["group"], ai["angle_slug"], ai["ads"]) == ("AI", "ALL", 2)
    assert ai["cpa"] == pytest.approx(1500 / 25) and ai["romi"] == pytest.approx(25 * 68 / 1500)
    assert ai["scaled"] == 1
    assert s["ignored"] == 1 and set(s["small_groups"]) == {"AI", "MAN"}
    assert [(r["group"], r["angle_slug"]) for r in s["rows"]] == [
        ("AI", "ALL"), ("MAN", "ALL"), ("AI", "a"), ("AI", "b")]


def test_zero_spend_and_purchases_do_not_crash():
    s = summarize(rows(("SL_W012_MAN_H01_a", 0, 0)), 68, 500, 1.25, 0.12)
    man = s["rows"][1]
    assert man["cpa"] is None and man["romi"] == 0.0
    assert s["rows"][0]["ads"] == 0


def test_report_cli_writes_csv(tmp_path):
    ads = tmp_path / "ads.csv"
    ads.write_text("ad_name,spend,purchases,impressions,clicks\nSL_W012_AI_H01_a,1000,20,80000,960\n")
    assert main(["report", "--ads", str(ads), "--out", str(tmp_path / "o")]) == 0
    header = (tmp_path / "o" / "report.csv").read_text().splitlines()[0]
    assert header == "group,angle_slug,ads,scaled,scaled_share,ci_low,ci_high,spend,purchases_adj,cpa,romi"
