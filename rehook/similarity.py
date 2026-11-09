"""Крок 6: фільтр схожості (кодом, без LLM).

Це наближена перевірка ТЕКСТУ. Meta Andromeda порівнює ще й картинку та звук,
тому різноманітність перших кадрів забезпечуємо окремо — на кроці кутів.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Обрано калібруванням на ~20 розмічених парах (tests/test_similarity.py):
#   word 1–2:       дублі від 0.36, не-дублі до 0.11 (3 дублі з 10 нижче 0.6)
#   char_wb 3–5:    дублі від 0.53, не-дублі до 0.20 — найбільший зазор.
# Символьні n-грами ловлять різні форми слів ("lose a sock" ≈ "losing socks"),
# яких на коротких фразах словесний TF-IDF не бачить.
ANALYZER = "char_wb"
NGRAM_RANGE = (3, 5)
STOP_WORDS = None
# Поріг усередині зазору (0.20…0.53), ближче до дублів: краще пропустити
# сумнівну перефразу, ніж викинути зайве. На 0.45 відсіювалися вже просто
# споріднені хуки ("dorm laundry day…" vs "dorm laundry ate my socks…" = 0.47).
DEFAULT_THRESHOLD = 0.50


def variant_text(item: dict) -> str:
    """Текст для порівняння: голос за кадром + текст на екрані."""
    return f"{item['hook_vo']} {item['on_screen_text']}".lower()


def similarity_matrix(texts: list[str]):
    """Косинусна схожість TF-IDF; словник і IDF будуються на всіх переданих текстах.

    Корпус малий (десятки фраз), тож IDF нестабільний: та сама пара в різних
    запусках може отримати трохи різну схожість.
    """
    vectorizer = TfidfVectorizer(analyzer=ANALYZER, ngram_range=NGRAM_RANGE, stop_words=STOP_WORDS)
    return cosine_similarity(vectorizer.fit_transform(texts))


def filter_similar(variants: list[dict], history: list[dict], threshold: float) -> tuple[list[dict], list[dict]]:
    """Жадібний відсів: від кращої оцінки до гіршої.

    1) схожий на вже запущений хук → similar_to_launched:<ad_name>
    2) схожий на вже залишений варіант → duplicate_of:<variant_id>
    3) інакше лишаємо.
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

    # max_similarity — лише серед залишених та історії (відсіяні дублі не рахуємо).
    for i in kept_idx:
        others = [sim[i][k] for k in kept_idx if k != i] + [sim[i][n + j] for j in range(len(history))]
        ordered[i]["max_similarity"] = round(float(max(others, default=0.0)), 2)
    return [ordered[i] for i in kept_idx], rejected
