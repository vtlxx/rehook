import pytest

import rehook.llm as llm_mod
from rehook.llm import LLM, LLMError, parse_json, render_prompt
from tests.fakes import FakeClient


@pytest.fixture
def prompt_x(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_mod, "PROMPTS_DIR", tmp_path)
    (tmp_path / "x.md").write_text("Say hi as JSON")


def need_key_a(d):
    if "a" not in d:
        raise ValueError("missing key 'a'")


def test_parse_json_strips_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        parse_json("not json")
    with pytest.raises(ValueError):
        parse_json("[1, 2]")


def test_render_prompt_replaces_placeholders(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_mod, "PROMPTS_DIR", tmp_path)
    (tmp_path / "x.md").write_text("Brand: {{brand}}\nList: {{items}}")
    out = render_prompt("x", {"brand": "SockLock", "items": ["a"]})
    assert "Brand: SockLock" in out and '"a"' in out


def test_render_prompt_missing_variable(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_mod, "PROMPTS_DIR", tmp_path)
    (tmp_path / "x.md").write_text("Brand: {{brand}}")
    with pytest.raises(LLMError, match="brand"):
        render_prompt("x", {})


def test_retry_once_then_ok(prompt_x):
    client = FakeClient(["oops", '{"a": 2}'])
    assert LLM(client=client).ask_json("s", "x", {}, need_key_a) == {"a": 2}
    retry = client.calls[1]["messages"]
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert retry[1]["content"] == "oops" and "invalid" in retry[2]["content"]


def test_second_failure_raises(prompt_x):
    client = FakeClient(['{"b": 1}', '{"b": 1}'])
    with pytest.raises(LLMError, match="missing key 'a'"):
        LLM(client=client).ask_json("s", "x", {}, need_key_a)
    assert len(client.calls) == 2


def test_usage_and_cost(prompt_x):
    llm = LLM(client=FakeClient(['{"a": 1}']))
    llm.ask_json("s", "x", {}, need_key_a)
    assert llm.usage == [{"step": "s", "input_tokens": 100, "output_tokens": 50}]
    assert llm.cost() == pytest.approx((100 * 2.0 + 50 * 10.0) / 1e6)


def test_request_params(prompt_x):
    client = FakeClient(['{"a": 1}'])
    LLM(client=client).ask_json("s", "x", {}, need_key_a)
    kw = client.calls[0]
    assert kw["model"] == "claude-sonnet-5-5" and kw["output_config"] == {"effort": "low"}
    assert "temperature" not in kw and "thinking" not in kw


def test_mock_reads_fixture(tmp_path, monkeypatch, prompt_x):
    monkeypatch.setattr(llm_mod, "FIXTURES_DIR", tmp_path)
    (tmp_path / "s.json").write_text('{"a": 3}')
    llm = LLM(mock=True)
    assert llm.ask_json("s", "x", {}, need_key_a) == {"a": 3}
    assert llm.cost() == 0.0


def test_mock_missing_fixture(tmp_path, monkeypatch, prompt_x):
    monkeypatch.setattr(llm_mod, "FIXTURES_DIR", tmp_path)
    with pytest.raises(LLMError, match="no mock fixture"):
        LLM(mock=True).ask_json("s", "x", {}, need_key_a)


def test_truncated_reply_gets_actionable_retry_hint(prompt_x):
    client = FakeClient(['{"a": ', '{"a": 1}'], stop_reasons=["max_tokens", "end_turn"])
    assert LLM(client=client).ask_json("s", "x", {}, need_key_a) == {"a": 1}
    retry = client.calls[1]["messages"]
    assert retry[1]["content"] == '{"a": ' and "cut off" in retry[2]["content"]
