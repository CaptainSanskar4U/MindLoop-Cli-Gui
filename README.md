<div align="center">

# MINDLOOP 心

### Learn until you can't get it wrong.

A **local-first study engine** that answers only from *your* material — then quizzes you, finds your misconceptions, re-teaches differently, and tracks mastery.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Local-first](https://img.shields.io/badge/local--first-offline--capable-green.svg)](#offline-mode)
[![Tests](https://img.shields.io/badge/tests-46%20passing-brightgreen.svg)](#development--testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

> "It doesn't stop when it gives you the answer. It stops when you understand it."

[Quickstart](#-60-second-tour) · [Commands](#-command-reference) · [GUI](#-browser-gui) · [How it works](#-how-grounding-works)

</div>

---

## 👀 60-second tour

```powershell
python -m mindloop ingest ./examples/sample-study-folder
python -m mindloop ask "Can Dijkstra handle negative weights?"
```

```
Based on your material: Dijkstra's algorithm does NOT support negative
edge weights. Once it finalizes a node it never revisits it...

sources - grounded in your material
  [1] dijkstra-notes.pdf - p.2
  [2] dijkstra-notes.pdf - p.3
```

Ask something you *haven't* indexed and it refuses honestly instead of hallucinating:

```powershell
python -m mindloop ask "Who won the 2018 football world cup?"
# → "I couldn't find this in your indexed material."
```

Then prove you understand it:

```powershell
python -m mindloop test --topic "dijkstra negative weights" --questions 1
python -m mindloop progress
```

Answer wrong and you'll get a named misconception, a fresh re-teach, and a new retest question — `progress` moves toward `MASTERED` only when you earn it.

---

## ⚡ Why it's different

| Normal AI tools | MINDLOOP |
|---|---|
| Stop after generating an answer | Stop when **you** can answer |
| Answer from anywhere on the internet | Answer **only from your notes**, with file + page citations |
| Happy to guess | **Refuses** when the answer isn't in your material |
| One shot, then forgotten | Test → misconception → re-teach → retest → **mastery tracking** |
| Cloud, account, subscription | **Local-first**, SQLite, works offline |

---

## ✨ What you get

**Learn** — `ask` with citations or honest refusal · `test`/`quiz` loop with re-teach + retest · `explain` / `teach` at two depths · `review` weakest-first · `search` instant library cards (no LLM needed)

**Practice** — `flashcards` with 1-3 grading · `battle` timed drill · `daily` two-card ritual · `drill` weakest-to-empty loop · `focus` silent breath timer

**Know your shelf** — `dashboard` one-screen overview with heatmap · `stats` / `streak` / `history` · `export` to JSON / Markdown / Anki · `import` alias · `config --wizard`

**Live anywhere** — calm ink-wash CLI with animated boot cinema · interactive session (`python -m mindloop`) · clean browser GUI · fully offline capable

---

## 📦 Installation

Requires **Python 3.10+**. Internet needed once for setup.

```powershell
# 1. Go to the project folder (the one with pyproject.toml)
cd C:\Users\Captain\Desktop\Rag

# 2. Isolated environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install (dev extras include the test suite)
python -m pip install -e ".[dev]"

# 4. Sample study material + setup check
python -m mindloop.sample_data
python -m mindloop init
python -m mindloop doctor
```

**Nicer phrasing with Ollama (optional).** Everything works without it via direct quotes. With it, answers read smoother:

1. Install from https://ollama.com
2. `ollama pull llama3.2:3b`
3. `ollama serve` (leave running in another terminal)

> On Windows `mindloop.exe` may not be on PATH — use `python -m mindloop ...` everywhere. Same thing.

---

## 🚀 Daily use

**Interactive session** (the main way to study):

```powershell
python -m mindloop ingest ./examples/sample-study-folder
python -m mindloop
```

Inside the session: type a question, get a compact answer with source chips, `/more` for quotes, `/quiz` to be tested, `/flash` for cards, `/daily` for the ritual, `/stats` for your shelf, `/help` for everything, `/exit` to leave.

**One-shot commands** (scripts, demos, CI):

```powershell
python -m mindloop ask "Can Dijkstra's algorithm handle negative edge weights?"
python -m mindloop search "dijkstra negative"
python -m mindloop test --topic "dijkstra negative weights" --questions 3
python -m mindloop flashcards --topic "bellman-ford"
python -m mindloop daily
python -m mindloop dashboard
python -m mindloop export --format anki --out cards.tsv
```

Full rehearsal script: [`docs/DEMO.md`](docs/DEMO.md).

---

## 🖥️ Browser GUI

Same engine as the CLI — progress is shared between both.

```powershell
python -m pip install -e ".[gui]"
python -m mindloop gui
```

Opens `http://localhost:8501` with three quiet tabs:

- **Ask** — grounded answers + citation chips + evidence quotes
- **Practice** — quiz / flashcards / battle / daily with the same mastery backend
- **Library** — ingest, file table, remove, export

---

## 📖 Command reference

### Learn

| Command | What it does |
|---|---|
| `ask "<question>"` | Grounded answer + citations, or honest refusal |
| `test [--topic X] [--questions N]` | Quiz loop: evaluate → misconception → re-teach → retest (`quiz` is an alias) |
| `explain "<concept>"` | Detailed grounded explanation |
| `teach "<concept>"` | Simple grounded explanation |
| `review` | Quiz your weakest concept first |
| `search "<words>"` | Instant keyword cards, no LLM call |
| `chat` | Interactive session (same as bare `python -m mindloop`) |

### Practice

| Command | What it does |
|---|---|
| `flashcards [--topic X]` | Flip cards, grade 1 (forgot) / 2 (half) / 3 (knew) |
| `battle [--topic X]` | Timed drill with seal verdicts |
| `daily` | Morning ritual: one weak card + one new card |
| `drill [--topic X]` | Loop weakest concepts until the shelf is clear |
| `focus [--minutes N]` | Silent breath-circle timer |

### Knowledge

| Command | What it does |
|---|---|
| `ingest <path>` | Index PDF / TXT / MD / SRT / DOCX, incremental by hash |
| `import <path>` | Same as `ingest`, reads like a library stamp |
| `status` | Docs, chunks, model, recent mastery |
| `sources` / `docs` | Indexed files (table / with on-disk paths) |
| `remove <name>` | Delete a doc's chunks (files on disk untouched) |
| `export [--format json\|md\|anki] [--out file]` | Dump mastery + history |
| `watch <folder>` | Auto-index every 3s (Ctrl+C to stop) |

### System & Journal

| Command | What it does |
|---|---|
| `init` | Create `~/.mindloop` + default config |
| `doctor` | Setup checks with exact fixes |
| `progress` / `mastery` | Mastery summary / detail with enso rings |
| `dashboard [--live]` | One-screen alcove: library, mastery, heatmap, next step |
| `stats` / `streak` / `history` | Shelf overview / day streak / recent attempts |
| `config [--show\|--set k=v\|--wizard]` | Tune settings without hand-editing JSON |
| `journal` | Append today to your paper diary (`~/.mindloop/journal.md`) |
| `completion [--shell bash\|zsh\|pwsh]` | Shell completion snippet |
| `gui [--port N]` | Browser GUI (auto-opens your browser) |
| `--offline` | Force local-only, e.g. `python -m mindloop --offline ask "..."` |
| `--no-animation` / `--cinema-fast` | Calm the boot cinema down |

---

## 🔬 How grounding works

```
python -m mindloop <command>      <- thin CLI (Typer + Rich), formatting only
         |
MindloopEngine                     <- all logic, returns objects, no print/input
  ingest ............ parsers + chunking + sha256 incremental
  store ............. SQLite: documents, chunks, mastery, attempts
  retrieve .......... TF-IDF + cosine, offline, no model download
  providers ......... OllamaLLM (llama3.2:3b) + FakeLLM for tests
  ask / search / start_test / submit_answer / reteach / retest / progress
```

Grounding is enforced by code, not hope: relevance-threshold check before any LLM call, context-only prompt, citations attached from chunk metadata, verbatim quotes sliced by code, refusal when evidence is thin. If Ollama is missing, `ask` falls back to extractive quoting so the demo never breaks.

---

## 🌙 Offline mode

After setup, everything works with the internet off. `--offline` forces the deterministic path and skips Ollama checks; `doctor` reports offline status.

## ⚙️ Configuration

Home: `~/.mindloop` (override with `MINDLOOP_HOME`, used by tests). Files: `config.json`, `mindloop.db`, `journal.md`, `history`, `knowledge/`, `logs/`.

Defaults: `chunk_size 800` · `retrieval_count 4` · `relevance_threshold 0.12` · 2 correct in a row to master · max 3 re-teaches before `STRUGGLING`. Tune via `config --wizard`.

---

## 🧪 Development / testing

```powershell
python -m pytest -q
```

46 tests, all offline and deterministic (`FakeLLM` + isolated temp `MINDLOOP_HOME`). Real-Ollama checks are manual via `doctor`.

---

## 🩹 Troubleshooting

<details>
<summary>Click to expand</summary>

- `Knowledge base is empty` → run `ingest` first.
- `No supported files` → only PDF / TXT / MD / SRT / DOCX are indexed; others ignored.
- `scanned PDF, no extractable text` → use a text-based PDF (no OCR in this version).
- `Path not found ... examples/sample-study-folder` → you're in the wrong folder; `cd` to the folder with `pyproject.toml` first.
- `Missing folder to index / Missing question` → the command needs an argument; the error panel shows the exact command to copy.
- `Ollama is not running` → answers still work (quotes); install Ollama + pull the model for smoother phrasing.
- `mindloop not recognized` → use `python -m mindloop ...`.
- Privacy: `remove` deletes indexed chunks; original files are never touched or uploaded.

</details>

---

## 📄 License

MIT — study well.

<div align="center">

**mindloop 心 — learn until you can't get it wrong.**

</div>
