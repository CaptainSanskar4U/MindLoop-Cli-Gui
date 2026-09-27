"""TF-IDF retrieval. Simple, offline, fast. No model download needed."""
from __future__ import annotations
from .models import RetrievedChunk
from .store import connect
from .config import load_config

def retrieve(query: str, top_k: int = 0, threshold: float = 0.0) -> list[RetrievedChunk]:
    cfg = load_config()
    top_k = top_k or cfg["retrieval_count"]
    threshold = threshold if threshold else cfg["relevance_threshold"]
    con = connect()
    try:
        rows = con.execute("SELECT * FROM chunks").fetchall()
    finally:
        con.close()
    if not rows:
        return []
    docs = [r["text"] for r in rows]
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e:
        raise RuntimeError("scikit-learn not installed. Run: python -m pip install scikit-learn") from e
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit(docs + [query])
    m = vec.transform(docs)
    q = vec.transform([query])
    scores = cosine_similarity(q, m)[0]
    out: list[RetrievedChunk] = []
    for r, s in zip(rows, scores):
        if s >= threshold:
            out.append(RetrievedChunk(
                chunk_id=r["chunk_id"], doc_id=r["doc_id"], filename=r["filename"],
                path=r["path"], page=r["page"], section=r["section"] or "",
                text=r["text"], score=float(s),
            ))
    out.sort(key=lambda c: c.score, reverse=True)
    return out[:top_k]
