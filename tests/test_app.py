"""Сторінка для дизайнерів (app.py): запускаємо її без браузера через Streamlit AppTest."""
import re

import pytest
from streamlit.testing.v1 import AppTest

APP = "../app.py"  # шлях відносно цього файлу


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
    assert len(at.subheader) == 6                      # картки згруповані за 6 кутами
    text = page_text(at)
    assert "price:$19" in text and "banned_claim:free" in text   # прапорці видно на картках
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
    cyrillic = [t for t in texts if re.search("[А-Яа-яЇїІіЄєҐґ]", t)]
    assert cyrillic == []
