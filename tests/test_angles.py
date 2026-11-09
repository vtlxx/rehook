import json

import pytest

from rehook.angles import EMOTIONS, FRAME_FORMATS, build_angles, validate_angles
from rehook.llm import LLM
from tests.fakes import FakeClient

PERSONAS = ["busy parents", "college students", "couples sharing laundry", "people who hate folding"]


def angles():
    base = [dict(angle_id=f"A{i + 1}", slug=f"s{i}", pain=f"pain {i}", persona=PERSONAS[i % 4],
                 emotion=EMOTIONS[i % 4], frame_format=FRAME_FORMATS[i % 5], is_safe=(i == 0))
            for i in range(6)]
    return {"angles": base}


def test_valid_angles_pass():
    validate_angles(angles(), PERSONAS)


@pytest.mark.parametrize("mutate,msg", [
    (lambda a: a["angles"].pop(), "exactly 6"),
    (lambda a: a["angles"][1].update(persona="dogs"), "persona"),
    (lambda a: a["angles"][1].update(emotion="rage"), "emotion"),
    (lambda a: a["angles"][1].update(slug="s0"), "unique"),
    (lambda a: [x.update(frame_format="pov") for x in a["angles"][:4]], "frame_format"),
    (lambda a: a["angles"][1].update(is_safe=True), "is_safe"),
    (lambda a: a["angles"][1].update(pain="Pain 0 ", persona=PERSONAS[0], emotion=EMOTIONS[0]), "differ"),
])
def test_invalid_angles(mutate, msg):
    data = angles()
    mutate(data)
    with pytest.raises(ValueError, match=msg):
        validate_angles(data, PERSONAS)


def test_build_angles_uses_llm():
    llm = LLM(client=FakeClient([json.dumps(angles())]))
    brand = {"personas": PERSONAS, "product": "x", "tone": "t", "facts": [], "offer": "o"}
    result = build_angles(llm, brand, {"winning_angle": {}})
    assert len(result) == 6 and result[0]["angle_id"] == "A1"


def test_missing_field_is_value_error_so_retry_happens():
    data = angles()
    del data["angles"][2]["pain"]
    with pytest.raises(ValueError):
        validate_angles(data, PERSONAS)
