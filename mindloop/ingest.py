"""Parsers + chunking + folder ingest. Simple and effective."""
from __future__ import annotations
import hashlib
import re
import time
import uuid
from pathlib import Path
from .models import IngestResult
from .store import connect
from .config import load_config

SUPPORTED = {".pdf", ".txt", ".md", ".srt", ".markdown", ".docx"}

def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def parse_txt(p: Path) -> list[tuple[str | None, str, str]]:
    text = p.read_text(encoding="utf-8", errors="ignore")
    return [(None, "", text)]

def parse_md(p: Path) -> list[tuple[str | None, str, str]]:
    text = p.read_text(encoding="utf-8", errors="ignore")
    # split by headings to keep section names
    parts: list[tuple[str | None, str, str]] = []
    cur_sec = ""
    cur_buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m:
            if cur_buf:
                parts.append((None, cur_sec, "\n".join(cur_buf)))
                cur_buf = []
            cur_sec = m.group(1).strip()
        cur_buf.append(line)
    if cur_buf:
        parts.append((None, cur_sec, "\n".join(cur_buf)))
    return parts or [(None, "", text)]

def parse_srt(p: Path) -> list[tuple[str | None, str, str]]:
    raw = p.read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\n\s*\n", raw)
    out: list[tuple[str | None, str, str]] = []
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            ts = lines[1]
            out.append((ts, "", " ".join(lines[2:])))
        elif lines:
            out.append((None, "", " ".join(lines)))
    return out or [(None, "", raw)]

def parse_pdf(p: Path) -> list[tuple[str | None, str, str]]:
    try:
        import pymupdf
    except ImportError as e:
        raise RuntimeError("PyMuPDF not installed. Run: python -m pip install pymupdf") from e
    doc = pymupdf.open(str(p))
    out: list[tuple[str | None, str, str]] = []
    for i, page in enumerate(doc):
        t = page.get_text().strip()
        if t:
            out.append((str(i + 1), "", t))
    if not out:
        raise RuntimeError(
            f"`{p.name}` has no extractable text (scanned PDF?). "
            "Try a text-based PDF. OCR is not enabled in this version."
        )
    return out

def parse_docx(p: Path) -> list[tuple[str | None, str, str]]:
    try:
        import docx
    except ImportError as e:
        raise RuntimeError("python-docx not installed. Run: python -m pip install python-docx") from e
    d = docx.Document(str(p))
    paras = [para.text.strip() for para in d.paragraphs if para.text.strip()]
    text = "\n".join(paras)
    if not text.strip():
        raise RuntimeError(f"`{p.name}` has no extractable text (empty DOCX?).")
    return [(None, "", text)]

def parse_file(p: Path) -> list[tuple[str | None, str, str]]:
    ext = p.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(p)
    if ext in (".md", ".markdown"):
        return parse_md(p)
    if ext == ".srt":
        return parse_srt(p)
    if ext == ".txt":
        return parse_txt(p)
    if ext == ".docx":
        return parse_docx(p)
    raise RuntimeError(f"Unsupported file type `{p.suffix}` for `{p.name}`. Supported: PDF, TXT, MD, SRT, DOCX.")

def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out, i = [], 0
    while i < len(text):
        j = min(i + size, len(text))
        # try to cut at sentence end
        if j < len(text):
            k = text.rfind(". ", i, j)
            if k > i + size // 2:
                j = k + 1
        out.append(text[i:j].strip())
        i = max(j - overlap, j) if j < len(text) else len(text)
        if i >= len(text):
            break
    return [c for c in out if c]

def ingest_path(path: str | Path) -> IngestResult:
    cfg = load_config()
    size, overlap = cfg["chunk_size"], cfg["chunk_overlap"]
    p = Path(path).expanduser().resolve()
    res = IngestResult()
    files: list[Path] = []
    if p.is_file():
        files = [p]
    elif p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix.lower() in SUPPORTED:
                files.append(f)
    else:
        raise RuntimeError(f"Path not found: {p}. Check the spelling and try again.")
    if not files:
        raise RuntimeError(f"No supported files found in `{p}`. Supported: PDF, TXT, MD, SRT, DOCX.")

    con = connect()
    try:
        for f in files:
            try:
                h = file_hash(f)
                row = con.execute("SELECT hash FROM documents WHERE path=?", (str(f),)).fetchone()
                if row and row["hash"] == h:
                    res.files_skipped.append(f.name)
                    continue
                units = parse_file(f)
                # delete old chunks for re-index
                doc_id = str(f)
                con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
                n = 0
                for page, section, utext in units:
                    for c in chunk_text(utext, size, overlap):
                        cid = f"{h[:12]}-{n:04d}"
                        con.execute(
                            "INSERT OR REPLACE INTO chunks(chunk_id,doc_id,filename,path,page,section,text) VALUES(?,?,?,?,?,?,?)",
                            (cid, doc_id, f.name, str(f), page, section, c),
                        )
                        n += 1
                con.execute(
                    "INSERT OR REPLACE INTO documents(doc_id,path,filename,ftype,hash,indexed_at,chunk_count,status) VALUES(?,?,?,?,?,?,?,?)",
                    (doc_id, str(f), f.name, f.suffix.lower(), h, time.time(), n, "ok"),
                )
                con.commit()
                res.files_ok.append(f.name)
                res.chunks_added += n
            except Exception as e:
                res.files_failed.append((f.name, str(e)))
        # cleanup: if ingesting a folder, drop docs whose files disappeared
        if p.is_dir():
            try:
                rows = con.execute("SELECT doc_id, path, filename FROM documents").fetchall()
                for r in rows:
                    dp = Path(r["path"])
                    try:
                        inside = dp.resolve().is_relative_to(p)
                    except AttributeError:
                        inside = str(p) in str(dp.resolve())  # py3.10 fallback
                    if inside and not dp.exists():
                        con.execute("DELETE FROM chunks WHERE doc_id=?", (r["doc_id"],))
                        con.execute("DELETE FROM documents WHERE doc_id=?", (r["doc_id"],))
                        con.commit()
            except Exception:
                pass
    finally:
        res.docs_total = con.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
        con.close()
    return res

def all_chunks() -> list[dict]:
    con = connect()
    try:
        rows = con.execute("SELECT * FROM chunks").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
