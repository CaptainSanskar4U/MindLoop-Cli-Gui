# MINDLOOP — MASTER PRD
## Local-First Adaptive Learning Engine + CLI

You are a senior software architect, AI/RAG engineer, Python engineer, CLI/UX designer, and product engineer.

Your job is to build MINDLOOP as a real, LOCAL-FIRST learning system with a production-quality structure that is also demo-reliable for a live hackathon presentation.

Do not treat this as a demo chatbot. Do not treat it as a throwaway script either.

MINDLOOP is an adaptive learning engine that takes a user's own study material, retrieves grounded evidence from that material, answers questions with citations, tests the learner's understanding, detects misconceptions, re-teaches the weak concept, and retests until mastery.

The core philosophy is:

    FIND THE ANSWER
    ↓
    UNDERSTAND THE ANSWER
    ↓
    PROVE YOU UNDERSTAND IT
    ↓
    DETECT MISUNDERSTANDING
    ↓
    RE-TEACH
    ↓
    RETEST
    ↓
    MASTER

The final system must have:

1. A reusable MINDLOOP CORE ENGINE
2. A powerful CLI built on top of that engine
3. A clean architecture that can later support a GUI without rewriting the core

--------------------------------------------------
# 0. CONTEXT, USER, AND PRIORITIES
--------------------------------------------------

## Context

MINDLOOP is being built for a hackathon whose problem statement is:

    "Build a RAG-based student study assistant where a student can upload
     study material (notes, PDF, or a DSA topic writeup) and ask questions
     about it. Answers must be grounded strictly in that content, not in
     generic AI guesses or hallucinations."

Grounded answers with citations and refusal to guess are therefore the FIRST thing that must work perfectly. The adaptive learning loop is the differentiator on top of it.

## About the person you are working with

The user is a BEGINNER who has never built a CLI or a software project before.

Therefore:

- explain what you are doing in simple language
- never assume they know terminal, Python packaging, or virtual environment commands
- give exact, copy-pasteable commands for every setup step
- explain errors in plain words and say exactly what to do next
- do not use jargon without a one-line explanation

## Target environment

- Works on Windows, macOS, and Linux (use `pathlib`, avoid shell-specific commands)
- Python 3.10+
- Normal student laptop: 8 GB RAM, no GPU
- Internet is needed ONCE for setup (installing dependencies, downloading models). After setup, every study workflow must work with the internet disconnected.

## Build priority (IMPORTANT)

Build in this order. Do NOT start a lower tier until the tier above works end-to-end.

TIER 1 — MUST WORK PERFECTLY (the demo):
- ingest (PDF, TXT, Markdown, SRT transcripts; folders; incremental)
- ask (grounded answer + citations + refusal when evidence is missing)
- test → evaluate → misconception detection → adaptive re-teach → retest → mastery
- progress (mastery view)
- doctor (checks the setup)
- offline operation
- tests + README

TIER 2 — SHOULD HAVE:
- chat (interactive mode)
- docs, status, sources, remove
- DOCX support
- watch (auto-index new files in a folder)
- mastery detail, review, explain, teach

TIER 3 — STRETCH (only after Tiers 1 and 2 work; design the interfaces for them, but do not build fully until then):
- hybrid keyword + semantic retrieval, reranking
- remote/optional providers
- OCR for scanned PDFs
- async operations
- GUI

A small, working Tier 1 beats a large, half-working everything. If time or complexity forces a choice, cut from the bottom.

## Reference demo scenario (the acceptance test)

The whole product must be able to run this exact scenario reliably, with the internet OFF:

1. `mindloop ingest ./examples/sample-study-folder`
2. `mindloop ask "Can Dijkstra's algorithm handle negative edge weights?"`
   → grounded answer with file and page citation
3. `mindloop ask "Who won the 2018 football world cup?"`
   → clear refusal: not in your material
4. `mindloop test`
   → learner deliberately gives a WRONG answer (e.g. "Yes, Dijkstra handles negative weights")
   → MINDLOOP names the misconception (e.g. confusing Dijkstra with Bellman-Ford)
   → re-teaches with a DIFFERENT strategy
   → asks a NEW question on the same concept
   → learner answers correctly
   → `mindloop progress` shows the concept moving toward MASTERED

Create the sample study folder (see Section 6) so this scenario works out of the box.

--------------------------------------------------
# 1. PRODUCT VISION
--------------------------------------------------

MINDLOOP should solve a problem that normal AI study tools do not:

A student can find an answer, copy it, and even explain it without actually understanding it.

Most AI tools stop after generating an answer.

MINDLOOP continues until the learner demonstrates understanding.

Core product statement:

"Learning isn't finished when you get the answer.
It's finished when you can't get it wrong anymore."

MINDLOOP must therefore be:

- Grounded
- Local-first
- Private
- Offline-capable
- Adaptive
- Evidence-based
- CLI-friendly
- Extensible
- Testable

--------------------------------------------------
# 2. NON-NEGOTIABLE PRINCIPLES
--------------------------------------------------

## Grounded

MINDLOOP must answer questions using the user's indexed study material.

Every factual answer generated from indexed material must include:

- source file
- page number when available
- relevant section/chunk
- confidence/relevance information where appropriate

If the information does not exist in the user's material:

DO NOT hallucinate.

Clearly say:

"I couldn't find this in your indexed material."

Do not silently use unrelated external knowledge.

## How grounding is enforced (engineering rules)

Grounding must be enforced by the pipeline, not by hoping the model behaves:

1. Evidence check BEFORE generation: if the best retrieved chunks fall below a configurable relevance threshold, refuse immediately WITHOUT calling the LLM.
2. Context-only prompting: the LLM receives only the retrieved chunks and is instructed to answer only from them.
3. Citations are attached BY CODE from the metadata of the chunks actually used. The LLM must never be trusted to write file names or page numbers. A citation that does not map to a retrieved chunk must never be displayed.
4. If the model's answer says the information is unavailable, or the answer cannot be supported by the chunks, show the refusal/partial-coverage message instead.

## Local-first

User study material should remain local whenever possible.

The system must be designed so that:

- files are processed locally
- indexing is local
- retrieval is local
- embeddings can run locally
- LLM inference can run locally when a supported local model is available
- no internet is required for normal study workflows

External APIs may be supported as OPTIONAL providers, but they must never be silently required.

Create a provider abstraction such as:

LLMProvider
EmbeddingProvider
VectorStore
DocumentParser

so local and remote implementations can be swapped.

--------------------------------------------------
# 3. CORE ARCHITECTURE
--------------------------------------------------

Design MINDLOOP as a reusable engine.

Recommended conceptual architecture:

                    ┌─────────────────────┐
                    │      MINDLOOP       │
                    │       ENGINE        │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
     INGESTION             RETRIEVAL          LEARNING
          │                    │                    │
   PDF / DOCX / TXT       Semantic Search       Testing
   Markdown / SRT         Hybrid Search         Evaluation
          │                    │                    │
      Chunking             Reranking           Misconception
      Metadata             Citations             Detection
      Embeddings                                Re-teaching
                                                    │
                                                 Retest
                                                    │
                                                 Mastery

The CLI must be a thin interface over this engine.

DO NOT put core business logic directly inside CLI commands.

Future GUI must be able to import and use the same engine.

IMPORTANT for GUI-readiness:

- Engine functions must RETURN structured objects (dataclasses / pydantic models such as `Answer`, `Citation`, `Question`, `Evaluation`, `MasteryState`), never print or format text.
- The CLI is the only layer that formats output (using Rich).
- The engine must not depend on the CLI, on `input()`, or on `print()`.

--------------------------------------------------
# 4. DEFAULT TECHNOLOGY CHOICES
--------------------------------------------------

Make these decisions by default (do not ask). If an existing repository already uses something else, reuse it and document the decision.

- Language: Python 3.10+
- Packaging: `pyproject.toml`, installable with `pip install -e .`, with a `mindloop` console entry point
- CLI: Typer + Rich
- Local LLM: Ollama, default model `llama3.2:3b` (alternative: `qwen2.5:3b`), model name configurable
- Local embeddings: Ollama embedding model (default `nomic-embed-text`) so that only ONE local runtime is needed; keep the EmbeddingProvider abstraction so `sentence-transformers` can be swapped in
- PDF parsing: PyMuPDF (page numbers preserved)
- Vector store: ChromaDB (persistent, local), behind the VectorStore abstraction
- Metadata / manifest / sessions / mastery: SQLite (standard library)
- Validation of structured LLM output: pydantic
- Testing: pytest

Keep dependencies minimal. Do not add a dependency without a clear reason.

## Small local model reliability (IMPORTANT)

Small local models (3B parameters) are less reliable than cloud models. The design must expect this:

- Every structured output (generated questions, evaluations, misconception diagnosis) must be requested as JSON matching a defined schema, and validated with pydantic.
- If the JSON is invalid: retry once with a stricter prompt, then fall back gracefully with a clear message. Never crash on malformed model output.
- Keep prompts short and specific. Retrieve a small number of chunks (default 4–5).
- Use low temperature for answering and evaluating.
- Local generation can be slow: show a spinner or streamed output, set sensible timeouts, and show a clear message if the model is not responding.
- Cache generated questions so tests start quickly.

--------------------------------------------------
# 5. PROJECT STRUCTURE
--------------------------------------------------

Use a clean structure similar to:

mindloop/
│
├── core/
│   ├── ingestion/
│   ├── parsing/
│   ├── chunking/
│   ├── embeddings/
│   ├── retrieval/
│   ├── reranking/
│   ├── generation/
│   ├── citations/
│   ├── testing/
│   ├── misconceptions/
│   ├── teaching/
│   ├── mastery/
│   ├── sessions/
│   └── models/
│
├── cli/
│   ├── commands/
│   ├── formatting/
│   └── interactive/
│
├── providers/
│   ├── llm/
│   ├── embeddings/
│   └── storage/
│
├── tests/
│
├── examples/
│   └── sample-study-folder/
│
├── docs/
│
├── pyproject.toml
└── README.md

Adapt this structure to the existing repository if one already exists. If the repository is empty, start fresh and skip the inspection steps that do not apply.

IMPORTANT:

Before writing code:

1. Inspect the entire repository.
2. Identify existing architecture.
3. Identify existing dependencies.
4. Identify what is already implemented.
5. Reuse working code where appropriate.
6. Do not rewrite functioning components unnecessarily.
7. Explain your implementation plan before making large architectural changes.

--------------------------------------------------
# 6. DOCUMENT INGESTION
--------------------------------------------------

MINDLOOP must support studying from:

- PDF
- TXT
- Markdown
- SRT (lecture transcripts; ignore timestamps, keep the text and, where useful, the timestamp range as location metadata)
- DOCX (Tier 2)
- folders containing multiple supported files

Design ingestion as a pipeline:

FILE
↓
PARSER
↓
TEXT EXTRACTION
↓
STRUCTURE DETECTION
↓
CHUNKING
↓
METADATA
↓
EMBEDDING
↓
INDEX

Each chunk should preserve metadata such as:

- document ID
- filename
- path
- page number (or timestamp range for transcripts)
- section
- chunk ID
- source text
- embedding
- creation timestamp

Never lose source information during chunking.

Citation accuracy is a core feature. A chunk must never span pages in a way that makes its page citation ambiguous; if a chunk crosses pages, record the page range.

## Sample study folder

Create `examples/sample-study-folder/` containing small, realistic study material for the demo scenario:

- a multi-page PDF (at least 3 pages) with a DSA writeup covering Dijkstra's algorithm and Bellman-Ford, including the fact that Dijkstra does not support negative edge weights while Bellman-Ford does
- a Markdown notes file on another topic (e.g. time complexity or sorting)

Generate the sample PDF with a small script committed to the repo (for example using `reportlab` as a dev-only dependency) so it is reproducible. Do not use copyrighted material.

--------------------------------------------------
# 7. STUDY FOLDERS
--------------------------------------------------

The user should be able to point MINDLOOP at an entire folder.

Example:

mindloop ingest ./my-study-folder

MINDLOOP should:

- recursively discover supported files
- ignore unsupported files
- avoid unnecessary duplicate indexing
- detect changed files
- update only changed documents where possible
- maintain an index manifest (path, content hash, indexed time, chunk count, status)
- handle a file that disappeared from the folder (mark or remove its chunks)

Example:

study-folder/
├── physics/
│   ├── mechanics.pdf
│   └── notes.md
├── mathematics/
│   └── calculus.pdf
└── chemistry/
    └── organic.pdf

The system should preserve folder/file relationships.

Tier 2: `mindloop watch <folder>` monitors a folder and indexes new or changed files automatically (a simple polling loop is acceptable).

--------------------------------------------------
# 8. KNOWLEDGE BASE
--------------------------------------------------

Create a persistent local knowledge base.

It should support:

- document registry
- chunk storage
- embeddings
- metadata
- indexing status
- document hashes
- retrieval

Use a sensible local database/vector architecture (see Section 4 defaults).

The architecture should not require a cloud database.

--------------------------------------------------
# 9. RETRIEVAL
--------------------------------------------------

When a user asks:

"What is Newton's second law?"

MINDLOOP should:

1. Understand the query.
2. Search the user's indexed material.
3. Retrieve relevant chunks.
4. Optionally perform hybrid keyword + semantic retrieval (Tier 3).
5. Rerank candidates when useful (Tier 3).
6. Determine whether sufficient evidence exists.
7. Generate an answer ONLY from retrieved evidence.
8. Attach citations.

Conceptually:

QUERY
↓
QUERY ANALYSIS
↓
RETRIEVAL
↓
RERANK
↓
EVIDENCE CHECK
↓
ANSWER
↓
CITATIONS

--------------------------------------------------
# 10. ANTI-HALLUCINATION BEHAVIOR
--------------------------------------------------

This is critical.

Never fabricate:

- facts
- citations
- page numbers
- document names
- quotes
- evidence

If evidence is insufficient:

"I couldn't find enough evidence in your material to answer this."

If the material partially answers the question:

"Your material covers X, but I couldn't find information about Y."

Never pretend the answer exists.

Quotes shown as evidence must be verbatim excerpts copied from the retrieved chunk text by code, never regenerated by the LLM.

--------------------------------------------------
# 11. ASK MODE
--------------------------------------------------

CLI command:

mindloop ask "What is photosynthesis?"

Expected conceptual output:

┌──────────────────────────────────────────────┐
│ ANSWER                                       │
└──────────────────────────────────────────────┘

Photosynthesis is ...

SOURCE
📄 biology.pdf — Page 42

EVIDENCE
...

The exact UI can be designed professionally, but it must remain readable.

Support:

mindloop ask "question"

and interactive mode (Tier 2):

mindloop chat

Interactive mode should allow:

> ask a question
> show sources
> explain simpler
> quiz me
> exit

--------------------------------------------------
# 12. TEST MODE
--------------------------------------------------

The system must not stop after answering.

Command:

mindloop test

Useful options: `--topic "<concept>"`, `--questions N`, `--path <file-or-folder>` to limit the material being tested.

`mindloop quiz` is an alias of `mindloop test`.

The engine should generate questions from the user's indexed material.

Question types can include:

- conceptual
- multiple choice
- short answer
- explain in your own words
- application
- comparison
- reasoning

Questions must be grounded in the study material.

Every generated question must keep a reference to the source chunk(s) it was generated from, plus the key concepts an answer must contain. Evaluation, misconception detection, and re-teaching must all use that same source text, so the system never "corrects" a student using outside knowledge.

Example:

Question:
Why does increasing temperature affect reaction rate?

The learner answers.

MINDLOOP evaluates the response.

IMPORTANT:

Do not judge only keyword matching.

Evaluation should consider:

- correctness
- required concepts
- misconceptions
- missing reasoning
- contradiction
- partial understanding

Suggested approach: give the LLM the source text, the question, the required concepts, and the learner's answer, and require a validated JSON verdict (correct / partial / incorrect, missing concepts, suspected misconception, short explanation). Multiple-choice questions can be graded deterministically.

--------------------------------------------------
# 13. MISCONCEPTION DETECTION
--------------------------------------------------

This is one of the most important MINDLOOP features.

When a learner answers incorrectly, do NOT simply show the correct answer.

Instead determine:

WHAT DID THE LEARNER MISUNDERSTAND?

Example:

Expected concept:
Higher temperature increases molecular kinetic energy, causing more effective collisions.

Student:
"Higher temperature makes molecules larger, so they collide more."

Detected misconception:

"The learner appears to confuse molecular size with molecular kinetic energy."

Store the misconception in the learning session.

The misconception statement must be phrased tentatively ("appears to", "may be confusing") and must be tied to the source text. If no clear misconception can be identified (for example the answer is only incomplete or off-topic), say so honestly instead of inventing one.

--------------------------------------------------
# 14. ADAPTIVE RE-TEACHING
--------------------------------------------------

After detecting a misconception:

DO NOT repeat the same explanation.

Change the teaching strategy.

Possible strategies:

- simpler explanation
- analogy
- step-by-step explanation
- counterexample
- visual mental model
- comparison
- misconception correction
- worked example

Example:

Initial explanation:
Technical textbook explanation.

After failure:

"Think of the molecules like runners..."

The system should adapt based on the detected weakness.

Rules:

- Record which strategy was used for each concept in the session.
- Never reuse a strategy already tried for the same concept; if the learner fails again, move to the next strategy.
- Re-teaching must still be grounded in the source chunks. Analogies are allowed as teaching aids but must be clearly tied to, and consistent with, the material, and the source citation must still be shown.

--------------------------------------------------
# 15. RETEST
--------------------------------------------------

After re-teaching:

Do not immediately ask the exact same question.

Generate a NEW question testing the same underlying concept.

Example:

Question 1:
Explain why temperature affects reaction rate.

After misconception:

Question 2:
Two reactions use the same reactants. One is heated. What changes at the molecular level?

The goal is to determine whether the learner understood the concept rather than memorized the answer.

Check that the new question is meaningfully different from earlier questions on the same concept.

--------------------------------------------------
# 16. MASTERY
--------------------------------------------------

Create a mastery model.

A concept should not be marked "mastered" simply because the learner answered one question correctly.

Track:

- attempts
- correct answers
- incorrect answers
- misconception history
- difficulty
- retest performance
- confidence
- recent performance

Conceptual state:

UNKNOWN
↓
INTRODUCED
↓
PRACTICING
↓
STRUGGLING
↓
RE-TAUGHT
↓
RETESTING
↓
MASTERED

Mastery thresholds should be configurable.

Sensible default: a concept becomes MASTERED after the learner answers at least 2 different questions on it correctly in a row, and if the concept was ever failed, at least one of those correct answers must come AFTER re-teaching and be a new question.

Persist mastery and session data in the local SQLite database so progress survives closing the terminal and the learner can resume where they stopped.

--------------------------------------------------
# 17. LEARNING LOOP
--------------------------------------------------

The main engine workflow:

INGEST
↓
INDEX
↓
ASK
↓
ANSWER
↓
TEST
↓
EVALUATE
↓
IF CORRECT
    increase mastery
    ↓
    next concept / harder question

IF WRONG
    detect misconception
    ↓
    re-teach
    ↓
    retest
    ↓
    evaluate again

Repeat until mastery or session termination.

Add a limit on the number of re-teach attempts per concept (configurable, default 3). If the limit is reached, mark the concept as STRUGGLING, show the relevant source pages to re-read, and move on. Never loop forever.

This loop is the defining feature of MINDLOOP.

--------------------------------------------------
# 18. CLI DESIGN
--------------------------------------------------

The CLI should feel like a real developer/student tool.

Tier 1 commands:

mindloop init
mindloop ingest <path>
mindloop ask "<question>"
mindloop test          (alias: quiz)
mindloop progress
mindloop doctor

Tier 2 commands:

mindloop chat
mindloop status
mindloop docs
mindloop sources
mindloop remove <document>
mindloop mastery
mindloop review        (re-practice concepts marked STRUGGLING or due for review)
mindloop watch <folder>
mindloop teach "<concept>"
mindloop explain "<concept>"

Optional, only if they add clear value: mindloop retest, mindloop session

Do not create overlapping commands that do the same thing under different names, except the documented `quiz` alias.

Use intuitive command names.

Provide:

--help
--version

for every major command.

--------------------------------------------------
# 19. EXAMPLE CLI EXPERIENCE
--------------------------------------------------

Example:

$ mindloop ingest ./biology

Indexing study material...

✓ biology.pdf
✓ chapter-2-notes.md
✓ genetics.pdf

42 documents/pages processed
1,284 chunks indexed

Knowledge base ready.

Then:

$ mindloop ask "What is DNA replication?"

MINDLOOP

DNA replication is ...

Sources:
  biology.pdf — p. 73
  genetics.pdf — p. 18

Grounded in your material ✓

Then:

$ mindloop test

MINDLOOP TEST

Question 1/5

Why does DNA replication need a template strand?

> [user answer]

Evaluating...

Your answer is partially correct.

What you're missing:
You identified the copying process, but missed why complementary
base pairing is necessary.

Let's fix that.

RE-TEACH

...

RETEST

New question:
...

This should feel polished and useful, not like raw Python output.

--------------------------------------------------
# 20. GUI + CLI ARCHITECTURE
--------------------------------------------------

The CLI is NOT the product's core.

The engine is.

The architecture must support:

CLI
 │
 ▼
MINDLOOP ENGINE
 │
 ├── ingestion
 ├── retrieval
 ├── generation
 ├── testing
 ├── misconception detection
 ├── teaching
 └── mastery

Later:

GUI (planned: Streamlit)
 │
 ▼
MINDLOOP ENGINE

Therefore:

NEVER implement important learning logic only inside CLI commands.

Everything reusable belongs in the engine.

The engine should expose a small, clear public API (for example a `MindloopEngine` class with methods such as `ingest()`, `ask()`, `start_test()`, `submit_answer()`, `get_progress()`) so that a GUI can call it directly with no changes to the core. Interactive flows (like tests) must be step-based: the engine returns the next question or evaluation and waits to be called again, rather than blocking on `input()`.

--------------------------------------------------
# 21. PROVIDER SYSTEM
--------------------------------------------------

Create abstractions for:

LLM

Embedding

Vector database/storage

Document parser

This should allow:

Local LLM
Remote LLM

to be swapped without rewriting the learning engine.

Example conceptual configuration:

provider:
    llm: local
    embeddings: local
    storage: local

Optional remote configuration may exist (Tier 3).

But local mode must remain a first-class experience.

Also implement `FakeLLMProvider` and `FakeEmbeddingProvider` (deterministic, no model needed). These are used by the automated tests so the whole test suite runs quickly, offline, and without Ollama installed.

--------------------------------------------------
# 22. OFFLINE MODE
--------------------------------------------------

Provide:

mindloop --offline

or configuration equivalent.

In offline mode:

- no internet requests
- local documents only
- local retrieval
- local model/provider

If a required local model is missing:

Give a clear setup message with exact commands (for example: install Ollama, then run `ollama pull llama3.2:3b` and `ollama pull nomic-embed-text`).

Never silently connect to the internet.

In offline mode, any remote provider must be refused with a clear message.

`mindloop doctor` must check and report: Python version, Ollama installed and running, required models downloaded, knowledge base location writable, indexed documents present, and whether offline mode is active. Every failed check must include the exact fix.

--------------------------------------------------
# 23. PRIVACY
--------------------------------------------------

Study documents may contain private information.

Therefore:

- do not upload files by default
- do not log document contents unnecessarily
- avoid storing sensitive generated text unnecessarily
- provide clear local storage locations
- provide commands to remove indexed documents
- make network behavior explicit

--------------------------------------------------
# 24. CONFIGURATION
--------------------------------------------------

Provide a simple configuration system.

Example:

~/.mindloop/

config
knowledge/
sessions/
models/
logs/

Configuration should support:

- model
- embedding model
- storage path
- chunk size
- retrieval count
- relevance threshold
- mastery threshold
- max re-teach attempts
- offline mode
- output style

Use sensible defaults.

The user should be able to start quickly without configuring 20 things.

Allow the storage location to be overridden with a `MINDLOOP_HOME` environment variable (useful for tests and for keeping separate knowledge bases per subject).

--------------------------------------------------
# 25. ERROR HANDLING
--------------------------------------------------

Errors must be human-readable.

Bad:

Traceback...
ValueError...
ConnectionError...

Better:

MINDLOOP couldn't index `biology.pdf`.

Reason:
The PDF contains scanned pages without extractable text.

Try:
Use a text-based version of the PDF. (OCR support is not enabled in this version.)

Errors should suggest actionable solutions. Only suggest commands or flags that actually exist in the current version (for example, suggest `--ocr` only if OCR is implemented).

Common cases that must be handled with clear messages: Ollama not running, model not downloaded, empty or scanned PDF, unsupported file type, empty knowledge base ("Run `mindloop ingest <folder>` first"), corrupted file, model timeout, invalid model output.

--------------------------------------------------
# 26. PERFORMANCE
--------------------------------------------------

The system should be designed for:

- incremental indexing
- caching
- batch embeddings
- efficient retrieval
- avoiding repeated model calls
- asynchronous operations where appropriate (Tier 3)

Do not sacrifice reliability for premature optimization.

Target: on an 8 GB laptop with no GPU, `ask` should answer in a reasonable time with visible progress. Measure and report actual timings on the development machine.

--------------------------------------------------
# 27. TESTING
--------------------------------------------------

Create serious tests.

Unit and integration tests must use the Fake providers so they run offline and deterministically. Tests that need a real Ollama model should be a separate, clearly marked group (for example `@pytest.mark.integration`) that is skipped automatically when Ollama is not available.

At minimum:

### Ingestion tests
- PDF extraction
- TXT extraction
- Markdown extraction
- SRT extraction
- DOCX extraction (Tier 2)
- folder ingestion
- incremental re-ingestion (unchanged file is skipped, changed file is updated)

### Retrieval tests
- relevant retrieval
- irrelevant retrieval
- citation metadata
- missing evidence

### Grounding tests
- answer from evidence
- refuse unsupported answer (LLM must not be called when evidence is weak)
- citation accuracy (cited page matches the page the text came from)

### Learning tests
- correct answer evaluation
- incorrect answer evaluation
- misconception detection
- malformed model output handled gracefully
- re-teaching uses a different strategy each time
- retesting produces a new question
- mastery progression
- re-teach attempt limit

### CLI tests
Test major commands programmatically (for example with Typer's `CliRunner`).

--------------------------------------------------
# 28. EVALUATION / QUALITY GATES
--------------------------------------------------

Before declaring the implementation complete, demonstrate:

1. Ingest a real PDF.
2. Ask a question.
3. Receive a grounded answer.
4. Verify citation points to the correct page.
5. Ask something absent from the document.
6. Verify MINDLOOP refuses to hallucinate.
7. Start a test.
8. Give an incorrect answer.
9. Detect the misconception.
10. Receive an adapted explanation.
11. Receive a new retest question.
12. Answer correctly.
13. Show mastery progression.
14. Run everything without internet where local providers are available.
15. Run `mindloop doctor` and show it correctly reports a healthy setup, and a clear fix when something is missing.
16. Run the full reference demo scenario (Section 0) end to end, three times in a row, without failure.

Show the real commands and their real output. Do not claim a gate passed without running it.

--------------------------------------------------
# 29. DOCUMENTATION
--------------------------------------------------

Create a professional README.

It must explain:

- What MINDLOOP is
- Why it exists
- Architecture
- Installation (including installing Python and Ollama and pulling the models, step by step, for beginners)
- Quick start
- Ingesting documents
- Asking questions
- Testing
- Adaptive learning
- Offline mode
- Configuration
- CLI commands
- Provider configuration
- Development
- Testing
- Troubleshooting

Include examples.

Also create `docs/DEMO.md`: a short, exact, step-by-step demo script for the reference scenario (commands to type, the wrong answer to give, and what output to expect), so the demo can be rehearsed.

--------------------------------------------------
# 30. UX / DESIGN LANGUAGE
--------------------------------------------------

MINDLOOP should feel:

- intelligent
- calm
- focused
- academic
- premium
- private
- developer-friendly

Avoid:

- excessive emojis
- noisy terminal output
- fake AI language
- unnecessary animations
- verbose logs
- marketing fluff

Use clean terminal hierarchy.

Important information should be visually obvious.

Output must remain readable on both dark and light terminal themes and on Windows terminals.

--------------------------------------------------
# 31. IMPORTANT ENGINEERING RULES
--------------------------------------------------

DO NOT:

- fabricate functionality
- pretend a model is local when it is remote
- fabricate citations
- silently access the internet
- hardcode a specific user's documents
- put all logic into one Python file
- tightly couple CLI and engine
- add unnecessary dependencies
- rewrite working components without reason
- claim a feature works without testing it
- start Tier 2 or Tier 3 work before Tier 1 works end to end

DO:

- inspect the repository first
- create a plan
- implement incrementally
- test every major component
- preserve source metadata
- keep the architecture modular
- document important decisions
- make failures understandable
- prioritize a working end-to-end vertical slice

--------------------------------------------------
# 32. IMPLEMENTATION STRATEGY
--------------------------------------------------

Do NOT attempt to build everything blindly at once.

Work in phases.

PHASE 1
Repository inspection + architecture + project skeleton
(includes: pyproject and `mindloop` entry point, config system, provider interfaces, Ollama providers, Fake providers, `mindloop --version` and `mindloop doctor` working)

PHASE 2
Document ingestion

PHASE 3
Local knowledge base

PHASE 4
Retrieval + citations

PHASE 5
Grounded ASK   ← STOP HERE and let the user try it (first working vertical slice)

PHASE 6
TEST engine

PHASE 7
Misconception detection

PHASE 8
Adaptive re-teaching

PHASE 9
Retesting + mastery   ← STOP HERE and let the user try the full loop

PHASE 10
CLI polish + Tier 2 commands

PHASE 11
Offline verification, `doctor` completion, remove/privacy commands

PHASE 12
Final testing + documentation + demo script

Tests are written in every phase, not only at the end.

At the end of every phase:

- run tests
- fix failures
- verify behavior
- summarize what changed in simple language
- give the exact commands the user can run to see the new feature working

Continue automatically to the next phase unless a phase fails or needs something from the user (for example installing Ollama or downloading a model). Always stop at the end of Phase 5 and Phase 9 so the user can try the product.

--------------------------------------------------
# 33. FIRST ACTION
--------------------------------------------------

Before writing implementation code:

INSPECT THE EXISTING PROJECT.

Determine:

- language
- framework
- current structure
- existing dependencies
- existing RAG code
- existing CLI code
- existing database/storage
- existing models
- existing tests
- what can be reused

Then provide:

1. Current architecture summary
2. Problems/gaps
3. Proposed architecture
4. File changes
5. Dependencies required
6. Implementation phases

Then begin implementation.

Do not ask unnecessary questions.

If a reasonable engineering decision can be made from the existing repository, make it and document the decision.

--------------------------------------------------
# 34. DEFINITION OF DONE
--------------------------------------------------

MINDLOOP is considered complete for the first production-ready milestone when a user can run:

    mindloop ingest ./study-material

then:

    mindloop ask "Explain this concept."

and receive a grounded answer with source citation.

Then:

    mindloop test

and experience:

    QUESTION
       ↓
    ANSWER
       ↓
    EVALUATE
       ↓
    MISCONCEPTION
       ↓
    RE-TEACH
       ↓
    RETEST
       ↓
    MASTERY

The same underlying engine must power every step, and every step must work with the internet disconnected.

The final result must feel like a real product, not a collection of scripts.

MINDLOOP's defining promise:

    "It doesn't stop when it gives you the answer.
     It stops when you understand it."