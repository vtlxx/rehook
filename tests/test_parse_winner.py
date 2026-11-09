import json

import pytest

from rehook.llm import LLM
from rehook.parse_winner import parse_winner, read_winner, validate_parsed
from tests.fakes import FakeClient

PARSED = {
    "segments": [{"part": "hook", "timecode": "0-3s", "vo": "v", "on_screen": "o", "visual": "x"}],
    "winning_angle": {"pain": "p", "persona": "busy parents", "emotion": "humor", "why": "w"},
}


def test_read_winner(tmp_path):
    p = tmp_path / "w.txt"
    p.write_text('WINNER_ID: 012\n[0-3s] VO: "hook"\n[3-8s] VO: "body one"\n[8-15s] VO: "body two"\n')
    w = read_winner(str(p))
    assert w["winner_id"] == "012" and "hook" not in w["body"] and "body two" in w["body"]


def test_read_winner_without_id(tmp_path):
    p = tmp_path / "w.txt"
    p.write_text("[0-3s] VO: x")
    with pytest.raises(ValueError, match="WINNER_ID"):
        read_winner(str(p))


def test_validate_parsed():
    validate_parsed(PARSED)
    bad = json.loads(json.dumps(PARSED))
    bad["segments"][0]["part"] = "intro"
    with pytest.raises(ValueError, match="part"):
        validate_parsed(bad)
    with pytest.raises(ValueError, match="winning_angle"):
        validate_parsed({"segments": PARSED["segments"], "winning_angle": {"pain": "p"}})


def test_parse_winner_calls_llm():
    llm = LLM(client=FakeClient([json.dumps(PARSED)]))
    out = parse_winner(llm, {"winner_id": "012", "text": "script", "body": ""}, {"product": "SockLock"})
    assert out == PARSED and "script" in llm.client.calls[0]["messages"][0]["content"]
