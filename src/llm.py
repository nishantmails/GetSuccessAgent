"""LLM factory.

Real mode  -> langchain_openai.ChatOpenAI (needs OPENAI_API_KEY)
Dry-run    -> deterministic heuristic stub with the SAME
              `.with_structured_output(schema).invoke(prompt)` interface,
              so the full pipeline can be tested offline.
"""
from __future__ import annotations

import re
from typing import Any, Type

from pydantic import BaseModel

from .schemas import Calibration, SourceAnalysis

_POSITIVE = {
    "excellent", "outstanding", "strong", "great", "exceeded", "exceeds", "proactive",
    "reliable", "exceptional", "improved", "leadership", "delivered", "ownership",
    "collaborative", "praised", "consistently", "quality", "mentoring", "innovative",
    "commendable", "dedicated", "initiative", "positive", "asset", "kudos",
}
_NEGATIVE = {
    "concern", "improvement", "missed", "poor", "lack", "lacks", "struggled",
    "delay", "delayed", "escalation", "unreliable", "below", "issue", "complaint",
    "weak", "absent", "disciplinary", "slip", "gap", "risk", "conflict", "negative",
    "inconsistent", "underperform",
}


def _heuristic_score(text: str) -> tuple[float, int, int]:
    words = re.findall(r"[a-z']+", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    score = min(5.0, max(1.0, round(3.0 + 0.35 * (pos - neg), 1)))
    return score, pos, neg


def _sentences_with(text: str, vocab: set[str], limit: int = 3) -> list[str]:
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if any(w in sent.lower() for w in vocab) and 20 < len(sent) < 220:
            out.append(sent.strip())
        if len(out) == limit:
            break
    return out


class _StubStructured:
    """Mimics the runnable returned by ChatOpenAI.with_structured_output()."""

    def __init__(self, schema: Type[BaseModel]):
        self.schema = schema

    def invoke(self, prompt: str, **_: Any) -> BaseModel:
        if self.schema is SourceAnalysis:
            return self._source_analysis(prompt)
        if self.schema is Calibration:
            return self._calibration(prompt)
        raise NotImplementedError(f"Stub does not support schema {self.schema}")

    # -- builders ----------------------------------------------------------
    def _source_analysis(self, prompt: str) -> SourceAnalysis:
        m = re.search(r"<feedback>(.*?)</feedback>", prompt, re.S)
        text = m.group(1).strip() if m else prompt
        role_m = re.search(r"Reviewer role:\s*(.+)", prompt)
        role = role_m.group(1).strip() if role_m else "Reviewer"
        score, pos, neg = _heuristic_score(text)
        sentiment = "positive" if pos - neg >= 2 else "negative" if neg - pos >= 2 else "mixed"
        confidence = "high" if len(text) > 400 else "medium" if len(text) > 150 else "low"
        strengths = _sentences_with(text, _POSITIVE) or ["No explicit strengths stated."]
        concerns = _sentences_with(text, _NEGATIVE) or ["No explicit concerns stated."]
        summary = (
            f"[DRY-RUN heuristic] {role} feedback contains {pos} positive and "
            f"{neg} negative signals; implied score {score}/5."
        )
        return SourceAnalysis(
            summary=summary, strengths=strengths, concerns=concerns,
            score=score, sentiment=sentiment, confidence=confidence,
        )

    def _calibration(self, prompt: str) -> Calibration:
        name_m = re.search(r"Employee:\s*(.+)", prompt)
        name = name_m.group(1).strip() if name_m else "the employee"
        scores = {
            role: float(s)
            for role, s in re.findall(
                r"(People Manager|Account Manager|HR)\s+score:\s*([0-9.]+)", prompt
            )
        }
        flags: list[str] = []
        if scores:
            hi, lo = max(scores.values()), min(scores.values())
            if hi - lo > 1.5:
                hi_role = max(scores, key=scores.get)
                lo_role = min(scores, key=scores.get)
                flags.append(
                    f"Large divergence: {hi_role} ({hi}) vs {lo_role} ({lo}) — "
                    "verify both reviewers assessed the same period/projects."
                )
        narrative = (
            f"[DRY-RUN heuristic] Comparative review for {name}. Source scores: "
            + (", ".join(f"{r} {s}/5" for r, s in scores.items()) or "n/a")
            + ". Run with a real LLM (--no-dry-run) for an evidence-based narrative."
        )
        return Calibration(
            comparative_feedback=narrative,
            key_themes=["dry-run heuristic output"],
            consistency_flags=flags,
        )


class DryRunLLM:
    """Drop-in replacement exposing only what the agents use."""

    def with_structured_output(self, schema: Type[BaseModel]) -> _StubStructured:
        return _StubStructured(schema)


def build_llm(cfg: dict, dry_run: bool = False) -> Any:
    """Return the LLM (or dry-run stub) used by every agent node."""
    if dry_run:
        return DryRunLLM()

    from langchain_openai import ChatOpenAI  # imported lazily so dry-run needs no key

    llm_cfg = cfg.get("llm", {})
    return ChatOpenAI(
        model=llm_cfg.get("model", "gpt-4o-mini"),
        temperature=llm_cfg.get("temperature", 0.1),
    )
