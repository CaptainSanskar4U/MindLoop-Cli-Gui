"""Still-frame library for the wordmark. No motion here — cinema.py directs.

Sumi ink lockup with vermillion hanko seal. lockup_at(progress) renders
the ignition state: letters with index/8 <= progress burn at full color,
later letters still dark embers. progress >= 1.0 is the settled lockup.
Keeps the classic spaced M I N D L O O P for compatibility; glow is style.
"""
from __future__ import annotations

NAME = "MINDLOOP"
TAGLINE = "learn until you can't get it wrong."
RULE_LEN = 28
HANKO_CHAR = "心"

# sumi -> warm stone -> hanko heart -> stone -> sumi, one stop per letter
STOPS = ["#4A4A48", "#8A8378", "#C9A227", "#C73E1D", "#C73E1D", "#C9A227", "#8A8378", "#4A4A48"]
DARK = "#2A2A28"
SHINE = "#FFF3D6"

try:
    from rich.text import Text as _Text
except Exception:  # pragma: no cover - rich always present in practice
    _Text = None  # type: ignore


def lockup_at(progress: float, shine_at: int | None = None):
    """Wordmark Text at ignition progress 0.0 (dark) .. 1.0 (full burn)."""
    t = _Text()
    n = len(NAME)
    for i, ch in enumerate(NAME):
        lit = (i + 1) / n <= progress + 1e-9
        if shine_at is not None and i == shine_at:
            style = f"bold {SHINE}"
        elif lit:
            style = STOPS[i]
        else:
            style = DARK
        t.append(ch, style=style)
        if i < n - 1:
            t.append(" ", style="default")
    return t


def lockup_full():
    return lockup_at(1.0)


def progress_for_frame(frame: int, total: int) -> float:
    """Ease-out ignition: fast start, gentle landing on the honey heart."""
    if total <= 1:
        return 1.0
    x = frame / (total - 1)
    return 1.0 - (1.0 - x) ** 2


def should_animate(console, forced_off: bool = False) -> bool:
    import os
    if forced_off:
        return False
    if os.environ.get("NO_ANIMATION") or os.environ.get("MINDLOOP_NO_ANIMATION"):
        return False
    if os.environ.get("NO_COLOR"):
        return False
    try:
        if not console.is_terminal:
            return False
    except Exception:
        return False
    try:
        if (console.width or 80) < 70:
            return False
    except Exception:
        pass
    return True


def hanko_text():
    t = _Text()
    t.append(f" {HANKO_CHAR} ", style="white on #C73E1D")
    return t


def print_static(console) -> None:
    from rich.align import Align as _Align
    from rich.console import Group as _Group
    try:
        is_term = bool(console.is_terminal)
    except Exception:
        is_term = False
    console.print("")
    if is_term:
        try:
            from rich.columns import Columns
            console.print(_Align.center(lockup_full()))
            console.print(_Align.center(hanko_text()))
        except Exception:
            console.print(lockup_full(), justify="center")
    else:
        console.print(lockup_full(), justify="center")
    console.print("-" * RULE_LEN, style="#8A5A1A", justify="center")
    console.print(TAGLINE, style="dim", justify="center")
    console.print("")


def play(console, forced_off: bool = False, fast: bool = False) -> None:
    """Shimmer once, settle to still. cinema.py owns the full show."""
    from . import cinema as C
    C.play(console, forced_off=forced_off, fast=fast)
