"""Motion system. Hand-tuned ink animations, calm and brief.

All helpers are no-ops when motion is off (piped, narrow, NO_COLOR,
--no-animation). Never raise: animation must never break answers.
"""
from __future__ import annotations
import time

INK_LINES = [
    "grinding ink...",
    "laying paper...",
    "tracing sources...",
]

ENSO_FRAMES = ["○", "◔", "◑", "◕", "●"]


def motion_allowed(console, forced_off: bool = False) -> bool:
    try:
        from .wordmark import should_animate
        return bool(should_animate(console, forced_off))
    except Exception:
        return False


def brush_lines(console, text: str, delay: float = 0.014) -> None:
    for line in text.splitlines():
        console.print(line)
        time.sleep(delay)


def type_line(console, text: str, delay: float = 0.008) -> None:
    # typewriter for taglines: print progressively on one line
    try:
        if not motion_allowed(console):
            console.print(text)
            return
        from rich.live import Live
        from rich.text import Text
        with Live(Text(""), console=console, transient=True, refresh_per_second=30) as live:
            for i in range(1, len(text) + 1):
                live.update(Text(text[:i], style="dim"))
                time.sleep(delay)
        console.print(text, style="dim")
    except Exception:
        console.print(text)


def enso_breath(console, cycles: int = 2, delay: float = 0.18) -> None:
    try:
        if not motion_allowed(console):
            return
        from rich.live import Live
        from rich.text import Text
        frames = ["○", "◑", "●", "◑", "○"]
        with Live(Text(""), console=console, transient=True, refresh_per_second=12) as live:
            for _ in range(cycles):
                for f in frames:
                    live.update(Text(f"  {f}", style="#C73E1D"))
                    time.sleep(delay)
    except Exception:
        pass


def ink_status(console, label: str = "gathering"):
    """Context manager yielding a status with rotating ink lines."""
    from rich.console import Console as _C  # noqa
    try:
        if motion_allowed(console):
            return console.status(f"{label}... grinding ink...", spinner="dots")
    except Exception:
        pass
    # fallback: dummy context
    class _Dummy:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def update(self, *a, **k):
            pass
    return _Dummy()


def hanko_pause(delay: float = 0.12) -> None:
    try:
        time.sleep(delay)
    except Exception:
        pass


def countdown(console, secs: int = 3) -> None:
    try:
        allow = motion_allowed(console)
        for i in range(secs, 0, -1):
            console.print(f"[muted]{i}...[/muted]")
            if allow:
                time.sleep(0.45)
    except Exception:
        pass


def focus_timer(console, minutes: float = 1.0) -> None:
    """Silent zazen timer with breath circle. minutes may be fractional."""
    total = max(1, int(minutes * 60))
    allow = motion_allowed(console)
    try:
        from rich.live import Live
        from rich.text import Text
        frames = ["○", "◑", "●", "◑"]
        with Live(Text(""), console=console, transient=True, refresh_per_second=4) as live:
            for s in range(total, 0, -1):
                f = frames[(total - s) % len(frames)]
                mm, ss = divmod(s, 60)
                live.update(Text(f"  {f}  {mm:02d}:{ss:02d}  breathe", style="dim"))
                time.sleep(1)
    except Exception:
        # non-interactive fallback: short sleep
        if not allow:
            return
        time.sleep(min(total, 2))
    console.print("[muted]done. well sat.[/muted]")
