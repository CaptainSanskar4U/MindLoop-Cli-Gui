# MINDLOOP — Learn until you can't get it wrong

MINDLOOP is a **local-first RAG study assistant**. You give it your own notes (PDF, TXT, Markdown, SRT transcripts). It answers **only from your material** with file + page citations, refuses when the answer isn't there, then **quizzes you, finds misconceptions, re-teaches differently, retests, and tracks mastery**.

> "It doesn't stop when it gives you the answer. It stops when you understand it."

## Why it exists

Normal AI tools stop after generating an answer. Students can copy it without understanding. MINDLOOP continues until you prove understanding: test → evaluate → misconception → re-teach (new strategy) → new retest question → mastery.

## Architecture (simple)

```
python -m mindloop <command>      <- thin CLI (Typer + Rich), formatting only
        |
MindloopEngine                    <- all logic, returns objects, no print/input
  ingest (parsers + chunking + sha256 incremental)
  store (SQLite: documents, chunks, mastery)
  retrieve (TF-IDF + cosine, offline, no model download)
  providers (OllamaLLM llama3.2:3b + FakeLLM for tests)
  ask / start_test / submit_answer / reteach / retest / progress
```

Grounding is enforced by code, not hope: threshold check before LLM, context-only prompt, citations attached from chunk metadata, verbatim quotes sliced by code. If Ollama is missing, `ask` falls back to extractive quoting so the demo never breaks.

## Installation (Windows, step by step)

You need Python 3.10+. Internet is needed once for setup.

```powershell
# 1. Go to the PROJECT folder (the one with pyproject.toml, not any other folder)
cd C:\Users\Captain\Desktop\Rag

# 2. Create a virtual environment (an isolated Python box)
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install MINDLOOP
python -m pip install -e ".[dev]"

# 4. Make sample study material
python -m mindloop.sample_data

# 5. Check setup
python -m mindloop init
python -m mindloop doctor
```

**Ollama (optional, for nicer phrasing).** Without it, everything still works with direct quotes. With it, answers read smoother:

1. Install from https://ollama.com
2. `ollama pull llama3.2:3b`
3. `ollama serve` (leave running in another terminal)

Note: `mindloop.exe` may not be on PATH on Windows. Use `python -m mindloop ...` everywhere — same thing.

## Quick start

Run these from the Rag folder. The main way to use MINDLOOP is the session:

```powershell
python -m mindloop ingest ./examples/sample-study-folder
python -m mindloop
```

Bare `python -m mindloop` boots straight into ask-mode: type a question,
get a compact answer with source chips, `/more` for quotes, `/quiz` to be
tested, `/help` for all commands, `/exit` to leave.

## Browser GUI (same engine, three tabs)

```powershell
python -m pip install -e ".[gui]"
python -m mindloop gui
```

Opens `http://localhost:8501` with **Ask** (grounded answers + citations),
**Quiz** (test → misconception → re-teach → retest → mastery table), and
**Knowledge** (ingest folder, file table, remove). Same engine as the CLI,
so CLI progress and GUI progress are shared.

One-shot commands (for scripts and demos) still work:
python -m mindloop ask "Can Dijkstra's algorithm handle negative edge weights?"
python -m mindloop ask "Who won the 2018 football world cup?"
python -m mindloop test --topic "dijkstra negative weights" --questions 1
python -m mindloop progress
python -m mindloop doctor
```

Expected:
- Q1 → grounded answer citing `dijkstra-notes.pdf p.2` (Dijkstra = no negatives, Bellman-Ford = yes).
- Q2 → refusal: "I couldn't find this in your indexed material."
- `test` → give wrong answer `Yes, Dijkstra handles negative weights` → misconception naming Bellman-Ford confusion → re-teach with a new strategy → new retest question → answer correctly → `progress` moves toward MASTERED.

Full rehearsal script: see `docs/DEMO.md`.

## Commands

| Command | What it does |
|---|---|
| `init` | Create `~/.mindloop` + default config |
| `ingest <path>` | Index file/folder (PDF/TXT/MD/SRT/DOCX), incremental by hash, cleans removed files |
| `ask "<q>"` | Grounded answer + citations or refusal |
| `test [--topic X] [--questions N]` | Quiz loop (`quiz` is an alias) |
| `progress` / `mastery` | Mastery summary / detail |
| `status` | Docs, chunks, model, recent mastery |
| `sources` / `docs` | Indexed files (table / with paths) |
| `remove <name>` | Delete doc chunks (files on disk untouched) |
| `explain <concept>` / `teach <concept>` | Grounded explanation (detailed / simple) |
| `review` | Quiz weakest concept first |
| `chat` | Interactive: ask, sources, explain, quiz, exit |
| `watch <folder>` | Auto-index every 3s (Ctrl+C to stop) |
| `doctor` | Checks + exact fixes |
| `--offline` | Force local only (e.g. `python -m mindloop --offline ask "..."`) |
| `--version`, `--help` | Standard |

## Offline mode

After setup, all study workflows work with internet off. `--offline` forces Fake/deterministic path and skips Ollama checks. `doctor` reports offline status.

## Configuration

Home: `~/.mindloop` (override with `MINDLOOP_HOME` env var, used by tests). Files: `config.json`, `mindloop.db`, `knowledge/`, `logs/`.

Defaults: `chunk_size 800`, `retrieval_count 4`, `relevance_threshold 0.12`, need 2 correct in a row to master, max 3 re-teaches then STRUGGLING.

## Development / testing

```powershell
python -m pytest -q
```

Tests use `FakeLLM` + isolated temp `MINDLOOP_HOME`, so they run offline and deterministically. Real-Ollama checks are manual via `doctor`.

## Troubleshooting

- `Knowledge base is empty` → run `ingest` first.
- `No supported files` → only PDF/TXT/MD/SRT/DOCX are indexed; others ignored.
- `scanned PDF, no extractable text` → use a text-based PDF (OCR not in this version).
- `Path not found ... examples/sample-study-folder` → you're in the wrong folder. `cd` to the Rag folder first.
- `Missing folder to index / Missing question` → the command needs an argument; the error panel shows the exact command to copy.
- `Ollama is not running` → answers still work (quotes); for nicer phrasing install Ollama + pull model.
- `charmap codec can't encode` on Windows → fixed by using ASCII output; update to latest code.
- `mindloop not recognized` → use `python -m mindloop ...`.
- Privacy: `remove` deletes indexed chunks; original files are never touched or uploaded.
