# DEMO script (rehearse exactly, internet OFF allowed)

Takes ~3 minutes. Commands use `python -m mindloop` (same as `mindloop`).
Run everything from the Rag folder (the one with pyproject.toml).
Two ways to run: interactive `python -m mindloop` (ask directly, /quiz to test),
or one-shot commands below (for scripts). Both use the same engine.
The session opens with the MINDLOOP wordmark (a ~3s cinematic ignition plays
once on a real terminal — press any key to skip; `--cinema-fast` for the
1.5s cut, `--no-animation` to skip it entirely).

## 0. Setup (once)

```powershell
cd C:\Users\Captain\Desktop\Rag
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m mindloop.sample_data
python -m mindloop init
```

## 1. Ingest

```powershell
python -m mindloop ingest ./examples/sample-study-folder
```

Expect: `OK dijkstra-notes.pdf`, `OK complexity.md`, `2 documents`.

## 2. Grounded answer

```powershell
python -m mindloop ask "Can Dijkstra's algorithm handle negative edge weights?"
```

Expect: mentions Dijkstra does NOT support negatives, Bellman-Ford DOES. Then `Sources:` with `dijkstra-notes.pdf - p.2` plus a verbatim quote.

## 3. Refusal

```powershell
python -m mindloop ask "Who won the 2018 football world cup?"
```

Expect: `I couldn't find this in your indexed material.`

## 4. Test loop (the differentiator)

```powershell
python -m mindloop test --topic "dijkstra negative weights" --questions 1
```

- Question shows: `Can Dijkstra's algorithm handle negative edge weights?`
- Type (deliberately wrong): `Yes, Dijkstra handles negative weights`
- Expect: `Verdict: incorrect` + `Possible misconception:` mentioning confusion with Bellman-Ford.
- Expect: `Re-teach (simpler|analogy|...)` with explanation + `(Source: dijkstra-notes.pdf p.2)`.
- New `Retest:` question, different text, same concept.
- Type (correct): `No, Dijkstra cannot handle negative weights, Bellman-Ford can`
- Expect: `Retest: correct`.

## 5. Mastery

```powershell
python -m mindloop progress
```

Expect: row `dijkstra-negative-weights` with attempts going up, streak 1. Answer one more new question correctly to reach `MASTERED` (needs 2 correct in a row after a fail).

## 6. Health

```powershell
python -m mindloop doctor
```

Expect: PASS Python, PASS writable, PASS indexed (2 docs). Ollama FAIL is OK — answers still work via quotes; fix line tells you `ollama pull llama3.2:3b`.

## If something goes wrong live

- Empty KB → re-run step 1.
- Wrong question topic → use `--topic "dijkstra negative weights"` exactly.
- Ollama missing → say "running in extractive fallback, fully offline" — this is by design.
