"""Single design system. Sumi ink on washi paper, one vermillion hanko.

Calm Japanese composed: muted earth inks, generous whitespace, one
seal-red accent. Backward compatible: old style names (accent/muted/ok)
still resolve so existing screens keep working.
Windows: our literals avoid the classic cp1252-breakers (see tests).
Enso/hanko glyphs used here are UTF-8 and safe because cli.py
reconfigures stdout to utf-8; piped output falls back to ASCII.
"""
from __future__ import annotations
from rich.console import Console
from rich.theme import Theme

# --- heritage amber (kept as alias) ---
AMBER = "#D9A441"
EMBER = "#8A5A1A"
HONEY = "#F2C879"

# --- sumi ink palette (primary) ---
SUMI = "#1E1E1E"
WASHI = "#E8E0CF"
STONE = "#8A8378"
HANKO = "#C73E1D"
HANKO_DIM = "#8F2C14"
MOSS = "#6B7F5E"
CLAY = "#B8963E"
RUST = "#A44A3A"
GOLD = "#C9A227"
ENSO = "#3A3A38"
MIST = "#4A4A48"

THEME = Theme({
    # brand: hanko red IS the accent now (amber kept as honey alias)
    "accent": HANKO,
    "ember": EMBER,
    "honey": HONEY,
    "amber": AMBER,
    # inks
    "sumi": SUMI,
    "washi": WASHI,
    "stone": STONE,
    "hanko": HANKO,
    "gold": GOLD,
    "enso": ENSO,
    "mist": MIST,
    "heading": "bold",
    "muted": "dim",
    # semantics in natural inks (not neon)
    "ok": MOSS,
    "warn": CLAY,
    "err": RUST,
    "moss": MOSS,
    "clay": CLAY,
    "rust": RUST,
})

def make_console() -> Console:
    return Console(theme=THEME, highlight=False)
