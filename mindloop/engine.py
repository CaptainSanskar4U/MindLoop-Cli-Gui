"""MindloopEngine: ingest/ask/test loop. No print(), no input(). Returns objects."""
from __future__ import annotations
import json
import re
import time
import uuid
from pathlib import Path
from typing import Optional

from .models import Answer, Citation, RetrievedChunk, Question, Evaluation, MasteryState, IngestResult
from .config import load_config
from .store import connect, upsert_mastery, log_attempt
from . import ingest as ing
from . import retrieve as ret
from .providers import LLMProvider, OllamaLLM, FakeLLM

STRATEGIES = ["simpler", "analogy", "steps", "counterexample", "comparison"]

def make_llm(cfg: dict | None = None) -> LLMProvider:
    cfg = cfg or load_config()
    if cfg.get("offline"):
        return FakeLLM()
    oll = OllamaLLM(model=cfg.get("llm_model", "llama3.2:3b"),
                    host=cfg.get("ollama_host", "http://localhost:11434"),
                    timeout=cfg.get("llm_timeout", 60))
    ok, _ = oll.available()
    return oll if ok else FakeLLM()

def _cite(c: RetrievedChunk, maxlen: int = 220) -> Citation:
    q = re.sub(r"\s+", " ", c.text).strip()[:maxlen]
    return Citation(filename=c.filename, path=c.path, page=c.page, section=c.section, quote=q)

def _concept_for(text: str, section: str, filename: str) -> tuple[str, list[str]]:
    t = text.lower()
    if "dijkstra" in t and "negative" in t:
        return "dijkstra-negative-weights", ["Dijkstra requires non-negative weights", "Bellman-Ford handles negative weights"]
    if "dijkstra" in t:
        return "dijkstra-basics", ["Dijkstra finds shortest paths with non-negative weights"]
    if "bellman" in t:
        return "bellman-ford", ["Bellman-Ford relaxes edges repeatedly", "handles negative weights"]
    if "complexity" in t or "big-o" in t or "big o" in t:
        return "time-complexity", ["Big-O describes growth", "example complexities"]
    if "sort" in t:
        return "sorting", ["sorting concepts from material"]
    base = (section or Path(filename).stem).strip().lower() or "general"
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:40] or "general"
    # required concepts = first key sentence words
    sent = re.split(r"\.\s+", text.strip())
    req = [sent[0][:120]] if sent and sent[0] else [text[:120]]
    return base, req

class MindloopEngine:
    def __init__(self, llm: LLMProvider | None = None):
        self.cfg = load_config()
        self.llm = llm or make_llm(self.cfg)

    # ---- INGEST ----
    def ingest(self, path: str | Path) -> IngestResult:
        return ing.ingest_path(path)

    # ---- ASK (grounded) ----
    def ask(self, question: str) -> Answer:
        hits = ret.retrieve(question)
        if not hits:
            return Answer(
                text="I couldn't find this in your indexed material. Try ingesting the right folder first: mindloop ingest <folder>",
                refused=True, evidence_count=0,
            )
        cites = [_cite(h) for h in hits]
        context = "\n\n".join(f"[{h.filename} p.{h.page or '?'}] {h.text[:900]}" for h in hits)
        # Try LLM, fall back to extractive quoting
        text = ""
        if not isinstance(self.llm, FakeLLM):
            try:
                prompt = (
                    f"Context:\n{context}\n\nQuestion: {question}\n\n"
                    "Answer ONLY from the context above in 3-6 sentences. "
                    "If the context lacks the answer, reply exactly: NOT IN MATERIAL."
                )
                text = self.llm.generate(prompt, system="Answer only from provided context. Be short.")
                if "NOT IN MATERIAL" in text.upper():
                    return Answer(
                        text="I couldn't find this in your indexed material.",
                        citations=cites, refused=True, evidence_count=len(hits),
                    )
            except Exception:
                text = ""
        if not text:
            # Extractive fallback: quote best chunk sentences containing query words
            qwords = set(re.findall(r"[a-z]{3,}", question.lower()))
            best = hits[0]
            sents = re.split(r"(?<=[.!?])\s+", best.text)
            picked = [s for s in sents if qwords & set(re.findall(r"[a-z]{3,}", s.lower()))][:3]
            snippet = " ".join(picked) if picked else best.text[:500]
            text = f"Based on your material: {snippet.strip()}"
        return Answer(text=text.strip(), citations=cites, refused=False, evidence_count=len(hits))

    # ---- TEST ----
    def start_test(self, topic: str = "", n: int = 3) -> list[Question]:
        con = connect()
        try:
            if topic:
                rows = con.execute("SELECT * FROM chunks").fetchall()
            else:
                rows = con.execute("SELECT * FROM chunks ORDER BY rowid LIMIT 50").fetchall()
        finally:
            con.close()
        if not rows:
            raise RuntimeError("Knowledge base is empty. Run `mindloop ingest <folder>` first.")
        dicts = [dict(r) for r in rows]
        if topic:
            # rank by keyword overlap with topic
            tw = set(re.findall(r"[a-z]{3,}", topic.lower()))
            dicts.sort(key=lambda d: len(tw & set(re.findall(r"[a-z]{3,}", d["text"].lower()))), reverse=True)
        seen: set[str] = set()
        out: list[Question] = []
        for d in dicts:
            concept, req = _concept_for(d["text"], d.get("section") or "", d["filename"])
            if concept in seen:
                continue
            seen.add(concept)
            out.append(self._make_question(d, concept, req))
            if len(out) >= n:
                break
        # mark INTRODUCED
        con = connect()
        try:
            for q in out:
                row = con.execute("SELECT * FROM mastery WHERE concept=?", (q.concept,)).fetchone()
                if row is None:
                    upsert_mastery(con, q.concept, state="INTRODUCED")
            # ensure strategies rows
            for q in out:
                con.execute("INSERT OR IGNORE INTO strategies(concept,used) VALUES(?,?)", (q.concept, ""))
            con.commit()
        finally:
            con.close()
        return out

    def _make_question(self, d: dict, concept: str, req: list[str]) -> Question:
        cite = Citation(filename=d["filename"], path=d["path"], page=d.get("page"),
                        section=d.get("section") or "", quote=d["text"][:220])
        # Try LLM for a nicer question, else template
        qtext, key = "", ""
        if concept == "dijkstra-negative-weights":
            qtext = "Can Dijkstra's algorithm handle negative edge weights? Explain why."
            key = "No. Dijkstra requires non-negative weights; Bellman-Ford handles negatives."
        elif concept == "bellman-ford":
            qtext = "How does Bellman-Ford handle negative weights differently from Dijkstra?"
            key = "It relaxes all edges repeatedly instead of greedily finalizing nodes."
        else:
            # generic grounded template
            first = re.split(r"(?<=[.!?])\s+", d["text"].strip())
            core = first[0][:160] if first else d["text"][:160]
            qtext = f"In your own words, explain this from `{d['filename']}`: {core} ..."
            key = core
        if not isinstance(self.llm, FakeLLM):
            try:
                prompt = (
                    f"Source text: {d['text'][:1200]}\n\nWrite a question as JSON: "
                    '{"question": "...", "required": ["..."], "answer_key": "..."}. '
                    "Keep it short and grounded in the source."
                )
                raw = self.llm.generate(prompt)
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    data = json.loads(m.group(0))
                    if data.get("question"):
                        qtext = data["question"]
                        req = data.get("required", req)
                        key = data.get("answer_key", key)
            except Exception:
                pass
        return Question(qid=uuid.uuid4().hex[:8], concept=concept, text=qtext,
                        required_concepts=req, answer_key=key,
                        source_text=d["text"], source_citation=cite)

    def submit_answer(self, q: Question, learner: str) -> Evaluation:
        verdict, missing, misc, expl = self._grade(q, learner)
        self._update_mastery(q.concept, verdict)
        return Evaluation(verdict=verdict, missing=missing, misconception=misc, explanation=expl)

    def _grade(self, q: Question, learner: str) -> tuple[str, list[str], str, str]:
        # Try LLM JSON verdict first (works with FakeLLM + Ollama)
        if True:
            try:
                prompt = (
                    f"Source: {q.source_text[:1200]}\nQuestion: {q.text}\n"
                    f"Required: {q.required_concepts}\nLearner answer: {learner}\n"
                    'Reply as JSON only: {"verdict": "correct|partial|incorrect", '
                    '"missing": [...], "misconception": "...", "explanation": "..."}'
                )
                raw = self.llm.generate(prompt)
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    d = json.loads(m.group(0))
                    v = str(d.get("verdict", "partial")).lower()
                    if v not in ("correct", "partial", "incorrect"):
                        v = "partial"
                    misc = str(d.get("misconception", ""))
                    # rule-based misconception guard for the demo concept
                    if q.concept == "dijkstra-negative-weights" and re.search(r"\byes\b", learner.lower()) and "dijkstra" in learner.lower():
                        misc = "The learner appears to confuse Dijkstra with Bellman-Ford, which does handle negative weights."
                    # relevance guard: don't invent a misconception unrelated to the source
                    if misc and "bellman" in misc.lower() and "bellman" not in q.source_text.lower():
                        misc = ""
                    if v == "correct":
                        misc = ""
                    if v == "incorrect" and not misc:
                        misc = "No clear misconception identified from the source; the answer seems incomplete or off-topic."
                    return v, list(d.get("missing", [])), misc, str(d.get("explanation", ""))
            except Exception:
                pass
        # Keyword fallback
        t = learner.lower()
        hits = sum(1 for r in q.required_concepts for w in re.findall(r"[a-z]{3,}", r.lower()) if w in t)
        if hits >= 3 or ("not" in t and "negative" in t and "dijkstra" in t):
            return "correct", [], "", "Covers the required concept."
        misc = ""
        if q.concept == "dijkstra-negative-weights" and re.search(r"\byes\b", t):
            misc = "The learner appears to confuse Dijkstra with Bellman-Ford, which does handle negative weights."
        return ("incorrect", q.required_concepts, misc, "Missing the key point from the source.") if hits == 0 else ("partial", q.required_concepts, misc, "Partly right.")

    def _update_mastery(self, concept: str, verdict: str) -> MasteryState:
        con = connect()
        try:
            row = con.execute("SELECT * FROM mastery WHERE concept=?", (concept,)).fetchone()
            d = dict(row) if row else {"state": "INTRODUCED", "attempts": 0, "correct": 0, "incorrect": 0, "streak": 0, "ever_failed": 0}
            attempts = d["attempts"] + 1
            correct = d["correct"] + (1 if verdict == "correct" else 0)
            incorrect = d["incorrect"] + (1 if verdict == "incorrect" else 0)
            streak = d["streak"] + 1 if verdict == "correct" else 0
            ever_failed = d["ever_failed"] or (verdict == "incorrect")
            need = self.cfg.get("mastery_need_streak", 2)
            if verdict == "correct" and streak >= need and (not ever_failed or attempts >= 2):
                state = "MASTERED"
            elif verdict == "incorrect":
                state = "STRUGGLING" if attempts > self.cfg.get("max_reteach", 3) else "PRACTICING"
            elif verdict == "correct":
                state = "RETESTING" if ever_failed else "PRACTICING"
            else:
                state = "PRACTICING"
            upsert_mastery(con, concept, state=state, attempts=attempts, correct=correct,
                           incorrect=incorrect, streak=streak, ever_failed=bool(ever_failed))
            try:
                log_attempt(con, concept, verdict)
            except Exception:
                pass
            return MasteryState(concept, state, attempts, correct, incorrect, streak, bool(ever_failed))
        finally:
            con.close()

    def reteach(self, q: Question, ev: Evaluation) -> tuple[str, str]:
        """Return (strategy, explanation). Never reuses a strategy for the concept."""
        con = connect()
        try:
            row = con.execute("SELECT used FROM strategies WHERE concept=?", (q.concept,)).fetchone()
            used = (row["used"].split(",") if row and row["used"] else [])
            nxt = next((s for s in STRATEGIES if s not in used), STRATEGIES[len(used) % len(STRATEGIES)])
            con.execute("INSERT OR IGNORE INTO strategies(concept,used) VALUES(?,?)", (q.concept, ""))
            con.execute("UPDATE strategies SET used=? WHERE concept=?", (",".join(used + [nxt]), q.concept))
            con.commit()
        finally:
            con.close()
        # mark RE-TAUGHT
        con = connect()
        try:
            upsert_mastery(con, q.concept, state="RE-TAUGHT")
        finally:
            con.close()
        src = q.source_text[:900]
        head = {
            "simpler": "Simple version",
            "analogy": "Think of it like this",
            "steps": "Step by step",
            "counterexample": "Counterexample",
            "comparison": "Comparison",
        }[nxt]
        body = ""
        if not isinstance(self.llm, FakeLLM):
            try:
                body = self.llm.generate(
                    f"Re-teach with strategy '{nxt}'. Source: {src}\n"
                    f"Misconception: {ev.misconception}\nKeep it short and consistent with the source."
                )
            except Exception:
                body = ""
        if not body:
            if nxt == "analogy":
                body = ("Think of Dijkstra like a runner who never looks back: once it settles a node it never "
                        f"revisits it, so a later shortcut (negative edge) is missed. {src[:300]}")
            else:
                body = f"{head}: {src[:600]}"
                if ev.misconception:
                    body += f"\nNote: {ev.misconception}"
        cite = f"\n(Source: {q.source_citation.filename} p.{q.source_citation.page or '?'})" if q.source_citation else ""
        return nxt, body + cite

    def retest_question(self, q: Question) -> Question:
        variants = {
            "dijkstra-negative-weights": "A graph has a negative edge. Which algorithm from your notes must you use, and why not the other?",
            "bellman-ford": "Why must you relax edges repeatedly instead of settling nodes once?",
        }
        text = variants.get(q.concept, f"Apply the same idea differently: {q.text}")
        if not isinstance(self.llm, FakeLLM):
            try:
                raw = self.llm.generate(f"Source: {q.source_text[:1000]}\nWrite a NEW different question on the same concept as JSON: {{\"question\": \"...\"}}")
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    d = json.loads(m.group(0))
                    if d.get("question") and d["question"] != q.text:
                        text = d["question"]
            except Exception:
                pass
        return Question(qid=uuid.uuid4().hex[:8], concept=q.concept, text=text,
                        required_concepts=q.required_concepts, answer_key=q.answer_key,
                        source_text=q.source_text, source_citation=q.source_citation)

    def get_progress(self) -> list[MasteryState]:
        con = connect()
        try:
            rows = con.execute("SELECT * FROM mastery ORDER BY updated DESC").fetchall()
            return [MasteryState(r["concept"], r["state"], r["attempts"], r["correct"], r["incorrect"], r["streak"], bool(r["ever_failed"])) for r in rows]
        finally:
            con.close()

    # ---- TIER 2: explain / teach / review / status ----
    def explain(self, concept: str, level: str = "simple") -> Answer:
        """Grounded explanation of a concept: retrieve + summarize only from chunks."""
        hits = ret.retrieve(concept)
        if not hits:
            return Answer(
                text="I couldn't find this in your indexed material. Try ingesting the right folder first.",
                refused=True, evidence_count=0,
            )
        cites = [_cite(h) for h in hits]
        context = "\n\n".join(h.text[:800] for h in hits)
        text = ""
        if not isinstance(self.llm, FakeLLM):
            try:
                style = "like I'm 12, short" if level == "simple" else "step by step, short"
                text = self.llm.generate(
                    f"Explain '{concept}' {style}.\nContext:\n{context}\n"
                    "Use ONLY the context. If missing, reply exactly: NOT IN MATERIAL."
                )
                if "NOT IN MATERIAL" in text.upper():
                    return Answer(text="I couldn't find this in your indexed material.",
                                  citations=cites, refused=True, evidence_count=len(hits))
            except Exception:
                text = ""
        if not text:
            text = f"From your material on '{concept}': " + " ".join(
                re.split(r"(?<=[.!?])\s+", hits[0].text)[:3])
        return Answer(text=text.strip(), citations=cites, refused=False, evidence_count=len(hits))

    def review_list(self) -> list[MasteryState]:
        """Concepts needing practice: STRUGGLING / PRACTICING / RE-TAUGHT, most attempts first."""
        all_m = self.get_progress()
        weak = [m for m in all_m if m.state in ("STRUGGLING", "PRACTICING", "RE-TAUGHT", "RETESTING")]
        weak.sort(key=lambda m: (m.state == "STRUGGLING", m.attempts), reverse=True)
        return weak

    def status(self) -> dict:
        con = connect()
        try:
            ndocs = con.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
            nch = con.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
            docs = [dict(r) for r in con.execute(
                "SELECT filename, chunk_count FROM documents ORDER BY filename").fetchall()]
            mastery = [dict(r) for r in con.execute(
                "SELECT concept, state, attempts, correct, streak FROM mastery ORDER BY updated DESC LIMIT 20").fetchall()]
        finally:
            con.close()
        return {"docs": ndocs, "chunks": nch, "files": docs, "mastery": mastery,
                "model": self.cfg.get("llm_model"), "offline": self.cfg.get("offline")}

    def sources(self) -> list[dict]:
        from .store import list_documents
        con = connect()
        try:
            return list_documents(con)
        finally:
            con.close()

    def remove(self, name_or_path: str) -> int:
        from .store import remove_document
        con = connect()
        try:
            return remove_document(con, name_or_path)
        finally:
            con.close()

    # ---- POWER: search / history / stats / export / practice ----
    def search(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        return ret.retrieve(query, top_k=k)

    def history(self, limit: int = 20) -> list[dict]:
        from .store import recent_attempts
        con = connect()
        try:
            return recent_attempts(con, limit)
        finally:
            con.close()

    def heatmap(self, days: int = 28) -> list[int]:
        from .store import attempts_per_day
        con = connect()
        try:
            return attempts_per_day(con, days)
        finally:
            con.close()

    def stats(self) -> dict:
        s = self.status()
        heat = self.heatmap(28)
        hist = self.history(10)
        prog = self.get_progress()
        mastered = sum(1 for m in prog if m.state == "MASTERED")
        total_att = sum(m.attempts for m in prog)
        cur = 0
        for v in reversed(heat):
            if v > 0:
                cur += 1
            elif cur:
                break
        # current streak = trailing non-zero days
        streak_now = 0
        for v in reversed(heat):
            if v > 0:
                streak_now += 1
            else:
                break
        return {"status": s, "heatmap": heat, "history": hist,
                "mastered": mastered, "concepts": len(prog),
                "attempts": total_att, "streak_now": streak_now}

    def flashcard_deck(self, topic: str = "", n: int = 10) -> list[Question]:
        qs = self.start_test(topic=topic, n=n)
        return qs

    def daily_plan(self) -> list[Question]:
        weak = self.review_list()
        out: list[Question] = []
        if weak:
            try:
                out.extend(self.start_test(topic=weak[0].concept.replace("-", " "), n=1))
            except Exception:
                pass
        try:
            fresh = self.start_test(topic="", n=1)
            if fresh and (not out or fresh[0].concept != out[0].concept):
                out.extend(fresh)
        except Exception:
            pass
        return out[:2]

    def export_data(self, fmt: str = "json") -> str:
        import json as _j
        s = self.status()
        prog = [{"concept": m.concept, "state": m.state, "attempts": m.attempts,
                 "correct": m.correct, "streak": m.streak} for m in self.get_progress()]
        hist = self.history(50)
        fmt = fmt.lower()
        if fmt == "json":
            return _j.dumps({"status": s, "mastery": prog, "history": hist}, indent=2)
        if fmt == "md":
            lines = ["# mindloop journal", ""]
            lines.append(f"{s['docs']} docs, {s['chunks']} chunks")
            lines.append("")
            for m in prog:
                lines.append(f"- {m['concept']}: {m['state']} (att {m['attempts']}, streak {m['streak']})")
            lines.append("")
            for h in hist:
                lines.append(f"- {h.get('at','')}: {h.get('concept','')} -> {h.get('verdict','')}")
            return "\n".join(lines) + "\n"
        if fmt in ("anki", "tsv"):
            rows = [f"{m['concept']}\t{m['state']}  att {m['attempts']}\tmindloop" for m in prog]
            return "\n".join(rows) + ("\n" if rows else "")
        raise ValueError(f"unknown format {fmt!r} (json|md|anki)")
