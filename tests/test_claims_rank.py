import json
import re

import pytest

from rehook.claims import check_claims, validate_claims
from rehook.llm import LLM
from rehook.rank import CRITERIA, rank_variants, score_from_criteria, validate_rank
from tests.fakes import FakeClient, prompt_of

VS = [{"key": f"v{i}", "hook_vo": f"vo {i}", "on_screen_text": "os", "bridge_line": "", "variant_id": f"ID{i}"}
      for i in range(1, 6)]
BRAND = {"facts": ["f"], "offer": "o", "banned_claims": ["free"], "tone": "t"}


def test_score_formula():
    assert score_from_criteria(dict.fromkeys(CRITERIA, 5)) == 10.0
    assert score_from_criteria(dict.fromkeys(CRITERIA, 1)) == 1.0
    assert score_from_criteria(dict.fromkeys(CRITERIA, 3)) == 5.5


def test_check_claims_maps_by_key():
    reply = {"results": [{"key": v["key"], "claim_ok": v["key"] != "v2",
                          "claim_note": "'improves circulation' is a health claim" if v["key"] == "v2" else ""}
                         for v in VS]}
    items = [dict(v) for v in VS]
    llm = LLM(client=FakeClient([json.dumps(reply)]))
    check_claims(llm, items, BRAND)
    assert items[1]["claim_ok"] is False and "circulation" in items[1]["claim_note"]
    assert items[0]["claim_ok"] is True
    assert "ID1" not in prompt_of(llm.client.calls[0])      # the model gets only keys and texts


def test_validate_claims_missing_key():
    with pytest.raises(ValueError, match="v3"):
        validate_claims({"results": [{"key": "v1", "claim_ok": True, "claim_note": ""}]}, ["v1", "v3"])
    with pytest.raises(ValueError, match="claim_ok"):
        validate_claims({"results": [{"key": "v1", "claim_ok": "yes", "claim_note": ""}]}, ["v1"])


def test_validate_rank_range():
    ok = {"results": [dict(key="v1", **dict.fromkeys(CRITERIA, 3))]}
    validate_rank(ok, ["v1"])
    ok["results"][0]["tone_fit"] = 6
    with pytest.raises(ValueError, match="tone_fit"):
        validate_rank(ok, ["v1"])


def sent_key_order(seed):
    reply = {"results": [dict(key=v["key"], **dict.fromkeys(CRITERIA, 4)) for v in VS]}
    client = FakeClient([json.dumps(reply)])
    items = [dict(v) for v in VS]
    rank_variants(LLM(client=client), items, BRAND, {"best": [], "worst": []}, seed=seed)
    return re.findall(r'"key": "(v\d+)"', prompt_of(client.calls[0])), items


def test_rank_shuffle_is_deterministic():
    assert sent_key_order(42)[0] == sent_key_order(42)[0]
    assert sent_key_order(42)[0] != sent_key_order(43)[0]


def test_rank_sets_score():
    _, items = sent_key_order(42)
    assert all(i["score"] == 7.8 for i in items)
