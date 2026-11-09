"""Designer page (app.py): run it without a browser through Streamlit AppTest."""
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = "../app.py"  # path relative to this file


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def generate(at, mock=True):
    at.checkbox(key="mock").set_value(mock).run()
    at.button(key="generate").click().run()
    return at


def picks(at):
    return [c for c in at.checkbox if c.key.startswith("pick_")]


def page_text(at):
    return "\n".join(m.value for m in at.markdown) + "\n".join(c.value for c in at.caption)


def test_mock_by_default_without_key(app):
    assert app.checkbox(key="mock").value is True


def test_mock_generate_shows_cards_by_angle_with_flags(app):
    at = generate(app)
    assert not at.exception and not at.error
    assert len(picks(at)) == 20
    assert len(at.subheader) == 6                      # cards are grouped by 6 angles
    text = page_text(at)
    assert "price:$19" in text and "banned_claim:free" in text   # flags are visible on the cards
    assert "Selected 0 of 20" in text


def test_ticked_cards_are_counted_for_download(app):
    at = generate(app)
    picks(at)[0].check()
    picks(at)[3].check()
    at.run()
    assert "Selected 2 of 20" in page_text(at)
    assert not at.exception


def test_real_run_without_key_shows_error(app):
    at = generate(app, mock=False)
    assert not at.exception
    assert "ANTHROPIC_API_KEY" in at.error[0].value
    assert picks(at) == []


def test_mock_for_other_winner_shows_error(app):
    app.selectbox(key="sample").select("winner_027.txt").run()
    at = generate(app)
    assert not at.exception
    assert "012" in at.error[0].value


def test_page_is_in_english(app):
    at = generate(app)
    texts = [e.value for group in (at.title, at.subheader, at.markdown, at.caption) for e in group]
    texts += [e.label for group in (at.button, at.checkbox, at.selectbox, at.text_area, at.number_input,
                                     at.metric, at.expander) for e in group]
    cyrillic = [t for t in texts if re.search("[\u0400-\u04FF]", t)]
    assert cyrillic == []


WINNER_012 = (Path(__file__).resolve().parent.parent / "data" / "winner_012.txt").read_text(encoding="utf-8")


def test_sample_is_default_source_and_other_inputs_hidden(app):
    assert app.radio(key="source").value == "Sample from data/"
    assert [t.key for t in app.text_area if not t.disabled] == []   # editing only in "Paste" mode


def test_paste_mode_generates_from_pasted_text(app):
    app.radio(key="source").set_value("Paste text").run()
    assert [s.key for s in app.selectbox] == ["brief"]               # no sample to pick any more
    app.text_area(key="pasted").input(WINNER_012).run()
    at = generate(app)
    assert not at.error and len(picks(at)) == 20


def test_paste_mode_with_empty_text_shows_error(app):
    app.radio(key="source").set_value("Paste text").run()
    at = generate(app)
    assert not at.exception
    assert "Paste the winner script" in at.error[0].value


def test_upload_mode_without_file_shows_error(app):
    app.radio(key="source").set_value("Upload a file").run()
    at = generate(app)
    assert not at.exception
    assert "Upload a .txt" in at.error[0].value


def test_mock_error_says_how_to_fix(app):
    app.selectbox(key="sample").select("winner_027.txt").run()
    at = generate(app)
    assert "Untick Mock" in at.error[0].value


def test_brief_from_data_is_default(app):
    assert app.radio(key="brief_source").value == "From data/"
    assert app.selectbox(key="brief").value == "brand.yaml"


def test_brief_upload_without_file_shows_error(app):
    app.radio(key="brief_source").set_value("Upload a file").run()
    assert "brief" not in [s.key for s in app.selectbox]             # the data/ list is hidden
    at = generate(app)
    assert not at.exception
    assert "Upload a brand brief" in at.error[0].value
