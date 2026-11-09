"""Сторінка для дизайнерів: `streamlit run app.py`.

Ядро те саме, що й у CLI (run_generate); тут лише введення, картки й вибір.
"""
import os
import tempfile
import time
from pathlib import Path

import anthropic
import streamlit as st

from rehook.export import variant_warnings, variants_csv_text
from rehook.llm import LLM, LLMError
from rehook.pipeline import run_generate
from rehook.similarity import DEFAULT_THRESHOLD

DATA = Path(__file__).resolve().parent / "data"
SAMPLES = sorted(p.name for p in DATA.glob("winner_*.txt"))
BRIEFS = sorted(p.name for p in DATA.glob("*.yaml"))

st.set_page_config(page_title="rehook", page_icon="🧦", layout="wide")
st.title("rehook — new hooks for a winning ad")
st.caption("Only the first 3 seconds change; the rest of the script stays as in the winner.")

# ── Введення ────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])
with left:
    # Явний вибір джерела: показуємо лише одне поле, щоб було видно, який скрипт піде в роботу.
    source = st.radio("Winner script", ["Sample from data/", "Upload a file", "Paste text"],
                      horizontal=True, key="source")
    text = ""
    if source == "Sample from data/":
        sample = st.selectbox("Sample script", SAMPLES, key="sample")
        text = (DATA / sample).read_text(encoding="utf-8")
        st.text_area("Preview", value=text, height=200, disabled=True, key=f"preview_{sample}")
    elif source == "Upload a file":
        uploaded = st.file_uploader("Script (.txt) with a WINNER_ID line, e.g. examples/winner_044.txt", type="txt")
        if uploaded is not None:
            text = uploaded.getvalue().decode("utf-8")
            st.text_area("Preview", value=text, height=200, disabled=True, key=f"preview_{uploaded.name}")
    else:
        text = st.text_area("Paste the script", height=220, key="pasted",
                            placeholder='WINNER_ID: 044\n[0-3s] VO: "…"  ON-SCREEN: "…"  VISUAL: …\n[3-8s] VO: "…"')
with right:
    brief = st.selectbox("Brand brief", BRIEFS, key="brief")
    n = st.number_input("Variants to keep", min_value=6, max_value=60, value=20, step=1, key="n")
    mock = st.checkbox("Mock: recorded model replies, no key needed (winner 012 only, 20 variants)",
                       value=not os.environ.get("ANTHROPIC_API_KEY"), key="mock")
    with st.expander("Launch history (optional)"):
        history_file = st.file_uploader("Launched hooks (launched.csv)", type="csv")
        ads_file = st.file_uploader("Ads Manager export (ads_export.csv)", type="csv")
        st.caption("If nothing is uploaded, data/launched.csv and data/ads_export.csv are used.")


def _input_path(folder: Path, name: str, upload, default: Path) -> str:
    if upload is None:
        return str(default)
    path = folder / name
    path.write_bytes(upload.getvalue())
    return str(path)


def generate() -> None:
    if not text.strip():
        raise ValueError("Upload a .txt script first" if source == "Upload a file"
                         else "Paste the winner script first (it starts with a WINNER_ID line)")
    if not mock and not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("ANTHROPIC_API_KEY is not set: tick Mock, or restart the page with the key "
                       "(see README → Designer page)")
    llm = LLM(mock=mock)
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        winner_path = folder / "winner.txt"
        winner_path.write_text(text, encoding="utf-8")
        started = time.monotonic()
        result = run_generate(llm, str(winner_path), str(DATA / brief),
                              _input_path(folder, "launched.csv", history_file, DATA / "launched.csv"),
                              _input_path(folder, "ads_export.csv", ads_file, DATA / "ads_export.csv"),
                              int(n), str(folder / "out"), DEFAULT_THRESHOLD, 42)
        result["brief_md"] = (folder / "out" / "brief.md").read_text(encoding="utf-8")
    result["cost"], result["elapsed"], result["mock"] = llm.cost(), time.monotonic() - started, mock
    st.session_state["result"] = result
    for key in [k for k in st.session_state if str(k).startswith("pick_")]:
        del st.session_state[key]  # нова генерація — старі галочки не потрібні


if st.button("Generate", type="primary", key="generate"):
    st.session_state.pop("result", None)
    try:
        with st.spinner("Breaking down the winner, building angles, generating and checking variants…"):
            generate()
    except (LLMError, ValueError, KeyError, OSError, anthropic.APIError) as e:
        hint = " Untick Mock to run the real model on this script." if mock and "mock" in str(e).lower() else ""
        st.error(f"Error: {e}.{hint}" if hint else f"Error: {e}")

# ── Результат ───────────────────────────────────────────────────────────────
result = st.session_state.get("result")
if result:
    selected, rejected = result["selected"], result["rejected"]
    cols = st.columns(4)
    cols[0].metric("Generated", result["generated"])
    cols[1].metric("Dropped", len(rejected))
    cols[2].metric("Selected", len(selected))
    cols[3].metric("Angles", len({v["angle_id"] for v in selected}))
    st.caption(f"Cost ${result['cost']:.3f} · time {result['elapsed']:.0f} s"
               + (" · mock: model replies were recorded in advance, no API calls" if result["mock"] else ""))
    for warning in result["warnings"]:
        st.warning(warning)

    wa = result["parsed"]["winning_angle"]
    with st.expander("Why the winner works"):
        st.markdown(f"**Pain:** {wa['pain']}  \n**Persona:** {wa['persona']}  \n"
                    f"**Emotion:** {wa['emotion']}  \n**Why:** {wa['why']}")

    st.markdown("Tick the variants you will work on. The score is only an ordering, not a forecast: the test decides.")
    for angle in result["angles"]:
        items = [v for v in selected if v["angle_id"] == angle["angle_id"]]
        if not items:
            continue
        kind = "safe" if angle.get("is_safe") else "bold"
        st.subheader(f"{angle['angle_id']} · {angle['slug']} ({kind})")
        st.caption(f"Pain: {angle['pain']} · Persona: {angle['persona']} · Emotion: {angle['emotion']} · "
                   f"First frame: {angle['frame_format']}")
        grid = st.columns(3)
        for i, v in enumerate(items):
            with grid[i % 3].container(border=True):
                st.checkbox(f"**{v['score']}** · {v['hook_type']} · `{v['variant_id']}`", key=f"pick_{v['variant_id']}")
                lines = [f"🎙 {v['hook_vo']}", f"🔤 {v['on_screen_text']}", f"🎬 {v['first_frame']}"]
                if v.get("bridge_line"):
                    lines.append(f"🔗 {v['bridge_line']}")
                lines += [f":red[⚠️ {note}]" for note in variant_warnings(v)]
                st.markdown("  \n".join(lines))

    chosen = [v for v in selected if st.session_state.get(f"pick_{v['variant_id']}")]
    st.divider()
    st.markdown(f"**Selected {len(chosen)} of {len(selected)}**")
    winner_id = result["winner"]["winner_id"]
    down = st.columns(2)
    down[0].download_button("Download selected as CSV", variants_csv_text(chosen), type="primary",
                            file_name=f"variants_W{winner_id}_selected.csv", mime="text/csv", disabled=not chosen)
    down[1].download_button("Download brief.md (all selected variants)", result["brief_md"],
                            file_name=f"brief_W{winner_id}.md", mime="text/markdown")
    with st.expander(f"Dropped variants ({len(rejected)})"):
        st.dataframe([{k: r.get(k, "") for k in ("variant_id", "hook_vo", "score", "reason")} for r in rejected],
                     hide_index=True, use_container_width=True)
