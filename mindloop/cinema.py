"""Quiet boot cinema. Six small acts, one transient Live canvas, then stillness.

Act 1 Enso: a single ink circle breathes open.
Act 2 Ignition: letters bloom stone -> hanko, staggered ease-out.
Act 3 Comet: bright head sweeps with a warm tail, answers back fast.
Act 4 Starfield: seeded dust frames the lockup (deterministic).
Act 5 Whisper: the rule draws itself, the tagline types in.
Act 6 Seal: the hanko stamps once, then stillness.

Any keypress skips to the still frame. Piped/narrow/NO_COLOR/env/flags
bypass to the static lockup. Glow is Rich style only.
"""
from __future__ import annotations
import random
import sys
import threading
import time

STAR_SEED = 7
STAR_COUNT = 36
CURSOR = "_"
ENSO_FRAMES = ["○", "◔", "◑", "◕", "●"]

try:
    from rich.align import Align as _Align
    from rich.console import Group as _Group
    from rich.live import Live as _Live
    from rich.text import Text as _Text
except Exception:  # pragma: no cover
    _Align = _Group = _Live = _Text = None  # type: ignore

from . import wordmark as W


def ease_in_out(x: float) -> float:
    return x * x * (3.0 - 2.0 * x)


def field_stars(width: int, count: int = STAR_COUNT) -> list[tuple[int, int, int]]:
    """Deterministic starfield: (column, row 0|4, phase). Same every run."""
    rng = random.Random(STAR_SEED)
    field_w = max(20, min(width - 8, 64))
    left = max(0, (width - field_w) // 2)
    return [(left + rng.randrange(field_w), rng.randrange(2) * 4, rng.randrange(6)) for _ in range(count)]


def _twinkle_style(tick: int, phase: int) -> str | None:
    slot = (tick + phase) % 6
    if slot == 0:
        return "#8A8378"
    if slot in (1, 5):
        return "#4A4A48"
    return None


def _star_line(width: int, stars: list[tuple[int, int, int]], row: int, tick: int, fade: float = 1.0):
    t = _Text()
    dots = {c: p for (c, r, p) in stars if r == row}
    for col in range(width):
        if col in dots and fade > 0:
            style = _twinkle_style(tick, dots[col])
            if style and (fade >= 1.0 or (tick + dots[col]) % 2 == 0):
                t.append(".", style=style)
            else:
                t.append(" ")
        else:
            t.append(" ")
    return t


def render_frame(width: int, stars, kind: str, idx: int, tick: int, type_per_frame: int = 2):
    """Pure frame builder: same inputs -> same frame (tests rely on this)."""
    lines = [_Align.center(_star_line(width, stars, 0, tick, 0.0 if kind in ("tag", "seal") else 1.0))]
    if kind == "enso":
        f, total = idx if isinstance(idx, tuple) else (idx, 5)
        glyph = ENSO_FRAMES[min(len(ENSO_FRAMES) - 1, f)]
        lines.append(_Align.center(_Text(f"  {glyph}", style="#C73E1D")))
        lines.append(_Align.center(_Text(" ")))
        lines.append(_Align.center(_Text(" ", style="dim")))
    elif kind == "ignite":
        f, total = idx
        prog = W.progress_for_frame(f, total)
        lines.append(_Align.center(W.lockup_at(prog)))
        lines.append(_Align.center(_Text(" ")))
        lines.append(_Align.center(_Text(" ")))
    elif kind == "comet":
        pos, returning = idx
        tail = 3
        t = _Text()
        for i, ch in enumerate(W.NAME):
            d = pos - i if not returning else i - pos
            if d == 0:
                style = f"bold {W.SHINE}"
            elif 1 <= d <= tail:
                k = 1.0 - d / (tail + 1.0)
                style = W.STOPS[min(len(W.STOPS) - 1, int(k * (len(W.STOPS) - 1)))]
            else:
                style = W.STOPS[i]
            t.append(ch, style=style)
            if i < len(W.NAME) - 1:
                t.append(" ", style="default")
        lines.append(_Align.center(t))
        lines.append(_Align.center(_Text(" ")))
        lines.append(_Align.center(_Text(" ")))
    elif kind == "rule":
        f, total = idx
        k = int((f + 1) / max(1, total) * W.RULE_LEN)
        lines.append(_Align.center(W.lockup_full()))
        lines.append(_Align.center(_Text("-" * max(1, k), style="#8A5A1A")))
        lines.append(_Align.center(_Text(" ")))
    elif kind == "tag":
        shown = W.TAGLINE[: (idx + 1) * type_per_frame]
        cursor = "" if len(shown) >= len(W.TAGLINE) else CURSOR
        lines.append(_Align.center(W.lockup_full()))
        lines.append(_Align.center(_Text("-" * W.RULE_LEN, style="#8A5A1A")))
        tag = _Text(shown, style="dim") + _Text(cursor, style="#C73E1D")
        lines.append(_Align.center(tag))
    elif kind == "seal":
        lines.append(_Align.center(W.lockup_full()))
        lines.append(_Align.center(_Text("-" * W.RULE_LEN, style="#8A5A1A")))
        seal = _Text(f" {W.HANKO_CHAR} ", style="white on #C73E1D")
        lines.append(_Align.center(seal))
    else:
        lines.append(_Align.center(W.lockup_full()))
        lines.append(_Align.center(_Text(" ")))
        lines.append(_Align.center(_Text(" ")))
    lines.append(_Align.center(_star_line(width, stars, 4, tick, 0.0 if kind in ("tag", "seal") else 1.0)))
    return _Group(*lines)


def _timeline(fast: bool = False) -> list[tuple]:
    frames: list[tuple] = []
    enso_n = 3 if fast else 5
    for f in range(enso_n):
        frames.append(("enso", (f, enso_n), 0))
    ignite_n = 4 if fast else 8
    for f in range(ignite_n):
        frames.append(("ignite", (f, ignite_n), 0))
    fwd_n, back_n = (5, 3) if fast else (8, 4)
    for f in range(fwd_n):
        pos = int(ease_in_out(f / max(1, fwd_n - 1)) * 7)
        frames.append(("comet", (pos, False), 0))
    for f in range(back_n):
        pos = 7 - int((f + 1) / back_n * 7)
        frames.append(("comet", (pos, True), 0))
    rule_n = 3 if fast else 6
    for f in range(rule_n):
        frames.append(("rule", (f, rule_n), 0))
    total_chars = len(W.TAGLINE)
    per = 3 if fast else 2
    type_n = (total_chars + per - 1) // per
    for f in range(type_n):
        frames.append(("tag", f, per))
    seal_n = 2 if fast else 4
    for f in range(seal_n):
        frames.append(("seal", f, 0))
    return frames


def _arm_skip() -> tuple[object, object]:
    """Any-key skip listener. Returns (stop_event, thread). Never raises."""
    import threading as _t
    stop = _t.Event()

    def _win() -> None:
        try:
            import msvcrt
            while not stop.is_set():
                if msvcrt.kbhit():
                    msvcrt.getch()
                    stop.set()
                    break
                time.sleep(0.05)
        except Exception:
            pass

    def _posix() -> None:
        try:
            import select
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not stop.is_set():
                    if select.select([sys.stdin], [], [], 0.05)[0]:
                        sys.stdin.read(1)
                        stop.set()
                        break
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                except Exception:
                    pass
        except Exception:
            pass

    target = _win if sys.platform.startswith("win") else _posix
    th = _t.Thread(target=target, daemon=True)
    try:
        th.start()
    except Exception:
        pass
    return stop, th


def play(console, forced_off: bool = False, fast: bool = False) -> None:
    """Full cinema, then settle to still. Any key skips to still."""
    if not W.should_animate(console, forced_off):
        W.print_static(console)
        return
    try:
        width = console.width or 80
    except Exception:
        width = 80
    stars = field_stars(width)
    stop, _th = _arm_skip()
    try:
        with _Live(render_frame(width, stars, "ignite", 0, 0), console=console,
                   transient=True, refresh_per_second=16) as live:
            tick = 0
            for kind, idx, per in _timeline(fast):
                if stop.is_set():
                    break
                live.update(render_frame(width, stars, kind, idx, tick,
                                         type_per_frame=per or 2))
                time.sleep(0.055 if kind in ("comet",) else 0.075)
                tick += 1
    except Exception:
        pass
    finally:
        try:
            stop.set()
        except Exception:
            pass
    W.print_static(console)
