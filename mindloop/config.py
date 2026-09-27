"""Simple config system. Home = MINDLOOP_HOME or ~/.mindloop."""
from __future__ import annotations
import json
import os
from pathlib import Path

DEFAULTS = {
    "llm_model": "llama3.2:3b",
    "ollama_host": "http://localhost:11434",
    "llm_timeout": 60,
    "chunk_size": 800,          # characters per chunk
    "chunk_overlap": 120,
    "retrieval_count": 4,       # top-k chunks for ask
    "relevance_threshold": 0.12,  # TF-IDF cosine below this = refuse
    "mastery_need_streak": 2,   # correct in a row to master
    "max_reteach": 3,
    "offline": False,
    "animation": True,
    "ink": "sumi",
    "daily_n": 2,
}

def get_home() -> Path:
    override = os.environ.get("MINDLOOP_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".mindloop"

def config_path() -> Path:
    return get_home() / "config.json"

def db_path() -> Path:
    return get_home() / "mindloop.db"

def ensure_dirs() -> Path:
    home = get_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "knowledge").mkdir(exist_ok=True)
    (home / "logs").mkdir(exist_ok=True)
    return home

def load_config() -> dict:
    cfg = dict(DEFAULTS)
    p = config_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
        except Exception:
            pass  # corrupt config -> use defaults, doctor will warn
    # env override for offline
    if os.environ.get("MINDLOOP_OFFLINE") == "1":
        cfg["offline"] = True
    return cfg

def save_config(cfg: dict) -> None:
    ensure_dirs()
    keep = {k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS}
    config_path().write_text(json.dumps(keep, indent=2), encoding="utf-8")
