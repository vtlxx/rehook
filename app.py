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
st.title("rehook — нові хуки до ролика-переможця")
st.caption("Змінюються лише перші 3 секунди; решта скрипту лишається як у переможця.")

# ── Введення ────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])
with left:
    sample = st.selectbox("Приклад скрипту з data/", SAMPLES, key="sample")
    uploaded = st.file_uploader("…або завантажте свій скрипт (.txt)", type="txt")
    # key залежить від прикладу: при виборі іншого прикладу текст оновлюється
    text = st.text_area("Скрипт переможця (можна редагувати або вставити свій)",
                        value=(DATA / sample).read_text(encoding="utf-8"), height=220, key=f"text_{sample}")
    if uploaded is not None:
        text = uploaded.getvalue().decode("utf-8")
        st.caption(f"Використовується завантажений файл: {uploaded.name}")
with right:
    brief = st.selectbox("Бриф бренду", BRIEFS, key="brief")
    n = st.number_input("Скільки варіантів лишити", min_value=6, max_value=60, value=20, step=1, key="n")
    mock = st.checkbox("Mock: записані відповіді моделі, без ключа (лише переможець 012, 20 варіантів)",
                       value=not os.environ.get("ANTHROPIC_API_KEY"), key="mock")
    with st.expander("Історія запусків (необов'язково)"):
        history_file = st.file_uploader("Запущені хуки (launched.csv)", type="csv")
        ads_file = st.file_uploader("Вигрузка з Ads Manager (ads_export.csv)", type="csv")
        st.caption("Без завантаження беруться data/launched.csv і data/ads_export.csv.")


def _input_path(folder: Path, name: str, upload, default: Path) -> str:
    if upload is None:
        return str(default)
    path = folder / name
    path.write_bytes(upload.getvalue())
    return str(path)


def generate() -> None:
    if not mock and not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("ANTHROPIC_API_KEY не задано: увімкніть mock або запустіть сторінку з ключем")
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


if st.button("Згенерувати", type="primary", key="generate"):
    st.session_state.pop("result", None)
    try:
        with st.spinner("Розбираю переможця, будую кути, генерую й перевіряю варіанти…"):
            generate()
    except (LLMError, ValueError, KeyError, OSError, anthropic.APIError) as e:
        st.error(f"Помилка: {e}")

# ── Результат ───────────────────────────────────────────────────────────────
result = st.session_state.get("result")
if result:
    selected, rejected = result["selected"], result["rejected"]
    cols = st.columns(4)
    cols[0].metric("Згенеровано", result["generated"])
    cols[1].metric("Відсіяно", len(rejected))
    cols[2].metric("Відібрано", len(selected))
    cols[3].metric("Кутів", len({v["angle_id"] for v in selected}))
    st.caption(f"Вартість ${result['cost']:.3f} · час {result['elapsed']:.0f} с"
               + (" · mock: відповіді моделі записані заздалегідь, API не викликався" if result["mock"] else ""))
    for warning in result["warnings"]:
        st.warning(warning)

    wa = result["parsed"]["winning_angle"]
    with st.expander("Чому переможець спрацював"):
        st.markdown(f"**Біль:** {wa['pain']}  \n**Персона:** {wa['persona']}  \n"
                    f"**Емоція:** {wa['emotion']}  \n**Чому:** {wa['why']}")

    st.markdown("Позначте варіанти, які берете в роботу. Оцінка — лише порядок, не прогноз: вирішує тест.")
    for angle in result["angles"]:
        items = [v for v in selected if v["angle_id"] == angle["angle_id"]]
        if not items:
            continue
        kind = "безпечний" if angle.get("is_safe") else "сміливий"
        st.subheader(f"{angle['angle_id']} · {angle['slug']} ({kind})")
        st.caption(f"Біль: {angle['pain']} · Персона: {angle['persona']} · Емоція: {angle['emotion']} · "
                   f"Перший кадр: {angle['frame_format']}")
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
    st.markdown(f"**Обрано {len(chosen)} з {len(selected)}**")
    winner_id = result["winner"]["winner_id"]
    down = st.columns(2)
    down[0].download_button("Завантажити CSV обраних", variants_csv_text(chosen), type="primary",
                            file_name=f"variants_W{winner_id}_selected.csv", mime="text/csv", disabled=not chosen)
    down[1].download_button("Завантажити brief.md (усі відібрані)", result["brief_md"],
                            file_name=f"brief_W{winner_id}.md", mime="text/markdown")
    with st.expander(f"Відсіяні варіанти ({len(rejected)})"):
        st.dataframe([{k: r.get(k, "") for k in ("variant_id", "hook_vo", "score", "reason")} for r in rejected],
                     hide_index=True, use_container_width=True)
