"""Cinema: deterministic frames, skip, fallback, glyph audit."""
from mindloop import cinema as C
from mindloop import wordmark as W
from mindloop.theme import make_console


def _shot(width: int, kind: str, idx, tick: int = 0, per: int = 2) -> str:
    from rich.console import Console
    c = Console(width=width, color_system=None, highlight=False)
    stars = C.field_stars(width)
    with c.capture() as cap:
        c.print(C.render_frame(width, stars, kind, idx, tick, type_per_frame=per))
    return cap.get()


def test_frames_deterministic():
    a = _shot(80, "ignite", (3, 8), tick=2)
    b = _shot(80, "ignite", (3, 8), tick=2)
    assert a == b
    c = _shot(80, "comet", (4, False), tick=1)
    d = _shot(80, "comet", (4, False), tick=1)
    assert c == d


def test_ignition_progress_monotonic():
    vals = [W.progress_for_frame(f, 8) for f in range(8)]
    assert vals == sorted(vals)
    assert vals[-1] == 1.0
    assert vals[0] == 0.0


def test_fast_timeline_shorter():
    assert len(C._timeline(fast=True)) < len(C._timeline(fast=False))
    assert len(C._timeline()) > 30  # full cinema has substance


def test_starfield_seeded():
    assert C.field_stars(80) == C.field_stars(80)
    assert len(C.field_stars(80)) == C.STAR_COUNT


def test_play_forced_off_prints_static():
    c = make_console()
    with c.capture() as cap:
        C.play(c, forced_off=True)
    assert "M I N D L O O P" in cap.get()


def test_cinema_literals_windows_safe():
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "mindloop" / "cinema.py").read_text(encoding="utf-8")
    for ch in ["\u2713", "\u2717", "\u276f", "\u2192", "\u2026", "\u2588"]:
        assert ch not in text
