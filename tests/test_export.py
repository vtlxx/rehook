import csv

from rehook.export import VARIANT_COLUMNS, REJECTED_COLUMNS, write_brief, write_rejected_csv, write_variants_csv

ROW = {"variant_id": "SL_W012_AI_H11_a", "winner_id": "012", "angle_id": "A1", "angle_slug": "a", "pain": "p",
       "persona": "busy parents", "emotion": "humor", "frame_format": "pov", "hook_type": "question",
       "hook_vo": 'Lost one, again? "Seriously"', "on_screen_text": "Where do my socks go?!", "first_frame": "ff",
       "bridge_line": "", "score": 7.8, "max_similarity": 0.31, "rule_flags": ["price:$19", "caps:NO WAY"],
       "claim_ok": False, "claim_note": "'cures' — health", "key": "v1"}


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_csv_roundtrip_with_commas_and_quotes(tmp_path):
    write_variants_csv([ROW], tmp_path / "v.csv")
    back = read(tmp_path / "v.csv")[0]
    assert list(back) == VARIANT_COLUMNS
    assert back["hook_vo"] == ROW["hook_vo"] and back["rule_flags"] == "price:$19; caps:NO WAY"
    assert back["claim_ok"] == "False"


def test_rejected_csv(tmp_path):
    write_rejected_csv([dict(ROW, reason="duplicate_of:SL_W012_AI_H12_b")], tmp_path / "r.csv")
    back = read(tmp_path / "r.csv")[0]
    assert list(back) == REJECTED_COLUMNS and back["reason"] == "duplicate_of:SL_W012_AI_H12_b"


def test_brief_marks_flags(tmp_path):
    angle = {"angle_id": "A1", "slug": "a", "pain": "p", "persona": "busy parents", "emotion": "humor",
             "frame_format": "pov", "is_safe": True}
    write_brief(tmp_path / "b.md", {"winner_id": "012", "body": "[3-8s] body"},
                {"segments": [], "winning_angle": {"pain": "p", "persona": "x", "emotion": "e", "why": "w"}},
                [angle], [ROW], ["angle A2 has only 1 variant(s) after filtering"])
    md = (tmp_path / "b.md").read_text()
    assert "⚠️" in md and "price:$19" in md and "health" in md and "[3-8s] body" in md
    assert "only 1 variant" in md and "ordering only" in md and "SL_W012_AI_H11_a" in md
