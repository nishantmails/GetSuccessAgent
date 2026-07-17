"""Deterministic bell-curve fitment.

Employees are ranked by composite score; each band claims the top `top_pct`
percent of the population (cumulative cut-offs read top-down from config).
"""
from __future__ import annotations

from .schemas import REVIEWER_ROLES, FinalRating


def apply_bell_curve(results: dict[str, dict], bands: list[dict]) -> list[FinalRating]:
    if not results:
        return []
    if not bands or abs(bands[-1]["top_pct"] - 100.0) > 1e-6:
        raise ValueError("Bell-curve bands must end with a band whose top_pct is 100.")

    ranked = sorted(results.values(), key=lambda r: (-r["composite_score"], r["employee_name"]))
    n = len(ranked)
    finals: list[FinalRating] = []

    for rank, r in enumerate(ranked, start=1):
        # top_position: how far from the top this employee sits, in % of the
        # population (rank 1 of N -> 100/N %). Bands claim cumulative cut-offs
        # from the top, so top_position <= top_pct selects the right band.
        top_position = 100.0 * rank / n
        band = next(b for b in bands if top_position <= float(b["top_pct"]) + 1e-9)
        percentile = round(100.0 * (n - rank + 1) / n, 1)  # display: 100 = best
        cal = r["calibration"]
        finals.append(
            FinalRating(
                employee_id=r["employee_id"],
                employee_name=r["employee_name"],
                employee_role=r.get("employee_role", ""),
                source_scores={
                    role: r["source_analyses"][role]["score"]
                    for role in REVIEWER_ROLES
                    if role in r["source_analyses"]
                },
                composite_score=r["composite_score"],
                percentile=percentile,
                band=band["band"],
                rating=int(band["rating"]),
                comparative_feedback=cal["comparative_feedback"],
                key_themes=cal.get("key_themes", []),
                consistency_flags=cal.get("consistency_flags", []),
            )
        )
    return finals
