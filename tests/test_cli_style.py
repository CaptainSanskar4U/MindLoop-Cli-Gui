"""CLI style: friendly errors, ASCII-safe literals, grouped help."""
from pathlib import Path
from typer.testing import CliRunner
from mindloop.cli import app

runner = CliRunner()
SRC = Path(__file__).resolve().parent.parent / "mindloop"


def test_missing_arg_shows_try():
    for args in [[
        "ingest"], ["ask"], ["remove"], ["explain"], ["teach"], ["watch"],
    ]:
        r = runner.invoke(app, args)
        assert r.exit_code == 2, args
        assert "Try:" in r.output, args
        assert "Reason:" in r.output, args


def test_bad_path_suggests_sample():
    r = runner.invoke(app, ["ingest", "./nope-missing-folder"])
    assert r.exit_code == 1
    assert "Try:" in r.output
    assert "sample-study-folder" in r.output


def test_our_literals_are_windows_safe():
    bad = ["\u2713", "\u2717", "\u276f", "\u2192", "\u2026"]
    for f in ["cli.py", "ui.py", "theme.py"]:
        text = (SRC / f).read_text(encoding="utf-8")
        for ch in bad:
            assert ch not in text, f"{f} contains {ch!r} (breaks cp1252 terminals)"


def test_help_is_grouped():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    for group in ["Learn", "Knowledge", "System"]:
        assert group in r.output, group
