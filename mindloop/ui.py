"""Shared calm components. Sumi ink on washi, one vermillion hanko.

Every command uses these; nothing prints raw. Hand-made, not AI-slop:
muted earth inks, generous whitespace, thin rules, one seal accent.
Kept Windows-safe: avoids the classic cp1252-breakers (checked by tests).
"""
from __future__ import annotations
from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

ACCENT = "#C73E1D"
AMBER = "#D9A441"
HANKO = "#C73E1D"
GOLD = "#C9A227"
STONE = "#8A8378"
TAGLINE = "learn until you can't get it wrong."

# hand-written loader lines, never LLM-generated at runtime
INK_LINES = [
    "grinding ink...",
    "laying paper...",
    "tracing sources...",
    "brushing answer...",
]
SEAL = {"correct": "正", "partial": "半", "incorrect": "誤"}


def banner(console) -> None:
    console.print("")
    console.print("[accent]mindloop[/accent]  [muted]" + TAGLINE + "[/muted]  [hanko]\u5fc3[/hanko]")


def section(console, title: str) -> None:
    try:
        is_term = bool(console.is_terminal)
    except Exception:
        is_term = False
    if is_term:
        # thin ink rule, title in stone, quiet left-aligned
        console.print("")
        console.print(f"[muted]{title}[/muted]")
        console.print(Rule(style="#3A3A38", characters="-"))
    else:
        console.print(f"--- {title} ---")


def ma(console, lines: int = 1) -> None:
    for _ in range(lines):
        console.print("")


def ink_rule(console, width: int = 40) -> None:
    console.print(f"[dim]{'-' * width}[/dim]")


def turn_divider(console) -> None:
    console.print("[muted]" + "-" * 32 + "[/muted]")


def enso_for_streak(streak: int, need: int = 2) -> str:
    if streak <= 0:
        return "\u25cb"
    if streak >= need + 1:
        return "\u25cf"
    if streak >= need:
        return "\u25d0"
    return "\u25d1"


def ink_bar(frac: float, width: int = 10) -> str:
    frac = max(0.0, min(1.0, frac))
    fills = [" ", "_", "-", "=", "#"]
    n = int(round(frac * width))
    return "#" * n + "-" * (width - n)


def sparkline(vals: list[float]) -> str:
    if not vals:
        return "-"
    glyphs = ["_", "-", "=", "#"]
    mx = max(vals) or 1.0
    return "".join(glyphs[min(3, int(v / mx * 3.99))] for v in vals[-12:])


def hanko_stamp(console, char: str = "\u5fc3", label: str = "") -> None:
    console.print(f"[white on #C73E1D] {char} [/white on #C73E1D]" + (f" [muted]{label}[/muted]" if label else ""))


def answer_panel(console, text: str) -> None:
    console.print("")
    console.print(Markdown(text.strip()))
    console.print("")


def answer_framed(console, text: str, title: str = "answer") -> None:
    console.print(Panel(
        Markdown(text.strip()),
        title=title,
        title_align="left",
        border_style="#3A3A38",
        box=box.ROUNDED,
        padding=(1, 2),
    ))


def sources_block(console, citations, limit: int = 4) -> None:
    console.print("[heading]sources[/heading] [muted]- grounded in your material[/muted]")
    for i, c in enumerate(citations[:limit], 1):
        console.print(f"  [accent][{i}][/accent] {c.filename} - p.{c.page or '?'}")
        if c.quote:
            console.print(f"      [muted]\"{c.quote[:180]}\"[/muted]")


def library_card(console, c, idx: int = 1, score: float = 0.0) -> None:
    dot = "#" if score >= 0.3 else ("=" if score >= 0.15 else "-")
    console.print(f"  [accent][{idx}][/accent] {c.filename} [muted]p.{c.page or '?'} {dot}[/muted]")
    if getattr(c, "quote", ""):
        console.print(f"      [muted]\"{c.quote[:160]}\"[/muted]")
    elif getattr(c, "text", ""):
        console.print(f"      [muted]\"{c.text[:160]}\"[/muted]")


def refusal_panel(console, text: str) -> None:
    console.print("")
    console.print("[muted]not in your material.[/muted]")
    console.print(f"[muted]{text}[/muted]")
    console.print("")


def error_panel(console, title: str, reason: str, fix: str) -> None:
    body = f"[heading]Reason:[/heading]\n[muted]{reason}[/muted]"
    if fix:
        body += f"\n\n[heading]Try:[/heading]\n{fix}"
    console.print(Panel(body, title=title, title_align="left", border_style="#3A3A38",
                        box=box.ROUNDED, padding=(1, 2)))


def verdict_style(verdict: str) -> str:
    return {"correct": "ok", "partial": "warn"}.get(verdict, "err")


def question_block(console, i: int, n: int, concept: str, text: str, source: str = "") -> None:
    console.print("")
    console.print(f"[muted]q{i}/{n}  ·  {concept}[/muted]")
    ink_rule(console, 40)
    console.print(Markdown(text))
    if source:
        console.print(f"[muted]{source}[/muted]")


def misconception_block(console, text: str) -> None:
    console.print(Panel(text, title="maybe mis-seen", title_align="left",
                        border_style="#8A8378",
                        box=box.ROUNDED, padding=(1, 2)))


def reteach_block(console, strategy: str, text: str) -> None:
    console.print(f"[muted]-金- repaired with {strategy} -金-[/muted]")
    console.print(Panel(Markdown(text), title=f"re-teach ({strategy})", title_align="left",
                        border_style=ACCENT, box=box.ROUNDED, padding=(1, 2)))


def seal_verdict(console, verdict: str, explanation: str = "") -> None:
    seal = SEAL.get(verdict, "・")
    style = verdict_style(verdict)
    console.print(f"[white on #C73E1D] {seal} [/white on #C73E1D] [{style}]{verdict}[/{style}]")
    if explanation:
        console.print(f"[muted]{explanation}[/muted]")


def mastery_table(console, rows, detail: bool = False, title: str = "mastery") -> None:
    t = Table(title="", box=box.SIMPLE, show_lines=False, padding=(0, 2))
    t.add_column("Concept", style="")
    t.add_column("State", style="muted")
    t.add_column("Att", justify="right")
    t.add_column("OK", justify="right")
    if detail:
        t.add_column("Miss", justify="right")
    t.add_column("Enso", justify="center")
    t.add_column("Flow")
    for r in rows:
        need = 2
        enso = enso_for_streak(r.streak, need)
        bar = ink_bar(r.correct / max(1, r.attempts), 8)
        cell = f"[accent]{enso}[/accent] {bar}"
        if detail:
            t.add_row(r.concept, r.state.lower(), str(r.attempts), str(r.correct),
                      str(r.incorrect), enso, f"[muted]{bar}[/muted]")
        else:
            t.add_row(r.concept, r.state.lower(), str(r.attempts), str(r.correct),
                      enso, f"[muted]{bar}[/muted]")
    console.print(f"[muted]{title}[/muted]")
    console.print(t)


def sources_table(console, docs) -> None:
    t = Table(title="", box=box.SIMPLE, show_lines=False, padding=(0, 2))
    t.add_column("File")
    t.add_column("Type", style="muted")
    t.add_column("Chunks", justify="right")
    t.add_column("Indexed", style="muted")
    for d in docs:
        t.add_row(d["filename"], d["ftype"], str(d["chunk_count"]), d["indexed"] or "")
    console.print("[muted]sources[/muted]")
    console.print(t)


def ask_prompt(console, label: str = "Your answer") -> str:
    console.print(f"[accent]>[/accent] [heading]{label}[/heading] [muted](type, Enter to send)[/muted]")
    return Prompt.ask("", console=console)


def progress_ink(console, label: str, done: int, total: int) -> None:
    bar = ink_bar(done / max(1, total), 16)
    console.print(f"  [muted]{label}[/muted] [{bar}] {done}/{total}")


def heatmap(console, days: list[int], width: int = 28) -> None:
    # days: counts per day, oldest first. quiet ink dots.
    if not days:
        console.print("[muted]no history yet.[/muted]")
        return
    row = ""
    for v in days[-width:]:
        row += "#" if v >= 3 else ("=" if v == 2 else ("-" if v == 1 else "."))
    console.print(f"[muted]{row}[/muted]")
    console.print("[muted]. empty  - one  = two  # deep[/muted]")


def dashboard_panels(console, status: dict, streak_days: list[int] | None = None) -> None:
    from rich.columns import Columns
    docs = status.get("docs", 0)
    chunks = status.get("chunks", 0)
    model = status.get("model", "?")
    console.print("")
    console.print(f"[muted]library[/muted]  {docs} docs   {chunks} chunks   [muted]{model}[/muted]")
    ink_rule(console, 40)
    mastery = status.get("mastery", [])[:5]
    if mastery:
        console.print("[muted]recent[/muted]")
        for m in mastery:
            enso = enso_for_streak(m.get("streak", 0))
            console.print(f"  [accent]{enso}[/accent] {m.get('concept')} [muted]- {m.get('state','').lower()}[/muted]")
    if streak_days is not None:
        console.print("")
        console.print("[muted]last days[/muted]")
        heatmap(console, streak_days)
    console.print("")


def welcome(console, animate: bool = False, no_animation: bool = False, fast: bool = False) -> None:
    from . import wordmark as W
    if animate:
        W.play(console, forced_off=no_animation, fast=fast)
    else:
        W.print_static(console)
    console.print("[muted]Ask anything about your material.  /help for commands.  /exit to leave.[/muted]")
    console.print("")


def turn_divider(console) -> None:
    console.print(Rule(style="#3A3A3A"))


def answer_serene(console, text: str, citations, limit: int = 2) -> None:
    console.print("")
    console.print(Markdown(text.strip()))
    console.print("")
    chips(console, citations, limit)
    console.print("")


def palette_help(console) -> None:
    from rich.table import Table as _T
    from rich import box as _box
    t = _T(box=_box.SIMPLE, show_header=False, padding=(0, 3))
    t.add_column("Command", style="accent", no_wrap=True)
    t.add_column("What it does", style="muted")
    for cmd, desc in [
        ("/quiz [topic]", "quiz me, re-teaches on wrong answers"),
        ("/flash [topic]", "flip cards, grade 1-3"),
        ("/battle [topic]", "timed drill"),
        ("/daily", "one weak + one new"),
        ("/drill", "loop weakest to empty"),
        ("/focus [min]", "silent timer"),
        ("/explain <idea>", "explain from your material"),
        ("/teach <idea>", "teach it simply"),
        ("/search <q>", "library cards, instant"),
        ("/review", "re-practice weakest concept"),
        ("/more", "show quotes for the last answer"),
        ("/sources", "list indexed files"),
        ("/ingest <path>", "index a file or folder"),
        ("/progress", "mastery table"),
        ("/stats", "ink overview + heatmap"),
        ("/streak", "current run"),
        ("/history", "recent attempts"),
        ("/journal", "append today to diary"),
        ("/doctor", "check setup"),
        ("/clear", "clear the screen"),
        ("/exit", "leave"),
    ]:
        t.add_row(cmd, desc)
    console.print("")
    console.print(t)
    console.print("")


def session_prompt(console, warm: bool = False) -> str:
    marker = "honey" if warm else "accent"
    glyph = "・" if warm else "?"
    console.print(f"[{marker}]{glyph}[/{marker}] ", end="")
    return Prompt.ask("", console=console)


def motion_on(console, no_animation: bool = False) -> bool:
    from .wordmark import should_animate
    try:
        return bool(should_animate(console, forced_off=no_animation))
    except Exception:
        return False


def answer_cascade(console, text: str, citations, limit: int = 2, animate: bool = False) -> None:
    """Brush reveal: line-by-line when motion on, instant Markdown otherwise."""
    console.print("")
    if animate:
        try:
            from .motion import brush_lines
            brush_lines(console, text.strip())
        except Exception:
            import time as _t
            for line in text.strip().splitlines():
                console.print(line)
                _t.sleep(0.012)
    else:
        console.print(Markdown(text.strip()))
    console.print("")
    chips(console, citations, limit)
    console.print("")


def say_verdict(console, verdict: str, explanation: str, animate: bool = False) -> None:
    """Hanko seal lands first, explanation follows a beat later."""
    try:
        seal_verdict(console, verdict, "")
    except Exception:
        style = verdict_style(verdict)
        console.print(f"[{style}]{verdict}[/{style}]")
    if explanation:
        if animate:
            import time as _t
            _t.sleep(0.12)
        console.print(f"[muted]{explanation}[/muted]")


def answer_compact(console, text: str, citations, limit: int = 2) -> None:
    console.print("")
    console.print(Markdown(text.strip()))
    chips(console, citations, limit)
    console.print("")


def chips(console, citations, limit: int = 2) -> None:
    if not citations:
        return
    parts = "  ".join(
        f"[accent][{i}][/accent] [muted]{c.filename} p.{c.page or '?'}[/muted]"
        for i, c in enumerate(citations[:limit], 1)
    )
    console.print(parts)
    console.print("[muted]/more for quotes[/muted]")


def quotes_expanded(console, citations, limit: int = 4) -> None:
    for i, c in enumerate(citations[:limit], 1):
        console.print(f"  [accent][{i}][/accent] {c.filename} - p.{c.page or '?'}")
        if c.quote:
            console.print(f"      [muted]\"{c.quote[:160]}\"[/muted]")


def hint(console, text: str) -> None:
    console.print(f"[muted]{text}[/muted]")


HELP_TEXT = (
    "Ask anything, or use a command:\n"
    "  /quiz [topic]     quiz me (re-teaches on wrong answers)\n"
    "  /flash [topic]    flip cards\n"
    "  /battle [topic]   timed drill\n"
    "  /daily            one weak + one new\n"
    "  /drill            weakest to empty\n"
    "  /focus [min]      silent timer\n"
    "  /explain <idea>   explain from your material\n"
    "  /teach <idea>     teach it simply\n"
    "  /search <q>       library cards\n"
    "  /review           re-practice weakest concept\n"
    "  /more             show quotes for the last answer\n"
    "  /sources          list indexed files\n"
    "  /ingest <path>    index a file or folder\n"
    "  /progress         mastery table\n"
    "  /stats            overview + heatmap\n"
    "  /doctor           check setup\n"
    "  /clear            clear the screen\n"
    "  /exit             leave"
)
