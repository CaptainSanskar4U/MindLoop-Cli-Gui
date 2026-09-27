"""Interactive session. Bare `mindloop` boots here.

Calm by design: quiet welcome, one question in, one answer out,
compact source chips, quotes only via /more. Engine owns all logic.
Kept Windows-safe (see tests).
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

from . import ui as U


def _load_history() -> None:
    try:
        from .config import get_home
        hf = get_home() / "history"
        hf.parent.mkdir(parents=True, exist_ok=True)
        try:
            import readline  # type: ignore
            try:
                readline.read_history_file(str(hf))
                readline.set_history_length(500)
            except FileNotFoundError:
                pass
        except ImportError:
            pass
    except Exception:
        pass


def _save_history() -> None:
    try:
        from .config import get_home
        hf = get_home() / "history"
        try:
            import readline  # type: ignore
            readline.write_history_file(str(hf))
        except Exception:
            pass
    except Exception:
        pass


def _suggest(cmd: str) -> str:
    import difflib as _d
    known = ["quiz", "test", "flash", "battle", "daily", "drill", "focus",
             "explain", "teach", "search", "review", "more", "sources",
             "ingest", "progress", "stats", "streak", "history", "journal",
             "doctor", "clear", "help", "exit"]
    m = _d.get_close_matches(cmd, known, n=1, cutoff=0.6)
    return m[0] if m else ""


def run(console, eng, no_animation: bool = False, fast: bool = False) -> None:
    U.welcome(console, animate=True, no_animation=no_animation, fast=fast)
    _load_history()
    last_cites: list = []
    last_q: str = ""
    turn = 0
    alive = U.motion_on(console, no_animation)
    while True:
        try:
            line = U.session_prompt(console, warm=alive and turn % 2 == 1).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[muted]Bye. Progress is saved.[/muted]")
            _save_history()
            break
        turn += 1
        if not line:
            continue
        if line.startswith("/"):
            cmd, _, rest = line[1:].partition(" ")
            cmd, rest = cmd.lower(), rest.strip()
            if cmd in ("exit", "quit", "q"):
                console.print("[muted]Bye. Progress is saved.[/muted]")
                _save_history()
                break
            elif cmd == "help":
                U.palette_help(console)
            elif cmd == "clear":
                console.clear()
                U.welcome(console)
            elif cmd == "more":
                if last_cites:
                    console.print("")
                    U.quotes_expanded(console, last_cites)
                    console.print("")
                else:
                    U.hint(console, "Nothing to expand yet. Ask a question first.")
            elif cmd == "sources":
                docs = eng.sources()
                if docs:
                    U.sources_table(console, docs)
                else:
                    U.hint(console, "No sources yet. Try: /ingest ./examples/sample-study-folder")
            elif cmd in ("quiz", "test"):
                last_cites = _quiz(console, eng, topic=rest)
            elif cmd == "flash":
                _flash(console, eng, topic=rest)
            elif cmd == "battle":
                _battle(console, eng, topic=rest)
            elif cmd == "daily":
                _daily(console, eng)
            elif cmd == "drill":
                _review(console, eng)
            elif cmd == "focus":
                _focus(console, rest)
            elif cmd == "search":
                if not rest:
                    U.hint(console, "Usage: /search <words>")
                    continue
                _search(console, eng, rest)
            elif cmd == "explain":
                if not rest:
                    U.hint(console, "Usage: /explain <idea>")
                    continue
                _explain(console, eng, rest, level="detailed")
            elif cmd == "teach":
                if not rest:
                    U.hint(console, "Usage: /teach <idea>")
                    continue
                _explain(console, eng, rest, level="simple")
            elif cmd == "review":
                _review(console, eng)
            elif cmd == "ingest":
                if not rest:
                    U.hint(console, "Usage: /ingest <file-or-folder>")
                    continue
                _ingest(console, eng, rest)
            elif cmd == "progress":
                rows = eng.get_progress()
                if rows:
                    U.mastery_table(console, rows)
                else:
                    U.hint(console, "No progress yet. Try: /quiz")
            elif cmd == "stats":
                _stats(console, eng)
            elif cmd == "streak":
                _streak(console, eng)
            elif cmd == "history":
                _history(console, eng)
            elif cmd == "journal":
                _journal(console, eng, rest)
            elif cmd == "doctor":
                _doctor(console, eng)
            else:
                sug = _suggest(cmd)
                extra = f" Did you mean /{sug}?" if sug else ""
                U.hint(console, f"Unknown command /{cmd}.{extra} Try /help.")
            continue
        # plain question -> ask
        last_q = line
        try:
            with console.status("Gathering evidence... grinding ink...", spinner="dots"):
                ans = eng.ask(line)
        except Exception as e:
            U.error_panel(console, "Couldn't answer", str(e),
                          "Try /ingest ./examples/sample-study-folder first.")
            continue
        if ans.refused:
            console.print("")
            U.refusal_panel(console, ans.text)
            console.print("")
            last_cites = list(ans.citations)
        else:
            U.answer_cascade(console, ans.text, ans.citations, animate=alive)
            last_cites = list(ans.citations)


def _explain(console, eng, concept: str, level: str) -> None:
    with console.status("Gathering evidence... laying paper...", spinner="dots"):
        ans = eng.explain(concept, level=level)
    if ans.refused:
        console.print("")
        U.refusal_panel(console, ans.text)
        console.print("")
    else:
        U.answer_cascade(console, ans.text, ans.citations, animate=U.motion_on(console))


def _search(console, eng, query: str) -> None:
    try:
        hits = eng.search(query, k=5)
    except Exception as e:
        U.error_panel(console, "Couldn't search", str(e), "/ingest ./examples/sample-study-folder")
        return
    if not hits:
        U.refusal_panel(console, "Nothing found. Try fewer words.")
        return
    U.section(console, "search")
    for i, h in enumerate(hits, 1):
        U.library_card(console, h, i, getattr(h, "score", 0.0))


def _flash(console, eng, topic: str = "") -> None:
    try:
        qs = eng.flashcard_deck(topic=topic, n=4)
    except Exception as e:
        U.error_panel(console, "Couldn't start cards", str(e), "/ingest ./examples/sample-study-folder")
        return
    for i, q in enumerate(qs, 1):
        U.question_block(console, i, len(qs), q.concept + " (card)", q.text)
        try:
            U.ask_prompt(console, "Enter to flip")
        except (EOFError, KeyboardInterrupt):
            return
        console.print(f"[muted]{(q.source_text or q.answer_key)[:380]}[/muted]")
        try:
            g = U.ask_prompt(console, "grade 1/2/3").strip()
        except (EOFError, KeyboardInterrupt):
            return
        verdict = "correct" if g == "3" else ("partial" if g == "2" else "incorrect")
        eng.submit_answer(q, f"grade {g} {q.answer_key}")
        U.seal_verdict(console, verdict)


def _battle(console, eng, topic: str = "") -> None:
    from .motion import countdown as _cd
    try:
        qs = eng.start_test(topic=topic, n=3)
    except Exception as e:
        U.error_panel(console, "Couldn't start battle", str(e), "/ingest ./examples/sample-study-folder")
        return
    _cd(console, 2)
    score = 0
    for i, q in enumerate(qs, 1):
        _quiz_turn(console, eng, q, i, len(qs))
    console.print("[muted]battle done.[/muted]")


def _daily(console, eng) -> None:
    try:
        qs = eng.daily_plan()
    except Exception as e:
        U.error_panel(console, "Couldn't start daily", str(e), "/ingest ./examples/sample-study-folder")
        return
    for i, q in enumerate(qs, 1):
        _quiz_turn(console, eng, q, i, len(qs))
    console.print("[muted]daily done. tea.[/muted]")


def _focus(console, rest: str) -> None:
    from .motion import focus_timer as _ft
    try:
        mins = float((rest or "1").strip().split()[0])
    except Exception:
        mins = 1.0
    mins = max(0.1, min(60, mins))
    console.print("[muted]sit. breathe.[/muted]")
    _ft(console, mins)


def _stats(console, eng) -> None:
    try:
        d = eng.stats()
    except Exception as e:
        U.error_panel(console, "Couldn't load stats", str(e), "/doctor")
        return
    s = d["status"]
    U.dashboard_panels(console, s, d["heatmap"])
    console.print(f"[muted]{d['mastered']}/{d['concepts']} mastered, {d['attempts']} attempts, streak {d['streak_now']}d[/muted]")


def _streak(console, eng) -> None:
    try:
        d = eng.stats()
    except Exception as e:
        U.error_panel(console, "Couldn't load streak", str(e), "/doctor")
        return
    U.section(console, "streak")
    console.print(f"  [accent]{U.enso_for_streak(min(d['streak_now'], 4), 2)}[/accent]  {d['streak_now']} days")
    U.heatmap(console, d["heatmap"])


def _history(console, eng) -> None:
    rows = eng.history(12)
    if not rows:
        U.hint(console, "empty. take a quiz first.")
        return
    U.section(console, "history")
    for h in rows:
        v = h.get("verdict", "")
        console.print(f"  [muted]{h.get('at','')}[/muted] {h.get('concept','')} - [{U.verdict_style(v)}]{v}[/{U.verdict_style(v)}]")


def _journal(console, eng, rest: str) -> None:
    from .config import get_home as _gh
    try:
        text = eng.export_data("md")
    except Exception as e:
        U.error_panel(console, "Couldn't build journal", str(e), "")
        return
    p = _gh() / "journal.md"
    try:
        prev = p.read_text(encoding="utf-8") if p.exists() else ""
        p.write_text(prev + ("\n---\n" if prev else "") + text, encoding="utf-8")
        console.print(f"[ok]brushed.[/ok] {p}")
    except Exception as e:
        U.error_panel(console, "Couldn't write journal", str(e), "")


def _ingest(console, eng, path: str) -> None:
    try:
        with console.status("Indexing...", spinner="dots"):
            res = eng.ingest(path)
    except Exception as e:
        msg = str(e)
        if "Path not found" in msg and not (Path.cwd() / "pyproject.toml").exists():
            msg += "\nYou don't seem to be in the project folder. cd to the Rag folder first."
        U.error_panel(console, "Couldn't index", msg,
                      "/ingest ./examples/sample-study-folder")
        return
    done = ", ".join(res.files_ok) if res.files_ok else "nothing new"
    console.print(f"\n[ok]Indexed.[/ok] {done}  [muted]({res.docs_total} docs)[/muted]\n")


def _quiz(console, eng, topic: str = "") -> list:
    try:
        qs = eng.start_test(topic=topic, n=1)
    except Exception as e:
        U.error_panel(console, "Couldn't start quiz", str(e),
                      "/ingest ./examples/sample-study-folder")
        return []
    q = qs[0]
    _quiz_turn(console, eng, q, 1, 1)
    console.print("")
    return []


def _quiz_turn(console, eng, q, i: int, n: int) -> None:
    console.print(f"[muted]Question {i} of {n}  ·  {q.concept}[/muted]")
    console.print("")
    from rich.markdown import Markdown
    console.print(Markdown(q.text))
    console.print("")
    try:
        learner = U.ask_prompt(console)
    except (EOFError, KeyboardInterrupt):
        console.print("\n[muted]Quiz skipped.[/muted]")
        return
    ev = eng.submit_answer(q, learner)
    U.say_verdict(console, ev.verdict, ev.explanation, animate=U.motion_on(console))
    if ev.misconception:
        U.misconception_block(console, ev.misconception)
    if ev.verdict != "correct":
        strat, expl = eng.reteach(q, ev)
        U.reteach_block(console, strat, expl)
        q2 = eng.retest_question(q)
        console.print(f"[muted]Retest  ·  {q2.concept}[/muted]")
        console.print("")
        console.print(Markdown(q2.text))
        console.print("")
        try:
            learner2 = U.ask_prompt(console, "Your answer (retest)")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[muted]Retest skipped.[/muted]")
            return
        ev2 = eng.submit_answer(q2, learner2)
        U.say_verdict(console, ev2.verdict, ev2.explanation, animate=U.motion_on(console))


def _review(console, eng) -> None:
    weak = eng.review_list()
    if not weak:
        console.print("[ok]Nothing weak.[/ok] Try /quiz, or you're mastered.")
        return
    top = weak[0]
    console.print(f"[muted]Weakest: {top.concept} ({top.state}).[/muted]")
    _quiz(console, eng, topic=top.concept.replace("-", " "))


def _doctor(console, eng) -> None:
    from .store import connect, doc_count, chunk_count
    from .config import load_config
    from .providers import OllamaLLM
    cfg = load_config()
    ok_all = True

    def line(name: str, ok: bool, detail: str = ""):
        nonlocal ok_all
        if not ok:
            ok_all = False
        console.print(f"[{'ok' if ok else 'err'}]{'PASS' if ok else 'FAIL'}[/] {name}" + (f" [muted]- {detail}[/muted]" if detail else ""))

    line("Python 3.10+", sys.version_info >= (3, 10), sys.version.split()[0])
    try:
        con = connect()
        n, c = doc_count(con), chunk_count(con)
        con.close()
        line("Knowledge base", True, f"{n} docs, {c} chunks")
    except Exception as e:
        line("Knowledge base", False, str(e))
    if cfg.get("offline"):
        console.print("[muted]Offline mode: ON[/muted]")
    elif shutil.which("ollama") is None:
        line("Ollama", False, "not found (answers still work via quotes)")
    else:
        oll = OllamaLLM(model=cfg.get("llm_model", "llama3.2:3b"))
        ok, msg = oll.available()
        line("Ollama", ok, msg)
    console.print("[ok]Healthy.[/ok]" if ok_all else "[warn]See fixes: run doctor as a command for details.[/warn]")
