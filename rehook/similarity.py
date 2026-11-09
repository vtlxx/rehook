"""Step 6: similarity filter (code, no LLM).

This is an approximate check of the TEXT. Meta Andromeda also compares image and audio,
so first-frame variety is ensured separately, at the angle step.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Chosen by calibration on ~20 labelled pairs (tests/test_similarity.py):
#   word 1–2:       dupes from 0.36, non-dupes up to 0.11 (3 of 10 dupes below 0.6)
#   char_wb 3–5:    dupes from 0.53, non-dupes up to 0.20: the widest gap.
# Character n-grams catch different word forms ("lose a sock" ≈ "losing socks"),
# which word-level TF-IDF misses on short phrases.
ANALYZER = "char_wb"
NGRAM_RANGE = (3, 5)
STOP_WORDS = None
# The threshold sits inside the gap (0.20…0.53), closer to the dupes: better to let
# a doubtful paraphrase through than to drop too much. At 0.45 merely
# related hooks were dropped ("dorm laundry day…" vs "dorm laundry ate my socks…" = 0.47).
DEFAULT_THRESHOLD = 0.50


def variant_text(item: dict) -> str:
    """Text to compare: voice-over + on-screen text."""
    return f"{item['hook_vo']} {item['on_screen_text']}".lower()


def similarity_matrix(texts: list[str]):
    """TF-IDF cosine similarity; vocabulary and IDF are built on all the given texts.

    The corpus is small (dozens of phrases), so IDF is unstable: the same pair can get
    a slightly different similarity in different runs.
    """
    vectorizer = TfidfVectorizer(analyzer=ANALYZER, ngram_range=NGRAM_RANGE, stop_words=STOP_WORDS)
    return cosine_similarity(vectorizer.fit_transform(texts))


def filter_similar(variants: list[dict], history: list[dict], threshold: float) -> tuple[list[dict], list[dict]]:
    """Greedy filtering: from the best score to the worst.

    1) similar to a launched hook → similar_to_launched:<ad_name>
    2) similar to a variant already kept → duplicate_of:<variant_id>
    3) otherwise keep it.
    """
    ordered = sorted(variants, key=lambda v: v["score"], reverse=True)
    texts = [variant_text(v) for v in ordered] + [variant_text(h) for h in history]
    sim = similarity_matrix(texts) if texts else []
    n = len(ordered)

    kept_idx, rejected = [], []
    for i, variant in enumerate(ordered):
        hist_scores = [(sim[i][n + j], h["ad_name"]) for j, h in enumerate(history)]
        best_hist = max(hist_scores, default=(0.0, ""))
        best_kept = max(((sim[i][k], ordered[k]["variant_id"]) for k in kept_idx), default=(0.0, ""))
        if best_hist[0] > threshold:
            variant["reason"] = f"similar_to_launched:{best_hist[1]}"
            rejected.append(variant)
        elif best_kept[0] > threshold:
            variant["reason"] = f"duplicate_of:{best_kept[1]}"
            rejected.append(variant)
        else:
            kept_idx.append(i)

    # max_similarity is computed only against kept variants and history (dropped dupes do not count).
    for i in kept_idx:
        others = [sim[i][k] for k in kept_idx if k != i] + [sim[i][n + j] for j in range(len(history))]
        ordered[i]["max_similarity"] = round(float(max(others, default=0.0)), 2)
    return [ordered[i] for i in kept_idx], rejected
