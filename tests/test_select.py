from collections import Counter

from rehook.select import select_top


def pool(counts, start=9.0):
    out, s = [], start
    for angle, c in counts.items():
        for i in range(c):
            out.append({"variant_id": f"{angle}-{i}", "angle_id": angle, "score": round(s, 2)})
            s -= 0.1
    return out


def test_quota_min_two_and_cap():
    vs = pool({"A1": 8, "A2": 2, "A3": 4, "A4": 4, "A5": 4, "A6": 4})
    sel, rest, warn = select_top(vs, n=20, angle_ids=[f'A{i}' for i in range(1, 7)])
    per = Counter(v["angle_id"] for v in sel)
    assert len(sel) == 20 and min(per.values()) >= 2 and max(per.values()) <= 5
    assert all(r["reason"] == "below_top_n" for r in rest) and len(rest) == len(vs) - 20
    assert warn == []


def test_selected_sorted_by_score():
    sel, _, _ = select_top(pool({"A1": 3, "A2": 3}), n=4, angle_ids=["A1", "A2"])
    assert [v["score"] for v in sel] == sorted((v["score"] for v in sel), reverse=True)


def test_warns_when_angle_short():
    _, _, warn = select_top(pool({"A1": 5, "A2": 1}), n=4, angle_ids=["A1", "A2"])
    assert warn == ["angle A2 has only 1 variant(s) after filtering"]


def test_low_scored_angle_still_gets_two():
    vs = pool({"A1": 6}) + [{"variant_id": "B", "angle_id": "A2", "score": 1.0},
                            {"variant_id": "C", "angle_id": "A2", "score": 1.5}]
    sel, _, _ = select_top(vs, n=4, angle_ids=["A1", "A2"])
    assert {"B", "C"} <= {v["variant_id"] for v in sel}


def test_warns_when_angle_empty():
    _, _, warn = select_top(pool({"A1": 5}), n=4, angle_ids=["A1", "A2"])
    assert warn == ["angle A2 has only 0 variant(s) after filtering"]
