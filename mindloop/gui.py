"""MINDLOOP browser GUI. Thin view over MindloopEngine — no learning logic here.

Run: python -m mindloop gui   (or: streamlit run mindloop/gui.py)
Design: plain native Streamlit, reading width, no custom theme.
Streamlit is imported lazily so the CLI never requires it.
"""
from __future__ import annotations
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CSS = """
<style>
.block-container { max-width: 760px !important; }
</style>
"""


def _engine():
    import streamlit as st
    if "engine" not in st.session_state:
        if __package__ in (None, ""):
            from mindloop.engine import MindloopEngine, make_llm
            from mindloop.config import load_config
        else:
            from .engine import MindloopEngine, make_llm
            from .config import load_config
        cfg = load_config()
        st.session_state["engine"] = MindloopEngine(llm=make_llm(cfg))
    return st.session_state["engine"]


def _answer_card(ans) -> None:
    import streamlit as st
    if ans.refused:
        st.warning(ans.text)
        return
    with st.container(border=True):
        st.write(ans.text)
    if ans.citations:
        st.caption(" · ".join(
            f"{c.filename} p.{c.page or '?'}" for c in ans.citations[:4]))
        with st.expander("Quotes"):
            for c in ans.citations[:4]:
                st.caption(f"{c.filename} — p.{c.page or '?'}")
                st.write(f'"{c.quote[:300]}"')


def _mastery_block(eng) -> None:
    import streamlit as st
    rows = eng.get_progress()
    if not rows:
        st.caption("No progress yet. Take a quiz first.")
        return
    st.dataframe(
        [{"concept": r.concept, "state": r.state, "attempts": r.attempts,
          "correct": r.correct, "streak": r.streak} for r in rows],
        use_container_width=True, hide_index=True)


def tab_ask(eng) -> None:
    import streamlit as st
    st.subheader("Ask")
    st.caption("Answered only from your material.")
    q = st.text_input("Question", placeholder="Can Dijkstra handle negative weights?",
                      key="ask_q")
    if st.button("Ask", key="ask_go") and q.strip():
        with st.spinner("Searching your material..."):
            st.session_state["last_answer"] = eng.ask(q.strip())
    ans = st.session_state.get("last_answer")
    if ans:
        _answer_card(ans)


def _quiz_reset_for(qid: str) -> None:
    import streamlit as st
    for k in ("quiz_a1", "quiz_a2"):
        st.session_state.pop(k, None)


def tab_quiz(eng) -> None:
    import streamlit as st
    st.subheader("Quiz")
    st.caption("Wrong answers get re-taught, then retested.")
    topic = st.text_input("Topic (optional)", placeholder="dijkstra negative weights",
                          key="quiz_topic")
    if st.button("New question", key="quiz_new"):
        try:
            qs = eng.start_test(topic=topic.strip(), n=1)
        except Exception as e:
            st.error(str(e))
            return
        st.session_state["quiz_q"] = qs[0]
        st.session_state["quiz_stage"] = "asked"
        st.session_state["quiz_ev"] = None
        st.session_state["quiz_q2"] = None
        st.session_state["quiz_ev2"] = None
        _quiz_reset_for(qs[0].qid)

    q = st.session_state.get("quiz_q")
    if not q:
        _mastery_block(eng)
        return
    stage = st.session_state.get("quiz_stage", "asked")
    with st.container(border=True):
        st.write(q.text)
        st.caption(f"Concept: {q.concept}")
    if stage == "asked":
        a = st.text_input("Your answer", key="quiz_a1")
        if st.button("Submit", key="quiz_submit") and a.strip():
            ev = eng.submit_answer(q, a.strip())
            st.session_state["quiz_ev"] = ev
            st.session_state["quiz_stage"] = "graded"
            st.rerun()
    elif stage == "graded":
        ev = st.session_state["quiz_ev"]
        if ev.verdict == "correct":
            st.success(f"correct — {ev.explanation}")
        elif ev.verdict == "partial":
            st.warning(f"partial — {ev.explanation}")
        else:
            st.error(f"incorrect — {ev.explanation}")
        if ev.misconception:
            st.info(f"Possible misconception: {ev.misconception}")
        if ev.verdict == "correct":
            if st.button("Next question", key="quiz_next"):
                st.session_state["quiz_q"] = None
                st.session_state["quiz_stage"] = "idle"
                st.rerun()
        else:
            strat, expl = eng.reteach(q, ev)
            with st.expander(f"Re-teach ({strat})", expanded=True):
                st.write(expl)
            q2 = eng.retest_question(q)
            st.session_state["quiz_q2"] = q2
            st.session_state["quiz_stage"] = "retest"
            st.rerun()
    elif stage == "retest":
        q2 = st.session_state["quiz_q2"]
        with st.container(border=True):
            st.write(f"Retest: {q2.text}")
        a2 = st.text_input("Your answer (retest)", key="quiz_a2")
        if st.button("Submit retest", key="quiz_submit2") and a2.strip():
            ev2 = eng.submit_answer(q2, a2.strip())
            st.session_state["quiz_ev2"] = ev2
            st.session_state["quiz_stage"] = "done"
            st.rerun()
    elif stage == "done":
        ev2 = st.session_state["quiz_ev2"]
        if ev2.verdict == "correct":
            st.success(f"correct — {ev2.explanation}")
        elif ev2.verdict == "partial":
            st.warning(f"partial — {ev2.explanation}")
        else:
            st.error(f"incorrect — {ev2.explanation}")
        if st.button("Next question", key="quiz_next2"):
            st.session_state["quiz_q"] = None
            st.session_state["quiz_stage"] = "idle"
            st.rerun()
    st.divider()
    _mastery_block(eng)


def tab_practice(eng) -> None:
    import streamlit as st
    st.subheader("Practice")
    mode = st.radio("Mode", ["Quiz", "Flashcards", "Daily"], horizontal=True, key="pr_mode")
    if mode == "Quiz":
        tab_quiz(eng)
        return
    topic = st.text_input("Topic (optional)", placeholder="dijkstra negative weights", key="pr_topic")
    if mode == "Flashcards":
        if st.button("New cards", key="pr_flash_new"):
            try:
                st.session_state["pr_deck"] = eng.flashcard_deck(topic=topic.strip(), n=5)
                st.session_state["pr_idx"] = 0
                st.session_state["pr_flip"] = False
            except Exception as e:
                st.error(str(e))
        deck = st.session_state.get("pr_deck", [])
        idx = st.session_state.get("pr_idx", 0)
        if deck and idx < len(deck):
            q = deck[idx]
            with st.container(border=True):
                st.write(f"Card {idx + 1}/{len(deck)}")
                st.write(q.text)
                st.caption(q.concept)
            if not st.session_state.get("pr_flip"):
                if st.button("Show answer", key="pr_flip_btn"):
                    st.session_state["pr_flip"] = True
                    st.rerun()
            else:
                with st.container(border=True):
                    st.write((q.source_text or q.answer_key)[:500])
                g = st.radio("Grade", ["Forgot", "Half", "Knew"], horizontal=True, key=f"pr_g_{idx}")
                if st.button("Next", key=f"pr_next_{idx}"):
                    eng.submit_answer(q, f"grade {g} {q.answer_key}")
                    st.session_state["pr_idx"] = idx + 1
                    st.session_state["pr_flip"] = False
                    st.rerun()
        elif deck:
            st.success("Deck clear.")
        _mastery_block(eng)
    else:
        if st.button("Today's cards", key="pr_daily"):
            try:
                st.session_state["pr_daily_qs"] = eng.daily_plan()
            except Exception as e:
                st.error(str(e))
        for qi, q in enumerate(st.session_state.get("pr_daily_qs", [])):
            with st.container(border=True):
                st.write(q.text)
                st.caption(q.concept)
            a = st.text_input(f"Answer {qi + 1}", key=f"pr_d_a_{qi}")
            if st.button(f"Submit {qi + 1}", key=f"pr_d_go_{qi}") and a.strip():
                ev = eng.submit_answer(q, a.strip())
                st.write(f"{ev.verdict} — {ev.explanation}")


def tab_journal(eng) -> None:
    import streamlit as st
    st.subheader("Progress")
    try:
        d = eng.stats()
    except Exception as e:
        st.error(str(e))
        return
    s = d["status"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents", s["docs"])
    c2.metric("Mastered", f"{d['mastered']}/{d['concepts']}")
    c3.metric("Attempts", d["attempts"])
    _mastery_block(eng)
    with st.expander("History"):
        for h in d["history"]:
            st.caption(f"{h.get('at', '')} — {h.get('concept', '')} -> {h.get('verdict', '')}")
    fmt = st.selectbox("Export format", ["md", "json", "anki"], key="j_fmt")
    if st.button("Build export", key="j_exp"):
        try:
            st.session_state["j_text"] = eng.export_data(fmt)
        except Exception as e:
            st.error(str(e))
    if st.session_state.get("j_text"):
        st.code(st.session_state["j_text"][:4000])
        st.download_button("Download", st.session_state["j_text"], file_name=f"mindloop.{fmt}")


def tab_knowledge(eng) -> None:
    import streamlit as st
    st.subheader("Library")
    s = eng.status()
    c1, c2 = st.columns(2)
    c1.metric("Documents", s["docs"])
    c2.metric("Chunks", s["chunks"])
    path = st.text_input("File or folder to index",
                         value="./examples/sample-study-folder", key="ing_path")
    if st.button("Ingest", key="ing_go") and path.strip():
        with st.spinner("Indexing..."):
            try:
                res = eng.ingest(path.strip())
            except Exception as e:
                st.error(str(e))
                return
        st.success(f"{len(res.files_ok)} indexed, {len(res.files_skipped)} unchanged, "
                   f"{len(res.files_failed)} failed. Total: {res.docs_total} docs.")
        for f, err in res.files_failed:
            st.warning(f"{f}: {err}")
    docs = eng.sources()
    if docs:
        st.dataframe([{"file": d["filename"], "type": d["ftype"],
                       "chunks": d["chunk_count"]} for d in docs],
                     use_container_width=True, hide_index=True)
        name = st.selectbox("Remove a document", [d["filename"] for d in docs],
                            key="rm_name")
        if st.button("Remove", key="rm_go"):
            try:
                n = eng.remove(name)
                st.success(f"Removed {name} ({n} chunks). Files on disk untouched.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.caption("Nothing indexed yet.")


def main() -> None:
    import streamlit as st
    st.set_page_config(page_title="mindloop", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("mindloop")
    st.caption("Learn until you can't get it wrong. Local-first, grounded in your material.")
    eng = _engine()
    t_ask, t_quiz, t_know = st.tabs(["Ask", "Practice", "Library"])
    with t_ask:
        tab_ask(eng)
    with t_quiz:
        tab_practice(eng)
    with t_know:
        tab_knowledge(eng)


if __name__ == "__main__":
    main()
