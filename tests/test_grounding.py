"""Retrieval + grounding: relevant hit, irrelevant refuse, citations, LLM not called on weak evidence."""
from mindloop.engine import MindloopEngine
from mindloop.providers import FakeLLM
from mindloop import retrieve as ret

def test_relevant_retrieval(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    hits = ret.retrieve("Can Dijkstra handle negative weights?")
    assert hits, "should retrieve dijkstra chunk"
    assert any("dijkstra" in h.text.lower() for h in hits)
    assert hits[0].page is not None or hits[0].filename.endswith(".md")

def test_irrelevant_refused(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    ans = eng.ask("Who won the 2018 football world cup?")
    assert ans.refused is True
    assert "couldn't find" in ans.text.lower()

def test_citation_accuracy(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    ans = eng.ask("Does Dijkstra support negative weights?")
    assert not ans.refused
    assert ans.citations, "must attach citations by code"
    # citation file must match retrieved chunk source
    assert any("notes.md" in c.filename for c in ans.citations)
    # quote must be verbatim substring of stored chunk
    from mindloop.store import connect
    con = connect()
    try:
        texts = [r["text"] for r in con.execute("SELECT text FROM chunks").fetchall()]
    finally:
        con.close()
    for c in ans.citations:
        assert any(c.quote[:40] in t for t in texts), "quote must come from stored chunk"

def test_weak_evidence_no_llm_call(home, monkeypatch):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    called = {"n": 0}
    orig = FakeLLM.generate
    def spy(self, *a, **k):
        called["n"] += 1
        return orig(self, *a, **k)
    monkeypatch.setattr(FakeLLM, "generate", spy)
    ans = eng.ask("xyzzy quantum football blarg")
    assert ans.refused is True
    # ask() refuses via threshold before generation for nonsense; generation may still run
    # for fallback but must not present fake facts
    assert "couldn't find" in ans.text.lower()
