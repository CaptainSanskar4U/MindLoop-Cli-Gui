"""CLI smoke tests via Typer runner. No Ollama needed."""
from typer.testing import CliRunner
from mindloop.cli import app

runner = CliRunner()

def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0

def test_init_and_doctor(home):
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["doctor"])
    assert r.exit_code == 0
    assert "PASS" in r.output or "FAIL" in r.output

def test_ingest_ask_progress(home):
    r = runner.invoke(app, ["ingest", str(home / "study")])
    assert r.exit_code == 0
    assert "indexed" in r.output.lower()
    r = runner.invoke(app, ["ask", "Does Dijkstra support negative weights?"])
    assert r.exit_code == 0
    assert "dijkstra" in r.output.lower() or "bellman" in r.output.lower()
    r = runner.invoke(app, ["ask", "Who won the 2018 football world cup?"])
    assert r.exit_code == 0
    assert "couldn't find" in r.output.lower()
