"""Learning loop: evaluate, misconception, reteach rotation, retest new Q, mastery, attempt limit."""
from mindloop.engine import MindloopEngine
from mindloop.providers import FakeLLM

def _dijkstra_q(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    qs = eng.start_test(topic="dijkstra negative", n=1)
    assert qs and "dijkstra" in qs[0].concept
    return eng, qs[0]

def test_incorrect_detects_misconception(home):
    eng, q = _dijkstra_q(home)
    ev = eng.submit_answer(q, "Yes, Dijkstra handles negative weights")
    assert ev.verdict == "incorrect"
    assert "bellman" in ev.misconception.lower()

def test_correct_answer(home):
    eng, q = _dijkstra_q(home)
    ev = eng.submit_answer(q, "No, Dijkstra cannot handle negative weights, Bellman-Ford can")
    assert ev.verdict == "correct"
    assert ev.misconception == ""

def test_reteach_rotates_strategy(home):
    eng, q = _dijkstra_q(home)
    ev = eng.submit_answer(q, "Yes Dijkstra handles it")
    s1, _ = eng.reteach(q, ev)
    s2, _ = eng.reteach(q, ev)
    assert s1 != s2, "must never reuse a strategy for the same concept"

def test_retest_is_new_question(home):
    eng, q = _dijkstra_q(home)
    q2 = eng.retest_question(q)
    assert q2.text != q.text
    assert q2.concept == q.concept

def test_mastery_needs_two_in_row(home):
    eng, q = _dijkstra_q(home)
    eng.submit_answer(q, "Yes, Dijkstra handles negative weights")  # fail
    q2 = eng.retest_question(q)
    eng.submit_answer(q2, "No, Dijkstra cannot handle negative weights, use Bellman-Ford")  # 1 correct
    from mindloop.store import connect
    con = connect()
    st = con.execute("SELECT state FROM mastery WHERE concept=?", (q.concept,)).fetchone()["state"]
    con.close()
    assert st != "MASTERED"
    eng.submit_answer(q2, "No, needs non-negative weights")  # 2nd correct in a row
    con = connect()
    st2 = con.execute("SELECT state FROM mastery WHERE concept=?", (q.concept,)).fetchone()["state"]
    con.close()
    assert st2 == "MASTERED"

def test_malformed_llm_handled(home, monkeypatch):
    from mindloop import providers
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    qs = eng.start_test(topic="dijkstra", n=1)
    monkeypatch.setattr(FakeLLM, "generate", lambda self, *a, **k: "not-json{{{")
    ev = eng.submit_answer(qs[0], "some answer")
    assert ev.verdict in ("correct", "partial", "incorrect")  # never crashes
