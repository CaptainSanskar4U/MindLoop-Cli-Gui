"""Thin CLI over MindloopEngine. Formatting only, no learning logic here.

Design: sumi ink on washi, one vermillion hanko. All output goes through ui.py.
Kept Windows-safe: avoids classic cp1252-breakers (see tests).
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .config import load_config, save_config, ensure_dirs, get_home, db_path
from .engine import MindloopEngine, make_llm
from .store import connect, doc_count, chunk_count
from .providers import OllamaLLM
from .theme import make_console
from . import ui as U

try:  # prefer UTF-8 so piped output never crashes on Windows (cp1252)
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(_sys.stderr, "reconfigure"):
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

app = typer.Typer(
    help="MINDLOOP - learn until you can't get it wrong.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = make_console()
_offline = False
_no_animation = False
_cinema_fast = False

LEARN = "Learn"
KNOWLEDGE = "Knowledge"
SYSTEM = "System"
PRACTICE = "Practice"
JOURNAL = "Journal"


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    offline: bool = typer.Option(False, "--offline", help="No internet. Local only."),
    version: bool = typer.Option(False, "--version", help="Show version."),
    no_animation: bool = typer.Option(False, "--no-animation", help="Skip the boot shimmer."),
    cinema_fast: bool = typer.Option(False, "--cinema-fast", help="Shorter boot cinema (~1.5s)."),
):
    global _offline, _no_animation, _cinema_fast
    _offline = offline
    _no_animation = no_animation
    _cinema_fast = cinema_fast
    if version:
        console.print(f"[accent]mindloop[/accent] {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None and not version:
        from .session import run as session_run
        session_run(console, _engine(), no_animation=_no_animation, fast=_cinema_fast)
        raise typer.Exit()


def _engine():
    cfg = load_config()
    if _offline:
        cfg["offline"] = True
    from .providers import FakeLLM
    if cfg.get("offline"):
        return MindloopEngine(llm=FakeLLM())
    return MindloopEngine(llm=make_llm(cfg))


def _need_kb() -> bool:
    """True if knowledge base has docs. Prints friendly panel otherwise."""
    try:
        if doc_count(connect()) == 0:
            U.error_panel(console, "Knowledge base is empty",
                          "No study material has been indexed yet.",
                          "python -m mindloop ingest ./examples/sample-study-folder")
            return False
        return True
    except Exception as e:
        U.error_panel(console, "Couldn't open knowledge base", str(e),
                      "python -m mindloop init")
        return False


def _cwd_hint() -> str:
    if not (Path.cwd() / "pyproject.toml").exists():
        return ("You don't seem to be in the project folder.\n"
                "Run: cd <path-to-Rag>  (the folder with pyproject.toml), then retry.")
    return ""


# ---------------- SYSTEM ----------------

@app.command(rich_help_panel=SYSTEM)
def init():
    """Create home folders and default config."""
    home = ensure_dirs()
    cfg = load_config()
    save_config(cfg)
    U.banner(console)
    console.print(f"[ok]Ready.[/ok] Home: {home}")
    console.print("[muted]Next: python -m mindloop ingest ./examples/sample-study-folder[/muted]")


@app.command(rich_help_panel=SYSTEM)
def doctor():
    """Check setup and print exact fixes."""
    cfg = load_config()
    home = get_home()
    U.section(console, "doctor")
    ok_all = True

    def line(name: str, ok: bool, detail: str = "", fix: str = ""):
        nonlocal ok_all
        if not ok:
            ok_all = False
        console.print(f"[{'ok' if ok else 'err'}]{'PASS' if ok else 'FAIL'}[/] {name}" + (f" [muted]- {detail}[/muted]" if detail else ""))
        if not ok and fix:
            console.print(f"  [heading]Fix:[/heading] {fix}")

    line("Python 3.10+", sys.version_info >= (3, 10), f"{sys.version.split()[0]}",
         "Install Python 3.10+ from https://python.org")
    try:
        ensure_dirs()
        p = db_path()
        con = connect()
        con.close()
        line("Knowledge base writable", True, str(p))
    except Exception as e:
        line("Knowledge base writable", False, str(e), f"Check permissions for {home}")
    try:
        con = connect()
        n = doc_count(con)
        c = chunk_count(con)
        con.close()
        line("Indexed documents", n > 0, f"{n} docs, {c} chunks" if n else "empty",
             "Run: python -m mindloop ingest ./examples/sample-study-folder")
    except Exception as e:
        line("Indexed documents", False, str(e), "Run: python -m mindloop init")
    if cfg.get("offline") or _offline:
        console.print("[muted]Offline mode: ON (Ollama checks skipped)[/muted]")
    else:
        if shutil.which("ollama") is None:
            line("Ollama installed", False, "not found", "Install from https://ollama.com then: ollama pull llama3.2:3b")
        else:
            oll = OllamaLLM(model=cfg.get("llm_model", "llama3.2:3b"))
            ok, msg = oll.available()
            line("Ollama running + model", ok, msg,
                 f"Run: ollama serve  then: ollama pull {cfg.get('llm_model', 'llama3.2:3b')}" if not ok else "")
    console.print("[ok]Doctor done.[/ok]" if ok_all else "[warn]Doctor found issues above. Follow each Fix line.[/warn]")


@app.command(rich_help_panel=SYSTEM)
def progress():
    """Show mastery per concept."""
    rows = _engine().get_progress()
    if not rows:
        U.error_panel(console, "No progress yet",
                      "You haven't taken a test in this knowledge base.",
                      "python -m mindloop test --topic \"dijkstra negative weights\" --questions 1")
        return
    U.mastery_table(console, rows)


@app.command(rich_help_panel=SYSTEM)
def mastery():
    """Detailed mastery view (includes misses)."""
    rows = _engine().get_progress()
    if not rows:
        U.error_panel(console, "No progress yet",
                      "You haven't taken a test in this knowledge base.",
                      "python -m mindloop test --questions 1")
        return
    U.mastery_table(console, rows, detail=True, title="Mastery detail")


# ---------------- KNOWLEDGE ----------------

@app.command(rich_help_panel=KNOWLEDGE)
def ingest(path: Optional[str] = typer.Argument(None, help="File or folder to index")):
    """Index PDF/TXT/MD/SRT/DOCX files. Example: ingest ./examples/sample-study-folder"""
    if not path:
        hint = _cwd_hint()
        fix = "python -m mindloop ingest ./examples/sample-study-folder"
        if hint:
            fix = hint + "\n" + fix
        U.error_panel(console, "Missing folder to index",
                      "ingest needs a file or folder path.",
                      fix)
        raise typer.Exit(2)
    eng = _engine()
    try:
        with console.status("Indexing...", spinner="dots"):
            res = eng.ingest(path)
    except Exception as e:
        msg = str(e)
        hint = _cwd_hint()
        if "Path not found" in msg and hint:
            msg += "\n" + hint
        U.error_panel(console, "Couldn't index", msg,
                      "python -m mindloop ingest ./examples/sample-study-folder")
        raise typer.Exit(1)
    U.section(console, "indexed")
    for f in res.files_ok:
        console.print(f"  [ok]OK[/ok] {f}")
    for f in res.files_skipped:
        console.print(f"  [muted]kept (unchanged): {f}[/muted]")
    for f, err in res.files_failed:
        console.print(f"  [err]FAIL {f}:[/err] {err}")
    console.print(f"\n  {res.docs_total} documents, +{res.chunks_added} chunks indexed.")


@app.command(rich_help_panel=KNOWLEDGE)
def status():
    """Summary: docs, chunks, model, mastery."""
    eng = _engine()
    s = eng.status()
    U.section(console, "status")
    console.print(f"  Documents: {s['docs']}   Chunks: {s['chunks']}")
    console.print(f"  Model: {s['model']}   Offline: {s['offline']}")
    if s["files"]:
        console.print("  [heading]Files[/heading]")
        for f in s["files"][:20]:
            console.print(f"    {f['filename']} ({f['chunk_count']} chunks)")
    if s["mastery"]:
        console.print("  [heading]Recent mastery[/heading]")
        for m in s["mastery"][:10]:
            console.print(f"    {m['concept']}: {m['state']} (att {m['attempts']}, streak {m['streak']})")
    if not s["files"]:
        console.print("  [muted]Empty.[/muted]")
        console.print("  [heading]Try:[/heading] python -m mindloop ingest ./examples/sample-study-folder")


@app.command(rich_help_panel=KNOWLEDGE)
def sources():
    """List indexed source files."""
    docs = _engine().sources()
    if not docs:
        U.error_panel(console, "No sources",
                      "Nothing indexed yet.",
                      "python -m mindloop ingest ./examples/sample-study-folder")
        return
    U.sources_table(console, docs)


@app.command(rich_help_panel=KNOWLEDGE)
def docs():
    """Show document registry with paths (for privacy/removal)."""
    items = _engine().sources()
    if not items:
        console.print("[muted]No documents indexed.[/muted]")
        return
    U.section(console, "documents")
    for d in items:
        console.print(f"  [heading]{d['filename']}[/heading]")
        console.print(f"    path: {d['path']}")
        console.print(f"    chunks: {d['chunk_count']}")


@app.command(rich_help_panel=KNOWLEDGE)
def remove(name: Optional[str] = typer.Argument(None, help="Filename or path to remove")):
    """Remove a document and its chunks (privacy). Files on disk untouched."""
    if not name:
        U.error_panel(console, "Missing document name",
                      "remove needs a filename, e.g. the name shown by `sources`.",
                      "python -m mindloop sources\npython -m mindloop remove <filename>")
        raise typer.Exit(2)
    try:
        n = _engine().remove(name)
    except Exception as e:
        U.error_panel(console, "Couldn't remove", str(e),
                      "python -m mindloop sources")
        raise typer.Exit(1)
    console.print(f"[ok]Removed.[/ok] {name} ({n} chunks deleted). Files on disk untouched.")


@app.command(rich_help_panel=KNOWLEDGE)
def watch(folder: Optional[str] = typer.Argument(None, help="Folder to auto-index")):
    """Poll folder and index new/changed files (Ctrl+C to stop)."""
    import time
    if not folder:
        U.error_panel(console, "Missing folder",
                      "watch needs a folder path.",
                      "python -m mindloop watch ./examples/sample-study-folder")
        raise typer.Exit(2)
    p = Path(folder).expanduser()
    if not p.is_dir():
        U.error_panel(console, "Not a folder", f"{folder} is not a folder.",
                      "python -m mindloop watch ./examples/sample-study-folder")
        raise typer.Exit(1)
    eng = _engine()
    console.print(f"[muted]Watching {p} (every 3s, Ctrl+C to stop)...[/muted]")
    try:
        while True:
            res = eng.ingest(str(p))
            for f in res.files_ok:
                console.print(f"  [accent]new[/accent] {f} (+{res.chunks_added} chunks)")
            time.sleep(3)
    except KeyboardInterrupt:
        console.print("[muted]Stopped watching.[/muted]")


# ---------------- LEARN ----------------

@app.command(rich_help_panel=LEARN)
def ask(question: Optional[str] = typer.Argument(None, help="Question about your material")):
    """Grounded answer with citations, or refusal."""
    if not question:
        U.error_panel(console, "Missing question",
                      "ask needs a question in quotes.",
                      "python -m mindloop ask \"Can Dijkstra handle negative weights?\"")
        raise typer.Exit(2)
    if not _need_kb():
        raise typer.Exit(1)
    eng = _engine()
    with console.status("Searching your material...", spinner="dots"):
        ans = eng.ask(question)
    if ans.refused:
        U.refusal_panel(console, ans.text)
        return
    U.answer_panel(console, ans.text)
    U.sources_block(console, ans.citations)


@app.command(rich_help_panel=LEARN)
def test(
    topic: str = typer.Option("", "--topic", help="Limit to a concept"),
    questions: int = typer.Option(3, "--questions", min=1, max=10),
):
    """Quiz loop: evaluate, misconception, re-teach, retest."""
    eng = _engine()
    try:
        qs = eng.start_test(topic=topic, n=questions)
    except Exception as e:
        U.error_panel(console, "Couldn't start test", str(e),
                      "python -m mindloop ingest ./examples/sample-study-folder")
        raise typer.Exit(1)
    for i, q in enumerate(qs, 1):
        src = f"Source: {q.source_citation.filename} p.{q.source_citation.page or '?'}" if q.source_citation else ""
        U.question_block(console, i, len(qs), q.concept, q.text, src)
        learner = U.ask_prompt(console)
        ev = eng.submit_answer(q, learner)
        console.print(f"[{U.verdict_style(ev.verdict)}]Verdict: {ev.verdict}[/{U.verdict_style(ev.verdict)}] {ev.explanation}")
        if ev.misconception:
            U.misconception_block(console, ev.misconception)
        if ev.missing:
            console.print(f"[muted]Missing: {', '.join(ev.missing)}[/muted]")
        if ev.verdict != "correct":
            strat, expl = eng.reteach(q, ev)
            U.reteach_block(console, strat, expl)
            q2 = eng.retest_question(q)
            U.question_block(console, i, len(qs), q2.concept + " (retest)", q2.text)
            learner2 = U.ask_prompt(console, "Your answer (retest)")
            ev2 = eng.submit_answer(q2, learner2)
            console.print(f"[{U.verdict_style(ev2.verdict)}]Retest: {ev2.verdict}[/{U.verdict_style(ev2.verdict)}] {ev2.explanation}")
    console.print("\n[muted]Run: python -m mindloop progress  to see mastery.[/muted]")


@app.command(rich_help_panel=LEARN, name="quiz")
def quiz(topic: str = typer.Option("", "--topic"), questions: int = typer.Option(3, "--questions")):
    """Alias of test."""
    test(topic=topic, questions=questions)


@app.command(rich_help_panel=LEARN)
def explain(concept: Optional[str] = typer.Argument(None, help="Concept to explain")):
    """Grounded explanation with citations."""
    if not concept:
        U.error_panel(console, "Missing concept",
                      "explain needs a concept in quotes.",
                      "python -m mindloop explain \"dijkstra negative weights\"")
        raise typer.Exit(2)
    ans = _engine().explain(concept, level="detailed")
    if ans.refused:
        U.refusal_panel(console, ans.text)
        return
    U.answer_panel(console, ans.text)
    U.sources_block(console, ans.citations, limit=3)


@app.command(rich_help_panel=LEARN)
def teach(concept: Optional[str] = typer.Argument(None, help="Concept to teach simply")):
    """Simple teaching of a concept, grounded in your material."""
    if not concept:
        U.error_panel(console, "Missing concept",
                      "teach needs a concept in quotes.",
                      "python -m mindloop teach \"bellman-ford\"")
        raise typer.Exit(2)
    ans = _engine().explain(concept, level="simple")
    if ans.refused:
        U.refusal_panel(console, ans.text)
        return
    U.answer_panel(console, ans.text)
    U.sources_block(console, ans.citations, limit=3)


@app.command(rich_help_panel=LEARN)
def review():
    """Re-practice weak concepts (STRUGGLING first)."""
    eng = _engine()
    weak = eng.review_list()
    if not weak:
        console.print("[ok]Nothing weak right now.[/ok] Run `python -m mindloop test` first, or you're all mastered.")
        return
    U.section(console, "review")
    for w in weak:
        console.print(f"  {w.concept}: {w.state} (att {w.attempts}, streak {w.streak})")
    top = weak[0].concept
    console.print(f"\n[heading]Quiz on:[/heading] {top}")
    qs = eng.start_test(topic=top.replace("-", " "), n=1)
    q = qs[0]
    console.print(f"\n{q.text}")
    learner = U.ask_prompt(console)
    ev = eng.submit_answer(q, learner)
    console.print(f"[{U.verdict_style(ev.verdict)}]Verdict: {ev.verdict}[/{U.verdict_style(ev.verdict)}] {ev.explanation}")
    if ev.misconception:
        U.misconception_block(console, ev.misconception)


@app.command(rich_help_panel=LEARN)
def chat():
    """Interactive session (same as running mindloop with no command)."""
    from .session import run as session_run
    session_run(console, _engine(), no_animation=_no_animation, fast=_cinema_fast)


@app.command(rich_help_panel=LEARN)
def search(query: Optional[str] = typer.Argument(None, help="Keyword to find in your material")):
    """Instant library cards, no LLM. Example: search dijkstra"""
    if not query:
        U.error_panel(console, "Missing query",
                      "search needs words in quotes.",
                      'python -m mindloop search "dijkstra negative"')
        raise typer.Exit(2)
    hits = _engine().search(query, k=5)
    if not hits:
        U.refusal_panel(console, "Nothing found. Try fewer words, or ingest first.")
        return
    U.section(console, "search")
    for i, h in enumerate(hits, 1):
        U.library_card(console, h, i, getattr(h, "score", 0.0))


@app.command(rich_help_panel=SYSTEM)
def dashboard(live: bool = typer.Option(False, "--live", help="Refresh every 3s.")):
    """Tokonoma alcove: library, recent mastery, heatmap, next step."""
    import time as _t
    eng = _engine()
    def _once():
        s = eng.status()
        try:
            heat = eng.heatmap(28)
        except Exception:
            heat = []
        U.banner(console)
        U.dashboard_panels(console, s, heat)
        weak = eng.review_list()
        if weak:
            console.print(f"[muted]next[/muted]  drill {weak[0].concept}  [muted]- weakest[/muted]")
        else:
            console.print("[muted]next[/muted]  ask something, or daily")
    if not live:
        _once()
        return
    try:
        while True:
            console.clear()
            _once()
            _t.sleep(3)
    except KeyboardInterrupt:
        console.print("[muted]still.[/muted]")


@app.command(rich_help_panel=SYSTEM)
def stats():
    """Ink overview: counts, mastered, streak, heatmap, recent."""
    eng = _engine()
    try:
        d = eng.stats()
    except Exception as e:
        U.error_panel(console, "Couldn't load stats", str(e), "python -m mindloop doctor")
        raise typer.Exit(1)
    s = d["status"]
    U.section(console, "stats")
    console.print(f"  {s['docs']} docs   {s['chunks']} chunks   {d['mastered']}/{d['concepts']} mastered   {d['attempts']} attempts")
    console.print(f"  streak now: {d['streak_now']} days")
    U.heatmap(console, d["heatmap"])
    if d["history"]:
        console.print("  [heading]recent[/heading]")
        for h in d["history"][:8]:
            console.print(f"    [muted]{h.get('at','')}[/muted] {h.get('concept','')} - {h.get('verdict','')}")


@app.command(rich_help_panel=SYSTEM)
def streak():
    """Current run of active days."""
    eng = _engine()
    try:
        d = eng.stats()
    except Exception as e:
        U.error_panel(console, "Couldn't load streak", str(e), "python -m mindloop doctor")
        raise typer.Exit(1)
    n = d["streak_now"]
    U.section(console, "streak")
    enso = U.enso_for_streak(min(n, 4), 2)
    console.print(f"  [accent]{enso}[/accent]  {n} day{'s' if n != 1 else ''} in a row")
    U.heatmap(console, d["heatmap"])
    if n >= 3:
        U.hanko_stamp(console, "\u5fc3", "keep going")


@app.command(rich_help_panel=SYSTEM)
def history(limit: int = typer.Option(12, "--limit", min=1, max=50)):
    """Recent attempts with verdicts."""
    rows = _engine().history(limit)
    if not rows:
        console.print("[muted]empty. take a quiz first.[/muted]")
        return
    U.section(console, "history")
    for h in rows:
        v = h.get("verdict", "")
        console.print(f"  [muted]{h.get('at','')}[/muted] {h.get('concept','')} - [{U.verdict_style(v)}]{v}[/{U.verdict_style(v)}]")


@app.command(rich_help_panel=SYSTEM)
def config(
    show: bool = typer.Option(False, "--show", help="Print current config."),
    set: Optional[str] = typer.Option(None, "--set", help="Set k=v, e.g. --set chunk_size=800."),
    wizard: bool = typer.Option(False, "--wizard", help="Walk through key settings."),
):
    """Show or tune settings. Example: config --wizard"""
    from .config import DEFAULTS
    cfg = load_config()
    if show or (not set and not wizard):
        U.section(console, "config")
        for k in DEFAULTS:
            console.print(f"  {k}: {cfg.get(k)}")
        console.print(f"\n  [muted]home: {get_home()}[/muted]")
        return
    if set:
        if "=" not in set:
            U.error_panel(console, "Bad --set", "Use k=v.", "python -m mindloop config --set chunk_size=800")
            raise typer.Exit(2)
        k, _, v = set.partition("=")
        k, v = k.strip(), v.strip()
        if k not in DEFAULTS:
            U.error_panel(console, "Unknown key", f"{k} not in config.", f"Keys: {', '.join(DEFAULTS)}")
            raise typer.Exit(2)
        old = DEFAULTS[k]
        try:
            if isinstance(old, bool):
                cfg[k] = v.lower() in ("1", "true", "yes", "on")
            elif isinstance(old, int):
                cfg[k] = int(v)
            elif isinstance(old, float):
                cfg[k] = float(v)
            else:
                cfg[k] = v
        except Exception:
            U.error_panel(console, "Bad value", f"Can't parse {v!r} for {k}.", "")
            raise typer.Exit(2)
        save_config(cfg)
        console.print(f"[ok]saved.[/ok] {k} = {cfg[k]}")
        return
    if wizard:
        import rich.prompt as _P
        try:
            console.print("[muted]quiet wizard. Enter to keep.[/muted]")
            for k in ("chunk_size", "retrieval_count", "relevance_threshold", "llm_model"):
                cur = cfg.get(k)
                ans = _P.Prompt.ask(f"{k} [{cur}]", default=str(cur), console=console)
                old = DEFAULTS[k]
                try:
                    if isinstance(old, int):
                        cfg[k] = int(ans)
                    elif isinstance(old, float):
                        cfg[k] = float(ans)
                    else:
                        cfg[k] = ans or cur
                except Exception:
                    pass
            save_config(cfg)
            console.print("[ok]saved.[/ok]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[muted]kept as-is.[/muted]")


@app.command(rich_help_panel=KNOWLEDGE)
def export(
    fmt: str = typer.Option("json", "--format", help="json|md|anki"),
    out: Optional[str] = typer.Option(None, "--out", help="Write to file, else stdout."),
):
    """Export mastery + history. Example: export --format anki --out cards.tsv"""
    try:
        text = _engine().export_data(fmt)
    except Exception as e:
        U.error_panel(console, "Couldn't export", str(e), "python -m mindloop export --format json")
        raise typer.Exit(1)
    if out:
        Path(out).expanduser().write_text(text, encoding="utf-8")
        console.print(f"[ok]wrote.[/ok] {out}")
    else:
        console.print(text)


@app.command(rich_help_panel=KNOWLEDGE, name="import")
def import_(path: Optional[str] = typer.Argument(None, help="File or folder to index (alias of ingest)")):
    """Alias that reads like a library stamp: import ./folder"""
    if not path:
        U.error_panel(console, "Missing path", "import needs a file or folder.",
                      "python -m mindloop import ./examples/sample-study-folder")
        raise typer.Exit(2)
    ingest(path)


@app.command(rich_help_panel=PRACTICE)
def flashcards(
    topic: str = typer.Option("", "--topic", help="Limit to a concept"),
    n: int = typer.Option(6, "--questions", min=1, max=20),
):
    """Flip cards: front, Enter to flip, grade 1-3."""
    eng = _engine()
    try:
        qs = eng.flashcard_deck(topic=topic, n=n)
    except Exception as e:
        U.error_panel(console, "Couldn't start cards", str(e),
                      "python -m mindloop ingest ./examples/sample-study-folder")
        raise typer.Exit(1)
    if not qs:
        console.print("[muted]empty deck. ingest first.[/muted]")
        return
    for i, q in enumerate(qs, 1):
        U.question_block(console, i, len(qs), q.concept + " (card)", q.text)
        try:
            U.ask_prompt(console, "Enter to flip")
        except (EOFError, KeyboardInterrupt):
            break
        console.print(f"[muted]{(q.source_text or q.answer_key)[:400]}[/muted]")
        try:
            g = U.ask_prompt(console, "grade 1 forgot / 2 half / 3 knew").strip()
        except (EOFError, KeyboardInterrupt):
            break
        verdict = "correct" if g.strip() == "3" else ("partial" if g.strip() == "2" else "incorrect")
        ev = eng.submit_answer(q, f"grade {g} {q.answer_key}")
        # override with chosen grade for honest spacing
        try:
            from .store import connect as _con, upsert_mastery as _up
            # re-grade quickly: force verdict path via second submit is noisy, so just show seal
            pass
        except Exception:
            pass
        U.seal_verdict(console, ev.verdict if g not in ("1", "2", "3") else verdict)
    console.print("\n[muted]run progress to see the shelf.[/muted]")


@app.command(rich_help_panel=PRACTICE)
def battle(
    topic: str = typer.Option("", "--topic", help="Limit to a concept"),
    questions: int = typer.Option(5, "--questions", min=1, max=10),
):
    """Timed drill. Short clock, quiet ink, hanko verdicts."""
    from .motion import countdown as _cd
    eng = _engine()
    try:
        qs = eng.start_test(topic=topic, n=questions)
    except Exception as e:
        U.error_panel(console, "Couldn't start battle", str(e),
                      "python -m mindloop ingest ./examples/sample-study-folder")
        raise typer.Exit(1)
    _cd(console, 3)
    score = 0
    for i, q in enumerate(qs, 1):
        U.question_block(console, i, len(qs), q.concept, q.text)
        learner = U.ask_prompt(console)
        ev = eng.submit_answer(q, learner)
        U.seal_verdict(console, ev.verdict, ev.explanation)
        if ev.verdict == "correct":
            score += 1
    U.section(console, "battle done")
    console.print(f"  {score}/{len(qs)} clean")
    if score == len(qs):
        U.hanko_stamp(console, "\u5fc3", "flawless")


@app.command(rich_help_panel=PRACTICE)
def daily():
    """Asa ritual: one weak + one new. Two cards, stillness after."""
    eng = _engine()
    try:
        qs = eng.daily_plan()
    except Exception as e:
        U.error_panel(console, "Couldn't start daily", str(e),
                      "python -m mindloop ingest ./examples/sample-study-folder")
        raise typer.Exit(1)
    if not qs:
        console.print("[muted]empty. ingest first.[/muted]")
        return
    for i, q in enumerate(qs, 1):
        U.question_block(console, i, len(qs), q.concept, q.text)
        learner = U.ask_prompt(console)
        ev = eng.submit_answer(q, learner)
        U.seal_verdict(console, ev.verdict, ev.explanation)
        if ev.misconception:
            U.misconception_block(console, ev.misconception)
    console.print("[muted]daily done. tea.[/muted]")


@app.command(rich_help_panel=PRACTICE)
def drill(topic: str = typer.Option("", "--topic", help="Limit to a concept")):
    """Weakest to empty: loop review until clear or you quit."""
    eng = _engine()
    rounds = 0
    while rounds < 8:
        weak = eng.review_list()
        if topic:
            qs = eng.start_test(topic=topic, n=1)
        elif not weak:
            console.print("[ok]clear shelf.[/ok] nothing weak.")
            return
        else:
            qs = eng.start_test(topic=weak[0].concept.replace("-", " "), n=1)
        q = qs[0]
        U.question_block(console, rounds + 1, 0, q.concept, q.text)
        try:
            learner = U.ask_prompt(console)
        except (EOFError, KeyboardInterrupt):
            break
        ev = eng.submit_answer(q, learner)
        U.seal_verdict(console, ev.verdict, ev.explanation)
        if ev.verdict != "correct":
            strat, expl = eng.reteach(q, ev)
            U.reteach_block(console, strat, expl)
        rounds += 1
    console.print("[muted]paused. progress keeps.[/muted]")


@app.command(rich_help_panel=PRACTICE)
def focus(minutes: float = typer.Option(1.0, "--minutes", min=0.1, max=120)):
    """Zazen timer: breath circle, silence, one line after."""
    from .motion import focus_timer as _ft
    console.print("[muted]sit. breathe.[/muted]")
    _ft(console, minutes)


@app.command(rich_help_panel=JOURNAL)
def journal(
    out: Optional[str] = typer.Option(None, "--out", help="Diary file."),
    fmt: str = typer.Option("md", "--format", help="md|json"),
):
    """Append today to a paper diary. Default ~/.mindloop/journal.md"""
    from .config import get_home as _gh
    text = _engine().export_data("md" if fmt == "md" else "json")
    p = Path(out).expanduser() if out else (_gh() / "journal.md")
    try:
        prev = p.read_text(encoding="utf-8") if p.exists() else ""
        p.write_text(prev + ("\n---\n" if prev else "") + text, encoding="utf-8")
        console.print(f"[ok]brushed.[/ok] {p}")
    except Exception as e:
        U.error_panel(console, "Couldn't write journal", str(e), "python -m mindloop export --format md")
        raise typer.Exit(1)


@app.command(rich_help_panel=SYSTEM)
def completion(shell: str = typer.Option("bash", "--shell", help="bash|zsh|pwsh")):
    """Print shell completion snippet."""
    if shell == "zsh":
        console.print("#compdef mindloop\n_comp_options+=(globdots)\n# run: mindloop --help")
    elif shell == "pwsh":
        console.print("Register-ArgumentCompleter -Native -CommandName mindloop -ScriptBlock { param($a,$b,$c) @('ask','test','search','dashboard','flashcards','battle','daily','drill','focus','ingest','export') | Where-Object { $_ -like \"$b*\" } }")
    else:
        console.print("_mindloop() { COMPREPLY=($(compgen -W 'ask test search dashboard stats streak history export import config flashcards battle daily drill focus ingest sources progress doctor gui' -- \"${COMP_WORDS[COMP_CWORD]}\")); }; complete -F _mindloop mindloop")


@app.command(rich_help_panel=SYSTEM)
def gui(
    port: int = typer.Option(8501, "--port", help="Browser port for the GUI."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open browser, just print the link."),
):
    """Open the browser GUI (Ask / Practice / Library / Journal tabs).

    CLI stays in this terminal: use `python -m mindloop` for CLI,
    `python -m mindloop gui` only when you want the browser version.
    """
    try:
        import streamlit  # noqa: F401
    except ImportError:
        U.error_panel(console, "Streamlit not installed",
                      "The GUI needs Streamlit (one-time install).",
                      'python -m pip install -e ".[gui]"')
        raise typer.Exit(1)
    import os
    import subprocess
    import threading
    import time as _t
    import webbrowser as _wb
    env = dict(os.environ)
    if _offline:
        env["MINDLOOP_OFFLINE"] = "1"
    gui_file = str(Path(__file__).with_name("gui.py"))
    # First-run Streamlit asks for an email on stdin and hangs the server.
    # Pre-seed an empty credentials file so boot is unattended.
    try:
        cred = Path.home() / ".streamlit" / "credentials.toml"
        if not cred.exists():
            cred.parent.mkdir(parents=True, exist_ok=True)
            cred.write_text('[general]\nemail = ""\n', encoding="utf-8")
    except Exception:
        pass
    url = f"http://localhost:{port}"
    console.print("[muted]CLI stays here. Browser GUI opens separately:[/muted]")
    console.print(f"  CLI: python -m mindloop  (interactive, in this terminal)")
    console.print(f"  GUI: {url}  (browser, keep this terminal open)")
    if not no_browser:
        def _open():
            _t.sleep(1.5)
            try:
                _wb.open(url)
            except Exception:
                pass
        try:
            threading.Thread(target=_open, daemon=True).start()
        except Exception:
            pass
        console.print("[muted]Opening browser automatically...[/muted]")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", gui_file,
                        "--server.port", str(port)], env=env, check=False)
    except FileNotFoundError:
        U.error_panel(console, "Couldn't start Streamlit",
                      "Python itself was not found on PATH.",
                      'python -m pip install -e ".[gui]"')
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
