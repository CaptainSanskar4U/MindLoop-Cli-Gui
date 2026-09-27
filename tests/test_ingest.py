"""Ingestion: TXT/MD/SRT, folder, incremental."""
from pathlib import Path
from mindloop.engine import MindloopEngine
from mindloop.providers import FakeLLM
from mindloop.store import connect, chunk_count

def test_folder_ingest(home):
    eng = MindloopEngine(llm=FakeLLM())
    res = eng.ingest(home / "study")
    assert len(res.files_ok) == 3, res
    assert res.chunks_added >= 3
    assert res.docs_total == 3

def test_incremental_skip(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    res2 = eng.ingest(home / "study")
    assert len(res2.files_skipped) == 3
    assert res2.chunks_added == 0

def test_changed_file_reindexed(home):
    eng = MindloopEngine(llm=FakeLLM())
    eng.ingest(home / "study")
    (home / "study" / "plain.txt").write_text("Time complexity O(n log n). Added line about quicksort.", encoding="utf-8")
    res = eng.ingest(home / "study")
    assert "plain.txt" in res.files_ok

def test_unsupported_ignored(home):
    (home / "study" / "img.png").write_bytes(b"\x89PNG")
    eng = MindloopEngine(llm=FakeLLM())
    res = eng.ingest(home / "study")
    assert all("png" not in f for f in res.files_ok)
