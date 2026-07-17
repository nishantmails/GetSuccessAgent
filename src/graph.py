"""LangGraph pipeline.

    START
      └─ load_data ──(Send per employee, parallel)──▶ review_employee
                                                        └─▶ bell_curve ─▶ report ─▶ END
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

try:  # langgraph >= 0.2.60
    from langgraph.types import Send
except ImportError:  # pragma: no cover - older langgraph
    from langgraph.constants import Send

from .agents import review_employee as run_review
from .bell_curve import apply_bell_curve
from .data_loader import group_by_employee, load_feedback
from .report import print_console_summary, write_excel_report


class AppState(TypedDict, total=False):
    input_path: str
    employees: dict[str, dict]
    results: Annotated[dict[str, dict], operator.or_]  # merged across parallel Sends
    final_ratings: list[dict]
    report_paths: dict[str, str]


def build_app(cfg: dict, llm: Any, output_dir: str):
    weights: dict[str, float] = cfg.get("weights", {})
    bands: list[dict] = cfg["bell_curve"]["bands"]

    # ------------------------------------------------------------------ nodes
    def load_data(state: AppState) -> dict:
        records = load_feedback(state["input_path"])
        employees = group_by_employee(records)
        print(f"[load_data] {len(records)} feedback rows for {len(employees)} employees")
        return {"employees": employees}

    def fan_out(state: AppState):
        return [
            Send("review_employee", {"employee": emp})
            for emp in state["employees"].values()
        ]

    def review_node(state: dict) -> dict:
        emp = state["employee"]
        result = run_review(emp, llm, weights)
        print(
            f"[review] {result['employee_name']:<25} composite {result['composite_score']}"
            + (f"  (missing: {', '.join(result['missing_sources'])})" if result["missing_sources"] else "")
        )
        return {"results": {result["employee_id"]: result}}

    def bell_curve_node(state: AppState) -> dict:
        finals = apply_bell_curve(state["results"], bands)
        print(f"[bell_curve] fitted {len(finals)} employees into {len(bands)} bands")
        return {"final_ratings": [f.model_dump() for f in finals]}

    def report_node(state: AppState) -> dict:
        paths = write_excel_report(state["final_ratings"], state["results"], bands, output_dir)
        print_console_summary(state["final_ratings"], bands, paths["excel"])
        return {"report_paths": paths}

    # ------------------------------------------------------------------ graph
    g = StateGraph(AppState)
    g.add_node("load_data", load_data)
    g.add_node("review_employee", review_node)
    g.add_node("bell_curve", bell_curve_node)
    g.add_node("report", report_node)

    g.add_edge(START, "load_data")
    g.add_conditional_edges("load_data", fan_out, ["review_employee"])
    g.add_edge("review_employee", "bell_curve")
    g.add_edge("bell_curve", "report")
    g.add_edge("report", END)
    return g.compile()
