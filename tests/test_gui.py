"""GUI contract: the exact engine flows the browser tabs rely on. No browser needed."""
from mindloop.engine import MindloopEngine
from mindloop.providers import FakeLLM


def _eng(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    return eng


def test_ask_tab_flow(home):
    eng = _eng(home)
    ans = eng.ask("Does Dijkstra support negative weights?")
    assert not ans.refused
    assert ans.text
    assert ans.citations and all(c.filename and c.quote for c in ans.citations)
    no = eng.ask("Who won the 2018 football world cup?")
    assert no.refused


def test_quiz_tab_state_machine(home):
    eng = _eng(home)
    qs = eng.start_test(topic="dijkstra negative", n=1)
    q = qs[0]
    ev = eng.submit_answer(q, "Yes, Dijkstra handles negative weights")
    assert ev.verdict == "incorrect" and ev.misconception
    strat, expl = eng.reteach(q, ev)
    assert strat and expl
    q2 = eng.retest_question(q)
    assert q2.text != q.text
    ev2 = eng.submit_answer(q2, "No, Dijkstra cannot handle negative weights, Bellman-Ford can")
    assert ev2.verdict == "correct"
    assert any(m.state in ("RETESTING", "MASTERED") for m in eng.get_progress())


def test_knowledge_tab_flows(home):
    eng = _eng(home)
    s = eng.status()
    assert s["docs"] >= 3
    assert any("notes.md" in d["filename"] for d in eng.sources())
    n = eng.remove("plain.txt")
    assert n >= 1
    assert all("plain.txt" not in d["filename"] for d in eng.sources())


def test_gui_module_imports_without_streamlit_server():
    import mindloop.gui as g
    for fn in ("main", "tab_ask", "tab_quiz", "tab_knowledge"):
        assert callable(getattr(g, fn))


def test_gui_launcher_uses_python_minus_m(monkeypatch, home):
    """Launcher must not depend on streamlit.exe being on PATH."""
    import sys
    import mindloop.cli as cli
    from typer.testing import CliRunner
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        class R:
            returncode = 0
        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    r = CliRunner().invoke(cli.app, ["gui", "--port", "8999"])
    assert r.exit_code == 0, r.output[-500:]
    cmd = calls["cmd"]
    assert cmd[0] == sys.executable and cmd[1:3] == ["-m", "streamlit"]
    assert "8999" in cmd
