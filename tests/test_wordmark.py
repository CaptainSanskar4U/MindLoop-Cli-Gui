"""Wordmark: static lockup, shimmer skip guards, Windows-safe literals."""
import os
from typer.testing import CliRunner
from mindloop import wordmark as W
from mindloop.theme import make_console
from mindloop.cli import app

runner = CliRunner()


def test_static_lockup_renders():
    c = make_console()
    with c.capture() as cap:
        W.print_static(c)
    out = cap.get()
    assert "M I N D L O O P" in out
    assert "learn until you can't get it wrong." in out


def test_shimmer_skips_when_piped():
    c = make_console()
    assert c.is_terminal is False  # CliRunner capture is not a tty
    assert W.should_animate(c) is False
    with c.capture() as cap:
        W.play(c)
    assert "M I N D L O O P" in cap.get()


def test_shimmer_skips_with_env(monkeypatch):
    c = make_console()
    monkeypatch.setenv("MINDLOOP_NO_ANIMATION", "1")
    assert W.should_animate(c, forced_off=False) is False
    assert W.should_animate(c, forced_off=True) is False


def test_no_animation_flag(home):
    r = runner.invoke(app, ["--no-animation", "ask", "Does Dijkstra support negative weights?"])
    # empty KB in this home -> friendly panel, but flag must parse
    assert r.exit_code in (0, 1), r.output[-300:]


def test_wordmark_literals_windows_safe():
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "mindloop" / "wordmark.py").read_text(encoding="utf-8")
    for ch in ["\u2713", "\u2717", "\u276f", "\u2192", "\u2026", "\u2588"]:
        assert ch not in text
