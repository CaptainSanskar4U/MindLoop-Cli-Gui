"""LLM providers. Local Ollama + deterministic Fake for tests. No cloud calls."""
from __future__ import annotations
import re
from typing import Optional


class LLMProvider:
    name = "base"

    def generate(self, prompt: str, system: str = "", timeout: int = 60) -> str:
        raise NotImplementedError

    def available(self) -> tuple[bool, str]:
        """Return (ok, message)."""
        return False, "not implemented"


class OllamaLLM(LLMProvider):
    name = "ollama"

    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434", timeout: int = 60):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        try:
            import httpx
            r = httpx.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code != 200:
                return False, f"Ollama responded with status {r.status_code}."
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if self.model not in models and not any(self.model in m for m in models):
                return False, (
                    f"Model '{self.model}' not downloaded. "
                    f"Run: ollama pull {self.model}"
                )
            return True, "ok"
        except Exception:
            return False, (
                "Ollama is not running. Install from https://ollama.com "
                "then run: ollama serve  (in another terminal: "
                f"ollama pull {self.model})"
            )

    def generate(self, prompt: str, system: str = "", timeout: int = 60) -> str:
        import httpx
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "Answer only from the provided context. Be short.",
            "stream": False,
            "options": {"temperature": 0.1},
        }
        try:
            r = httpx.post(f"{self.host}/api/generate", json=payload, timeout=timeout or self.timeout)
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e


class FakeLLM(LLMProvider):
    """Deterministic fake for tests/offline. No model needed."""
    name = "fake"

    def available(self) -> tuple[bool, str]:
        return True, "ok"

    def generate(self, prompt: str, system: str = "", timeout: int = 60) -> str:
        p = prompt.lower()
        # Evaluation prompts - look at the LEARNER part only (after marker)
        if "learner answer" in p or "student answer" in p:
            learner_part = p.split("learner answer")[-1] if "learner answer" in p else p.split("student answer")[-1]
            says_yes = re.search(r"\byes\b", learner_part) is not None
            mentions_dijkstra = "dijkstra" in learner_part
            mentions_negative = "negative" in learner_part
            if says_yes and mentions_dijkstra:
                return '{"verdict": "incorrect", "missing": ["Dijkstra fails with negative weights"], "misconception": "The learner appears to confuse Dijkstra with Bellman-Ford, which does handle negative weights.", "explanation": "Source says Dijkstra requires non-negative weights."}'
            # correct if learner says no/cannot + negative, or mentions non-negative, or bellman-ford correctly
            if mentions_negative and (re.search(r"\bno\b", learner_part) or "cannot" in learner_part or "not support" in learner_part or "non-negative" in learner_part or "nonnegative" in learner_part or "bellman" in learner_part or "does not" in learner_part or "doesn't" in learner_part):
                return '{"verdict": "correct", "missing": [], "misconception": "", "explanation": "Covers the required concept."}'
            return '{"verdict": "partial", "missing": ["key detail"], "misconception": "", "explanation": "Partly right."}'
        # Question generation prompts
        if "write a question" in p or "new question" in p:
            return '{"question": "Why can Bellman-Ford handle negative weights while Dijkstra cannot?", "required": ["Dijkstra needs non-negative weights", "Bellman-Ford relaxes edges"], "answer_key": "Dijkstra greedily finalizes nodes so negatives break it; Bellman-Ford relaxes all edges repeatedly."}'
        # Re-teach prompts
        if "re-teach" in p or "reteach" in p or "analogy" in p:
            return "Think of Dijkstra like a runner who never looks back: once it passes a town it never returns, so a shortcut (negative edge) found later is missed. Bellman-Ford walks every road many times, so it finds shortcuts."
        # Default ask
        return "Based on your material: Dijkstra does not support negative edge weights; Bellman-Ford does."
