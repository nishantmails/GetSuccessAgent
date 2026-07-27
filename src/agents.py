"""Agent prompts and the per-employee review logic.

For every employee the pipeline runs:
  1. Three SOURCE-ANALYST agents  (People Manager / Account Manager / HR)
     each turning raw feedback into a structured, scored analysis.
  2. One CALIBRATION agent that cross-examines the three analyses,
     flags inconsistencies / bias, and writes the comparative narrative.

The composite score is computed DETERMINISTICALLY (weighted average of the
source scores) so that the number fed into the bell curve is fully auditable —
the LLM writes prose, arithmetic stays in code.
"""
from __future__ import annotations

from typing import Any
import re
from pathlib import Path

from .schemas import REVIEWER_ROLES, Calibration, SourceAnalysis


def _load_prompts() -> tuple[str, str]:
        """Load prompts from `src/prompts.md`. Return (analyst, calibration).

        Falls back to the original in-code prompts if the markdown file is missing
        or cannot be parsed.
        """
        default_analyst = """\
You are an experienced HR analyst preparing year-end performance review material.

Employee: {employee_name}{role_clause}
Reviewer role: {reviewer_role}

Analyse the following year-end feedback from this reviewer, objectively and only
on the evidence present in the text.

Scoring rubric (score field):
    1 = exceptional, clearly exceeds role expectations
    2 = exceeds expectations in several areas
    3 = fully meets expectations
    4 = partially meets expectations, notable gaps
    5 = below expectations

Rules:
- Do not invent accomplishments that are not in the text.
- Strengths and concerns must be short phrases grounded in the feedback.
- confidence reflects how specific/evidence-based the feedback is
    (generic praise with no examples = low).

<feedback>
{feedback}
</feedback>
"""

        default_calibration = """\
You are a senior HR calibration partner in a year-end review panel.

Employee: {employee_name}{role_clause}

Below are structured analyses of this employee's three feedback sources.

{source_block}

Tasks:
1. Write a comparative feedback paragraph that weighs all three sources,
     explicitly noting where reviewers agree and disagree.
2. List the key themes (3-6 short phrases).
3. List consistency_flags for anything the calibration panel should double-check:
     - score divergence greater than 1.5 between sources,
     - one source generic/evidence-poor while others are specific,
     - signs of halo effect, recency bias, or personality-based comments.
     Return an empty list if the sources are consistent.
"""

        p = Path(__file__).resolve().parent / "prompts.md"
        try:
                txt = p.read_text(encoding="utf-8")
                # Capture sections that start with a heading: '## NAME' followed by content
                parts = dict(re.findall(r"^##\s*(.+?)\s*$\n(.*?)(?=^##\s*.+?$|\Z)", txt, flags=re.M | re.S))
                analyst = parts.get("ANALYST_PROMPT", default_analyst).rstrip()
                calib = parts.get("CALIBRATION_PROMPT", default_calibration).rstrip()
                return analyst, calib
        except Exception:
                return default_analyst, default_calibration


ANALYST_PROMPT, CALIBRATION_PROMPT = _load_prompts()


def _role_clause(employee: dict) -> str:
    return f" (role: {employee['employee_role']})" if employee.get("employee_role") else ""


def analyse_source(employee: dict, reviewer_role: str, feedback: str, llm: Any) -> SourceAnalysis:
    """Run one source-analyst agent."""
    prompt = ANALYST_PROMPT.format(
        employee_name=employee["employee_name"],
        role_clause=_role_clause(employee),
        reviewer_role=reviewer_role,
        feedback=feedback,
    )
    return llm.with_structured_output(SourceAnalysis).invoke(prompt)


def calibrate(employee: dict, analyses: dict[str, SourceAnalysis], llm: Any) -> Calibration:
    """Run the calibration agent over the source analyses."""
    blocks = []
    for role in REVIEWER_ROLES:
        a = analyses.get(role)
        if a is None:
            blocks.append(f"--- {role} ---\nNo feedback provided.")
            continue
        blocks.append(
            f"--- {role} ---\n"
            f"{role} score: {a.score}\n"
            f"Sentiment: {a.sentiment} | Confidence: {a.confidence}\n"
            f"Summary: {a.summary}\n"
            f"Strengths: {'; '.join(a.strengths) or 'none'}\n"
            f"Concerns: {'; '.join(a.concerns) or 'none'}"
        )
    prompt = CALIBRATION_PROMPT.format(
        employee_name=employee["employee_name"],
        role_clause=_role_clause(employee),
        source_block="\n\n".join(blocks),
    )
    return llm.with_structured_output(Calibration).invoke(prompt)


def composite_score(analyses: dict[str, SourceAnalysis], weights: dict[str, float]) -> float:
    """Deterministic weighted average; missing sources get weights renormalised."""
    total_w = total = 0.0
    for role, analysis in analyses.items():
        w = weights.get(role, 0.0)
        total += analysis.score * w
        total_w += w
    return round(total / total_w, 2) if total_w else 0.0


def review_employee(employee: dict, llm: Any, weights: dict[str, float]) -> dict:
    """Full agentic review of one employee. Returns a plain-dict result."""
    analyses: dict[str, SourceAnalysis] = {}
    for role in REVIEWER_ROLES:
        feedback = employee["feedbacks"].get(role)
        if feedback:
            analyses[role] = analyse_source(employee, role, feedback, llm)

    missing = [r for r in REVIEWER_ROLES if r not in analyses]
    calibration = calibrate(employee, analyses, llm)
    if missing:
        calibration.consistency_flags.append(
            f"Missing feedback from: {', '.join(missing)} — score renormalised over available sources."
        )

    return {
        "employee_id": employee["employee_id"],
        "employee_name": employee["employee_name"],
        "employee_role": employee.get("employee_role", ""),
        "source_analyses": {role: a.model_dump() for role, a in analyses.items()},
        "calibration": calibration.model_dump(),
        "composite_score": composite_score(analyses, weights),
        "missing_sources": missing,
    }
