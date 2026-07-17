"""Load and validate feedback data from Excel / CSV files.

Expected columns (case-insensitive, underscores or spaces both fine):
    employee_id      - unique employee identifier
    employee_name    - display name
    employee_role    - (optional) designation / level
    reviewer_role    - one of: People Manager | Account Manager | HR
    feedback         - free-text feedback
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schemas import REVIEWER_ROLES, FeedbackRecord

_COL_ALIASES = {
    "employee_id": {"employee_id", "employee id", "emp_id", "emp id", "id"},
    "employee_name": {"employee_name", "employee name", "name", "emp_name", "emp name"},
    "employee_role": {"employee_role", "employee role", "role", "designation", "level"},
    "reviewer_role": {"reviewer_role", "reviewer role", "source", "feedback_source", "feedback source"},
    "feedback": {"feedback", "comments", "feedback_text", "feedback text", "review"},
}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    lookup = {}
    for canonical, aliases in _COL_ALIASES.items():
        for col in df.columns:
            if str(col).strip().lower() in aliases:
                lookup[col] = canonical
                break
    df = df.rename(columns=lookup)
    missing = {"employee_id", "employee_name", "reviewer_role", "feedback"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Input file is missing required column(s): {sorted(missing)}. "
            f"Found columns: {list(df.columns)}"
        )
    if "employee_role" not in df.columns:
        df["employee_role"] = ""
    return df


def load_feedback(path: str | Path) -> list[FeedbackRecord]:
    """Read an .xlsx / .xls / .csv feedback file into validated records."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file type '{suffix}'. Use .xlsx, .xls or .csv")

    df = _normalise_columns(df)
    df = df.dropna(subset=["employee_id", "reviewer_role", "feedback"])

    records: list[FeedbackRecord] = []
    for i, row in df.iterrows():
        role = str(row["reviewer_role"]).strip()
        if role not in REVIEWER_ROLES:
            raise ValueError(
                f"Row {i + 2}: reviewer_role '{role}' is invalid. "
                f"Must be one of {REVIEWER_ROLES}."
            )
        records.append(
            FeedbackRecord(
                employee_id=str(row["employee_id"]).strip(),
                employee_name=str(row["employee_name"]).strip(),
                employee_role=str(row.get("employee_role", "") or "").strip(),
                reviewer_role=role,  # type: ignore[arg-type]
                feedback=str(row["feedback"]).strip(),
            )
        )
    if not records:
        raise ValueError("Input file contained no usable feedback rows.")
    return records


def group_by_employee(records: list[FeedbackRecord]) -> dict[str, dict]:
    """Group flat records into the per-employee bundle the agents work on.

    Returns {employee_id: {employee_id, employee_name, employee_role,
                           feedbacks: {reviewer_role: feedback_text}}}
    Multiple rows from the same reviewer for the same employee are concatenated.
    """
    employees: dict[str, dict] = {}
    for rec in records:
        emp = employees.setdefault(
            rec.employee_id,
            {
                "employee_id": rec.employee_id,
                "employee_name": rec.employee_name,
                "employee_role": rec.employee_role,
                "feedbacks": {},
            },
        )
        existing = emp["feedbacks"].get(rec.reviewer_role)
        emp["feedbacks"][rec.reviewer_role] = (
            f"{existing}\n{rec.feedback}" if existing else rec.feedback
        )
    return employees
