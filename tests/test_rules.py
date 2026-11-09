from rehook.rules import apply_rules, check_variant, count_words

BRAND = {
    "price_rules": ["$29"],
    "banned_words": ["guaranteed", "miracle", "cure"],
    "banned_claims": ["never lose a sock again guaranteed", "medical or health benefits", "free", "lifetime"],
    "limits": {"hook_vo_max_words": 12, "on_screen_max_words": 7},
}


def v(vo="Lost a sock again?", on="Where do my socks go?!", bridge=""):
    return {"hook_vo": vo, "on_screen_text": on, "bridge_line": bridge}


def test_count_words_ignores_symbols():
    assert count_words("5 pairs / $29") == 3


def test_clean_variant_has_no_flags():
    assert check_variant(v(), BRAND) == []


def test_too_long_vo_and_onscreen():
    flags = check_variant(v(vo=" ".join(["word"] * 14), on=" ".join(["w"] * 9)), BRAND)
    assert "vo_too_long:14>12" in flags and "onscreen_too_long:9>7" in flags


def test_wrong_price_flagged_allowed_price_not():
    assert check_variant(v(on="5 pairs for $19"), BRAND) == ["price:$19"]
    assert check_variant(v(on="5 pairs for $29.00"), BRAND) == []


def test_banned_word_whole_word_and_forms():
    assert check_variant(v(vo="A miracle for your laundry"), BRAND) == ["banned_word:miracle"]
    assert check_variant(v(vo="Results guaranteed"), BRAND) == ["banned_word:guaranteed"]
    assert check_variant(v(vo="Keeps pairs secure"), BRAND) == []
    assert check_variant(v(vo="It cures sock loss"), BRAND) == ["banned_word:cure"]


def test_short_banned_claims_checked_by_code():
    assert check_variant(v(on="Free shipping today"), BRAND) == ["banned_claim:free"]
    assert check_variant(v(bridge="Lifetime of matched pairs"), BRAND) == ["banned_claim:lifetime"]


def test_all_caps_more_than_one_word():
    assert check_variant(v(on="They LOCK TOGETHER"), BRAND) == ["caps:LOCK TOGETHER"]
    assert check_variant(v(vo="POV: I lost a sock"), BRAND) == []


def test_apply_rules_sets_field():
    items = [v(), v(on="$19 only")]
    apply_rules(items, BRAND)
    assert items[0]["rule_flags"] == [] and items[1]["rule_flags"] == ["price:$19"]
