import csv
import json
import re
from pathlib import Path

import numpy as np
import pytest

from rehook.__main__ import main
from rehook.llm import LLM
from rehook.pipeline import _read_brand, needs_topup, run_generate
from rehook.rank import CRITERIA
from rehook.similarity import DEFAULT_THRESHOLD, similarity_matrix, variant_text
from tests.fakes import FakeClient, prompt_of

ARGS = ["generate", "--winner", "data/winner_012.txt", "--brand", "data/brand.yaml",
        "--history", "data/launched.csv", "--ads", "data/ads_export.csv", "--mock"]
FIX = Path("tests/fixtures")


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_e2e_mock_meets_acceptance(tmp_path):
    out = tmp_path / "nested" / "out"
    assert main(ARGS + ["--out", str(out)]) == 0
    rows, rej = read(out / "variants.csv"), read(out / "rejected.csv")
    assert (out / "brief.md").exists()
    assert len(rows) >= 15 and len({r["angle_slug"] for r in rows}) >= 5
    m = similarity_matrix([variant_text(r) for r in rows])
    assert (m[np.triu_indices(len(rows), 1)] <= DEFAULT_THRESHOLD).all()
    assert any("price:$19" in r["rule_flags"] for r in rows)
    assert any(r["claim_ok"] == "False" for r in rows)
    assert any(r["reason"].startswith("similar_to_launched:") for r in rej)
    assert any(r["reason"].startswith("duplicate_of:") for r in rej)
    assert all(int(re.search(r"_H(\d+)_", r["variant_id"]).group(1)) >= 11 for r in rows)


def test_mock_without_optional_files(tmp_path):
    args = ["generate", "--winner", "data/winner_012.txt", "--brand", "data/brand.yaml", "--mock",
            "--out", str(tmp_path)]
    assert main(args) == 0
    ids = [r["variant_id"] for r in read(tmp_path / "variants.csv")]
    assert ids and all(i.startswith("SL_W012_AI_H") for i in ids)


def test_missing_key_without_mock(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(ARGS[:-1] + ["--out", str(tmp_path)]) == 1
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err


def test_mock_other_winner_fails_clearly(capsys, tmp_path):
    args = ["generate", "--winner", "data/winner_027.txt", "--brand", "data/brand.yaml", "--mock",
            "--out", str(tmp_path)]
    assert main(args) == 1
    assert "only for winner 012" in capsys.readouterr().err


def test_needs_topup():
    angles = [{"angle_id": f"A{i}"} for i in range(1, 7)]
    full = [{"angle_id": f"A{i}"} for i in range(1, 7) for _ in range(4)]
    assert needs_topup(full, angles, 20) == {}
    short = [k for k in full if k["angle_id"] != "A3"] + [{"angle_id": "A3"}]
    assert needs_topup(short, angles, 20) == {"A3": 5}


# --- top-up: a fake model that replies based on markers in the prompt ---

def fixture_text(name):
    return (FIX / f"{name}.json").read_text()


SAME_A3 = {"variants": [
    {"hook_type": t, "hook_vo": "Whose sock is this? Nobody in our house knows" + p,
     "on_screen_text": "Nobody claims this sock", "first_frame": "Talking head.", "bridge_line": ""}
    for t, p in zip(["question", "confession", "contrast", "curiosity", "pov"], [".", "!", "?", "...", "!!"])]}


def keys_in(prompt):
    return re.findall(r'"key": "(v\d+)"', prompt)


def router(kwargs):
    prompt = prompt_of(kwargs)
    if "structural parts" in prompt:
        return fixture_text("parse_winner")
    if "Build exactly 6 angles" in prompt:
        return fixture_text("angles")
    if "Write hooks for THIS angle" in prompt:
        this_angle = prompt.split("Write hooks for THIS angle:")[1].split("Other angles")[0]
        angle_id = json.loads(fixture_text("angles"))["angles"]
        slug_to_id = {a["slug"]: a["angle_id"] for a in angle_id}
        aid = next(i for s, i in slug_to_id.items() if f'"{s}"' in this_angle)
        if "these:\nnone" not in prompt:                        # top-up round
            return fixture_text("generate_A3")
        return json.dumps(SAME_A3) if aid == "A3" else fixture_text(f"generate_{aid}")
    if "compliance reviewer" in prompt:
        return json.dumps({"results": [{"key": k, "claim_ok": True, "claim_note": ""} for k in keys_in(prompt)]})
    if "Score hook variants" in prompt:
        return json.dumps({"results": [dict(key=k, **dict.fromkeys(CRITERIA, 3)) for k in keys_in(prompt)]})
    raise AssertionError("unexpected prompt")


def test_topup_runs_one_round_for_short_angles(tmp_path):
    client = FakeClient(router)
    result = run_generate(LLM(client=client), "data/winner_012.txt", "data/brand.yaml", "data/launched.csv",
                          "data/ads_export.csv", 20, str(tmp_path), DEFAULT_THRESHOLD, 42)
    assert result["topup"] == {"A3": 5}
    topup_calls = [c for c in client.calls if "Write hooks for THIS angle" in prompt_of(c)
                   and "these:\nnone" not in prompt_of(c)]
    assert len(topup_calls) == 1 and len(client.calls) == 13
    a3 = [v for v in result["selected"] if v["angle_id"] == "A3"]
    assert len(a3) >= 2
    numbers = sorted(int(re.search(r"_H(\d+)_", v["variant_id"]).group(1))
                     for v in result["selected"] + result["rejected"])
    assert numbers == list(range(11, 11 + 35))


def test_mock_with_other_n_fails_clearly(capsys, tmp_path):
    assert main(ARGS + ["--n", "10", "--out", str(tmp_path)]) == 1
    assert "--n 20" in capsys.readouterr().err


def test_mock_forced_topup_fails_clearly(capsys, tmp_path):
    assert main(ARGS + ["--sim-threshold", "0.2", "--out", str(tmp_path)]) == 1
    assert "default --sim-threshold" in capsys.readouterr().err


def test_history_with_wrong_columns_names_the_file(capsys, tmp_path):
    bad = tmp_path / "hist.csv"
    bad.write_text("name,text\nx,y\n")
    args = ["generate", "--winner", "data/winner_012.txt", "--brand", "data/brand.yaml", "--history", str(bad),
            "--mock", "--out", str(tmp_path)]
    assert main(args) == 1
    err = capsys.readouterr().err
    assert "hist.csv" in err and "ad_name" in err


def test_brand_missing_key_names_the_file(capsys, tmp_path):
    brand = tmp_path / "brand.yaml"
    brand.write_text("product: x\n")
    args = ["generate", "--winner", "data/winner_012.txt", "--brand", str(brand), "--mock", "--out", str(tmp_path)]
    assert main(args) == 1
    err = capsys.readouterr().err
    assert "brand.yaml" in err and "limits" in err


def test_read_brand_broken_yaml_names_the_file(tmp_path):
    path = tmp_path / "brand_x.yaml"
    path.write_text('product: "unclosed\noffer: x\n', encoding="utf-8")
    with pytest.raises(ValueError, match="brand_x.yaml: not valid YAML"):
        _read_brand(str(path))


def test_read_brand_not_a_mapping(tmp_path):
    path = tmp_path / "brand_x.yaml"
    path.write_text("- product\n- offer\n", encoding="utf-8")
    with pytest.raises(ValueError, match="brand_x.yaml: expected keys"):
        _read_brand(str(path))
