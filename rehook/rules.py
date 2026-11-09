"""Step 4: code checks, no LLM.

Flagged variants are not removed: flags only tell the designer
what to look at.
"""
import re

# Price: a dollar sign and a number, e.g. "$19", "$ 29", "$29.00".
PRICE_RE = re.compile(r"\$\s?(\d+(?:[.,]\d+)?)")
# Two or more words in a row in capitals (each with 2+ letters).
CAPS_RE = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b")


def count_words(text: str) -> int:
    """A word is a token with at least one letter or digit ("/" does not count)."""
    return sum(1 for token in text.split() if re.search(r"[A-Za-z0-9]", token))


def word_pattern(word: str) -> re.Pattern:
    """Whole word, case-insensitive, + simple endings (s/es/d/ed).

    So "cure" catches "cures" but not "secure".
    """
    return re.compile(rf"\b{re.escape(word)}(?:s|es|d|ed)?\b", re.IGNORECASE)


def _to_number(text: str) -> float:
    return float(text.replace(",", "."))


def _short_claims(brand: dict) -> list[str]:
    """Short banned claims (1–2 words, e.g. "free") are checked by code.

    Long descriptive ones ("medical or health benefits") only by the model in step 5.
    """
    return [claim for claim in brand.get("banned_claims", []) if len(claim.split()) <= 2]


def check_variant(variant: dict, brand: dict) -> list[str]:
    """Returns the variant's flags without duplicates, in the order found."""
    flags = []
    limits = brand["limits"]

    vo_words = count_words(variant["hook_vo"])
    if vo_words > limits["hook_vo_max_words"]:
        flags.append(f"vo_too_long:{vo_words}>{limits['hook_vo_max_words']}")
    on_words = count_words(variant["on_screen_text"])
    if on_words > limits["on_screen_max_words"]:
        flags.append(f"onscreen_too_long:{on_words}>{limits['on_screen_max_words']}")

    allowed_prices = {_to_number(m) for rule in brand["price_rules"] for m in PRICE_RE.findall(rule)}
    texts = [variant["hook_vo"], variant["on_screen_text"], variant.get("bridge_line", "")]
    for text in texts:
        for match in PRICE_RE.finditer(text):
            if _to_number(match.group(1)) not in allowed_prices:
                flags.append(f"price:{match.group(0)}")
        for word in brand["banned_words"]:
            if word_pattern(word).search(text):
                flags.append(f"banned_word:{word}")
        for claim in _short_claims(brand):
            if word_pattern(claim).search(text):
                flags.append(f"banned_claim:{claim}")
        for match in CAPS_RE.finditer(text):
            flags.append(f"caps:{match.group(0)}")

    return list(dict.fromkeys(flags))  # drop duplicates, keep order


def apply_rules(variants: list[dict], brand: dict) -> None:
    """Writes the flags into each variant's rule_flags field."""
    for variant in variants:
        variant["rule_flags"] = check_variant(variant, brand)
