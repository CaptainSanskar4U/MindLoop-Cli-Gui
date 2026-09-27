"""Structured objects. Engine RETURNS these, CLI only formats them."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Citation:
    filename: str
    path: str
    page: Optional[str]  # "2" or "2-3" or "00:01:10-00:01:25" for SRT, None for txt
    section: str = ""
    quote: str = ""      # verbatim excerpt, sliced by CODE

@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    filename: str
    path: str
    page: Optional[str]
    section: str
    text: str
    score: float = 0.0

@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    refused: bool = False
    partial: bool = False
    evidence_count: int = 0

@dataclass
class Question:
    qid: str
    concept: str
    text: str
    qtype: str = "short"  # short | mcq | explain | comparison
    choices: list[str] = field(default_factory=list)
    answer_key: str = ""          # short expected answer (for fallback grading)
    required_concepts: list[str] = field(default_factory=list)
    source_text: str = ""         # grounding text
    source_citation: Optional[Citation] = None

@dataclass
class Evaluation:
    verdict: str  # correct | partial | incorrect
    missing: list[str] = field(default_factory=list)
    misconception: str = ""
    explanation: str = ""

@dataclass
class MasteryState:
    concept: str
    state: str  # UNKNOWN|INTRODUCED|PRACTICING|STRUGGLING|RE-TAUGHT|RETESTING|MASTERED
    attempts: int = 0
    correct: int = 0
    incorrect: int = 0
    streak: int = 0
    ever_failed: bool = False

@dataclass
class IngestResult:
    files_ok: list[str] = field(default_factory=list)
    files_skipped: list[str] = field(default_factory=list)
    files_failed: list[tuple[str, str]] = field(default_factory=list)
    chunks_added: int = 0
    docs_total: int = 0
