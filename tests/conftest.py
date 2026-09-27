"""Isolated MINDLOOP_HOME for every test. Offline, Fake providers."""
import os
import tempfile
from pathlib import Path
import pytest

@pytest.fixture()
def home(monkeypatch):
    d = Path(tempfile.mkdtemp(prefix="mindloop-test-"))
    monkeypatch.setenv("MINDLOOP_HOME", str(d))
    monkeypatch.setenv("MINDLOOP_OFFLINE", "1")
    # make sample files
    (d / "study").mkdir()
    (d / "study" / "notes.md").write_text(
        "# Dijkstra\n\nDijkstra's algorithm does NOT support negative edge weights. "
        "Bellman-Ford DOES handle negative edge weights by relaxing every edge repeatedly.\n",
        encoding="utf-8",
    )
    (d / "study" / "lecture.srt").write_text(
        "1\n00:00:01,000 --> 00:00:05,000\nDijkstra greedily settles nodes and never revisits them.\n",
        encoding="utf-8",
    )
    (d / "study" / "plain.txt").write_text("Time complexity O(n log n) for mergesort.", encoding="utf-8")
    return d
