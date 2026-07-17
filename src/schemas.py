"""Pydantic models shared across the pipeline.

These models are used both for plain data handling and as the structured-output
schemas the LLM agents must conform to.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

REVIEWER_ROLES: tuple[str, str, str] = ("People Manager", "Account Manager", "HR")
ReviewerRole = Literal["People Manager", "Account Manager", "HR"]


class FeedbackRecord(BaseModel):
    """One row of the input file: one reviewer's feedback for one employee."""

    employee_id: str
    employee_name: str
    employee_role: str = ""
    reviewer_role: ReviewerRole
    feedback: str


class SourceAnalysis(BaseModel):
    """Structured analysis of ONE reviewer's feedback for ONE employee."""

    summary: str = Field(description="2-4 sentence factual summary of the feedback")
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    score: float = Field(
        ge=1.0, le=5.0,
        description="Performance score implied by this feedback alone, 1 (poor) to 5 (exceptional)",
    )
    sentiment: Literal["positive", "mixed", "negative"]
    confidence: Literal["low", "medium", "high"] = Field(
        description="How much concrete evidence the feedback contains"
    )


class Calibration(BaseModel):
    """Cross-source calibration for ONE employee."""

    comparative_feedback: str = Field(
        description=(
            "A narrative paragraph (5-8 sentences) that comparatively reviews the employee: "
            "weighs all three sources, calls out agreement/disagreement, and justifies the composite score."
        )
    )
    key_themes: list[str] = Field(default_factory=list)
    consistency_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Discrepancies or bias signals across sources (e.g. 'PM score far above HR score', "
            "'feedback is generic with no evidence'). Empty list if sources are consistent."
        ),
    )


class FinalRating(BaseModel):
    """The end-of-pipeline record for one employee."""

    employee_id: str
    employee_name: str
    employee_role: str = ""
    source_scores: dict[str, float] = Field(default_factory=dict)
    composite_score: float
    percentile: float = Field(description="Rank percentile within the review population, 0-100")
    band: str
    rating: int = Field(ge=1, le=5)
    comparative_feedback: str
    key_themes: list[str] = Field(default_factory=list)
    consistency_flags: list[str] = Field(default_factory=list)
