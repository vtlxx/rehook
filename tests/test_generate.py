import json

import pytest

from rehook.generate import (HOOK_TYPES, assign_ids, generate_all, generate_for_angle, next_hook_number,
                             pick_examples, validate_variants, variants_per_angle)
from rehook.llm import LLM
from tests.fakes import FakeClient, prompt_of


def test_variants_per_angle():
    assert variants_per_angle(20) == 5 and variants_per_angle(10) == 3


def good(k):
    return {"variants": [dict(hook_type=HOOK_TYPES[i % 7], hook_vo=f"vo {i}", on_screen_text="os",
                              first_frame="ff", bridge_line="") for i in range(k)]}


def test_validate_variants():
    validate_variants(good(5), 5)
    bad = good(5)
    bad["variants"][1]["hook_type"] = bad["variants"][0]["hook_type"]
    with pytest.raises(ValueError, match="hook_type"):
        validate_variants(bad, 5)
    with pytest.raises(ValueError, match="exactly 5"):
        validate_variants(good(4), 5)
    empty = good(3)
    empty["variants"][0]["hook_vo"] = ""
    with pytest.raises(ValueError, match="hook_vo"):
        validate_variants(empty, 3)


def test_validate_variants_more_than_seven_allows_repeats():
    validate_variants(good(9), 9)          # ceil(9/7)=2 повтори одного типу дозволені


def test_next_hook_number_and_ids():
    names = ["SL_W012_AI_H03_a", "SL_W012_AI_H10_b", "SL_W012_MAN_H15_c", "SL_W027_AI_H40_d"]
    assert next_hook_number("012", names) == 11 and next_hook_number("031", names) == 1
    vs = [{"angle_slug": "pain-lost-sock"}, {"angle_slug": "persona-parents"}]
    assign_ids(vs, "012", 11, 1)
    assert [v["variant_id"] for v in vs] == ["SL_W012_AI_H11_pain-lost-sock", "SL_W012_AI_H12_persona-parents"]
    assert [v["key"] for v in vs] == ["v1", "v2"]


def test_pick_examples_filters_and_ranks():
    ads = [{"ad_name": f"A{i}", "spend": 1000.0, "purchases": float(i)} for i in range(1, 13)] + \
          [{"ad_name": "SMALL", "spend": 100.0, "purchases": 50.0}, {"ad_name": "NOTEXT", "spend": 900.0, "purchases": 99.0}]
    launched = [{"ad_name": f"A{i}", "hook_vo": f"h{i}", "on_screen_text": ""} for i in range(1, 13)] + \
               [{"ad_name": "SMALL", "hook_vo": "s", "on_screen_text": ""}]
    ex = pick_examples(ads, launched)
    assert [e["ad_name"] for e in ex["best"]] == ["A12", "A11", "A10", "A9", "A8"]
    assert [e["ad_name"] for e in ex["worst"]] == ["A1", "A2", "A3", "A4", "A5"]
    assert ex["best"][0]["hook_vo"] == "h12"
    assert pick_examples([], []) == {"best": [], "worst": []}


ANGLE = {"angle_id": "A1", "slug": "s1", "pain": "p", "persona": "busy parents", "emotion": "humor",
         "frame_format": "pov", "is_safe": True}
CONTEXT = {"brand": {"limits": {"hook_vo_max_words": 12, "on_screen_max_words": 7}}, "parsed": {},
           "angles": [ANGLE], "examples": {"best": [], "worst": []}, "winner_id": "012", "body": "body"}


def test_generate_for_angle_copies_angle_fields_and_avoid_list():
    llm = LLM(client=FakeClient([json.dumps(good(3))]))
    out = generate_for_angle(llm, ANGLE, CONTEXT, 3, avoid=["old hook text"], step="topup")
    assert out[0]["angle_slug"] == "s1" and out[0]["persona"] == "busy parents" and out[0]["winner_id"] == "012"
    assert "old hook text" in prompt_of(llm.client.calls[0]) and llm.usage[0]["step"] == "topup"


def test_generate_all_parallel_keeps_angle_order():
    angles_ = [dict(ANGLE, angle_id=f"A{i}", slug=f"s{i}") for i in (1, 2)]
    llm = LLM(client=FakeClient([json.dumps(good(3))] * 2))
    out = generate_all(llm, angles_, dict(CONTEXT, angles=angles_), 3)
    assert [v["angle_id"] for v in out] == ["A1"] * 3 + ["A2"] * 3
