import json
from pathlib import Path

import yaml

from rehook.angles import validate_angles
from rehook.claims import validate_claims
from rehook.generate import validate_variants
from rehook.parse_winner import validate_parsed
from rehook.rank import validate_rank
from rehook.rules import check_variant

FIX = Path("tests/fixtures")
BRAND = yaml.safe_load(Path("data/brand.yaml").read_text())


def load(name):
    return json.loads((FIX / f"{name}.json").read_text())


def all_variants():
    out = []
    for i in range(1, 7):
        validate_variants(load(f"generate_A{i}"), 5)
        out += load(f"generate_A{i}")["variants"]
    return out


def test_fixtures_pass_validators():
    validate_parsed(load("parse_winner"))
    validate_angles(load("angles"), BRAND["personas"])
    keys = [f"v{i}" for i in range(1, 31)]
    validate_claims(load("claims"), keys)
    validate_rank(load("rank"), keys)


def test_fixtures_contain_demo_cases():
    flags = [check_variant(v, BRAND) for v in all_variants()]
    assert any("price:$19" in f for f in flags)
    assert any("banned_claim:free" in f for f in flags)
    assert any(not r["claim_ok"] for r in load("claims")["results"])
