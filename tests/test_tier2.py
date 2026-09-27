"""Tier 2: DOCX, explain/teach, status/sources/remove, review."""
from mindloop.engine import MindloopEngine
from mindloop.providers import FakeLLM

def test_docx_ingest(home):
    import docx
    p = home / "study" / "extra.docx"
    d = docx.Document()
    d.add_paragraph("Mitochondria is the powerhouse. Unique token QWERTY42.")
    d.save(str(p))
    eng = MindloopEngine(llm=FakeLLM())
    res = eng.ingest(home / "study")
    assert "extra.docx" in res.files_ok
    ans = eng.ask("What is the powerhouse? QWERTY42")
    assert not ans.refused
    assert any("extra.docx" in c.filename for c in ans.citations)

def test_explain_grounded(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    ans = eng.explain("dijkstra negative weights")
    assert not ans.refused
    assert ans.citations
    ans2 = eng.explain("xyzzy nonexistent topic qqq")
    assert ans2.refused

def test_status_sources_remove(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    s = eng.status()
    assert s["docs"] >= 3 and s["chunks"] >= 3
    docs = eng.sources()
    assert any("notes.md" in d["filename"] for d in docs)
    n = eng.remove("plain.txt")
    assert n >= 1
    assert all("plain.txt" not in d["filename"] for d in eng.sources())

def test_review_lists_weak(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    qs = eng.start_test(topic="dijkstra negative", n=1)
    eng.submit_answer(qs[0], "Yes, Dijkstra handles negative weights")
    weak = eng.review_list()
    assert any(w.concept == qs[0].concept for w in weak)
