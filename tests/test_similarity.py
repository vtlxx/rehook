import csv

from rehook.similarity import DEFAULT_THRESHOLD, filter_similar, similarity_matrix, variant_text

# Калібрувальні пари: та сама думка іншими словоформами / з перестановкою (дублі)
DUPES = [
    ("I used to lose a sock every laundry day. Where do my socks go?!",
     "I kept losing socks every single laundry day. Where did my socks go?"),
    ("Lost another sock in the wash? Single sock club",
     "Lost one more sock in the washer? Single socks club"),
    ("My kid has never worn a matching pair. Zero matching pairs",
     "My kids have never worn matching pairs. Zero matching pair"),
    ("I spent 20 minutes every Sunday matching socks. 20 min of sock sorting?",
     "Every Sunday I spend 20 minutes matching socks. 20 minutes of sorting socks"),
    ("POV: you pull out one sock. Just one. One sock. Again.",
     "POV: you pulled out one sock, just one. One sock again"),
    ("My washing machine has a sock-eating habit. The washer ate it",
     "My washing machine has a sock eating habit! The washer ate them"),
    ("Why does the dryer only keep one of each? One of each. Why?",
     "Why does my dryer keep only one of each sock? One of each, why?"),
    ("We argue about whose socks are whose. Whose socks are these?",
     "We always argue about whose socks are whose. Whose sock is this?"),
    ("Five kids, one washer, zero matching socks. Zero matching socks",
     "Five kids and one washer means zero matching socks. Zero matching socks!"),
    ("Dorm laundry ate half my socks this semester. Dorm laundry strikes again",
     "Dorm laundry ate half of my socks this semester. Dorm laundry strikes again!"),
]

# Та сама тема і спільні слова (sock/laundry/pair), але інша ідея — не дублі
NOT_DUPES = [
    ("Lost a sock again? Socks that lock", "Folding laundry takes forever? Pairs come out matched"),
    ("I used to lose a sock every laundry day. Where do my socks go?!",
     "My toddler thinks socks come in singles. Socks come in singles?"),
    ("Mismatched socks at school drop-off. Every day.", "We share a washer and somehow lose his socks."),
    ("POV: it's 7:58 and you need two matching socks. 7:58 sock panic",
     "POV: you open the dryer and every pair is still together. Still paired"),
    ("I timed my sock sorting. It was embarrassing. I timed it",
     "My Sunday hobby: sock matching. Not by choice. Sunday hobby"),
    ("Where do lost socks actually go? The sock mystery", "Lost another sock in the wash? Single sock club"),
    ("I own forty socks and no pairs. 40 socks, 0 pairs", "Five kids, one washer, zero matching socks."),
    ("Laundry day used to be a sock hunt. No more sock hunts",
     "Dorm laundry ate half my socks this semester. Dorm laundry strikes again"),
    ("Tiny socks, tiny magnets, zero arguments. Tiny magnets, big win",
     "We argue about whose socks are whose. Whose socks are these?"),
    ("What if socks came out of the dryer already paired? Already paired?",
     "Why does the dryer only keep one of each? One of each. Why?"),
]

with open("data/launched.csv", newline="", encoding="utf-8") as f:
    HISTORY_TEXTS = [variant_text(r) for r in csv.DictReader(f)]


def calibrated(pairs):
    texts = [t.lower() for p in pairs for t in p] + HISTORY_TEXTS   # реалістичний корпус для IDF
    m = similarity_matrix(texts)
    return [m[2 * i, 2 * i + 1] for i in range(len(pairs))]


def test_dupes_above_threshold():
    assert min(calibrated(DUPES)) > DEFAULT_THRESHOLD


def test_not_dupes_below_threshold():
    assert max(calibrated(NOT_DUPES)) <= DEFAULT_THRESHOLD


def mk(vid, score, vo, on="", angle="A1"):
    return {"variant_id": vid, "score": score, "hook_vo": vo, "on_screen_text": on, "angle_id": angle}


def test_filter_keeps_better_duplicate_and_flags_history():
    hist = [{"ad_name": "SL_W012_MAN_H01_x", "hook_vo": "I used to lose a sock every laundry day.",
             "on_screen_text": "Where do my socks go?!"}]
    vs = [mk("V1", 6.0, "Kids never wear matching socks", "Mismatched again"),
          mk("V2", 8.0, "Kids never wear matching socks!", "Mismatched again?"),
          mk("V3", 9.0, "I used to lose a sock every single laundry day.", "Where do my socks go?!"),
          mk("V4", 7.0, "Sorting socks steals my Sunday", "20 minutes of sorting")]
    kept, rejected = filter_similar(vs, hist, DEFAULT_THRESHOLD)
    assert [k["variant_id"] for k in kept] == ["V2", "V4"]
    reasons = {r["variant_id"]: r["reason"] for r in rejected}
    assert reasons == {"V3": "similar_to_launched:SL_W012_MAN_H01_x", "V1": "duplicate_of:V2"}
    assert all(k["max_similarity"] <= DEFAULT_THRESHOLD for k in kept)


def test_filter_without_history():
    kept, rejected = filter_similar([mk("V1", 5.0, "a b c"), mk("V2", 4.0, "x y z")], [], DEFAULT_THRESHOLD)
    assert len(kept) == 2 and rejected == []
