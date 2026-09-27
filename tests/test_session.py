"""Session: bare run boots ask-mode, compact chips, /more expands, slashes work."""
from typer.testing import CliRunner
from mindloop.cli import app

runner = CliRunner()


def _boot(home, text: str):
    return runner.invoke(app, [], input=text)


def test_bare_run_is_session_not_help_wall(home):
    from mindloop.engine import MindloopEngine
    from mindloop.providers import FakeLLM
    MindloopEngine(llm=FakeLLM()).ingest(home / "study")
    r = _boot(home, "Does Dijkstra support negative weights?\n/exit\n")
    assert r.exit_code == 0, r.output[-500:]
    assert "M I N D L O O P" in r.output
    assert "Knowledge" not in r.output  # no help wall
    assert "dijkstra" in r.output.lower() or "bellman" in r.output.lower()
    assert "/more for quotes" in r.output  # compact chips


def test_more_expands_quotes(home):
    from mindloop.engine import MindloopEngine
    from mindloop.providers import FakeLLM
    MindloopEngine(llm=FakeLLM()).ingest(home / "study")
    r = _boot(home, "Does Dijkstra support negative weights?\n/more\n/exit\n")
    assert r.exit_code == 0, r.output[-500:]
    assert '"' in r.output  # verbatim quote shown


def test_unknown_slash_suggests_help(home):
    r = _boot(home, "/frobnicate\n/exit\n")
    assert r.exit_code == 0, r.output[-500:]
    assert "/help" in r.output


def test_slash_quiz_flows(home):
    from mindloop.engine import MindloopEngine
    from mindloop.providers import FakeLLM
    MindloopEngine(llm=FakeLLM()).ingest(home / "study")
    r = _boot(home, "/quiz dijkstra negative\nYes, Dijkstra handles negative weights\nNo, Dijkstra cannot handle negative weights, Bellman-Ford can\n/exit\n")
    assert r.exit_code == 0, r.output[-800:]
    assert "incorrect" in r.output.lower()
    assert "bellman" in r.output.lower()


def test_session_literals_windows_safe():
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "mindloop" / "session.py").read_text(encoding="utf-8")
    for ch in ["\u2713", "\u2717", "\u276f", "\u2192", "\u2026"]:
        assert ch not in text
