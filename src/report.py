"""Excel + console reporting."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rich.console import Console
from rich.table import Table

from .schemas import REVIEWER_ROLES

console = Console()

_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_BAND_FILLS = {
    "Exceeds Expectations": PatternFill("solid", fgColor="C6EFCE"),
    "Meets Expectations": PatternFill("solid", fgColor="FFEB9C"),
    "Below Expectations": PatternFill("solid", fgColor="FFC7CE"),
}
_FALLBACK_FILLS = ["C6EFCE", "D9E1F2", "FFEB9C", "FCE4D6", "FFC7CE"]


def _band_fill(band: str, band_order: list[str]) -> PatternFill:
    if band in _BAND_FILLS:
        return _BAND_FILLS[band]
    idx = band_order.index(band) if band in band_order else 0
    return PatternFill("solid", fgColor=_FALLBACK_FILLS[idx % len(_FALLBACK_FILLS)])


def _style_sheet(ws, widths: dict[int, int]) -> None:
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def _add_bell_curve_chart(wb, df_dist: pd.DataFrame, band_order: list[str]) -> None:
    """Create a bell curve visualization chart on a new sheet."""
    ws_chart = wb.create_sheet("Bell Curve Chart")
    
    # Write header
    ws_chart["A1"] = "Rating Band"
    ws_chart["B1"] = "Target %"
    ws_chart["C1"] = "Actual %"
    for cell in ws_chart[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    
    # Write data rows
    for idx, row in df_dist.iterrows():
        ws_chart[f"A{idx+2}"] = row["Rating Band"]
        ws_chart[f"B{idx+2}"] = row["Target %"]
        ws_chart[f"C{idx+2}"] = row["Actual %"]
    
    # Set column widths
    ws_chart.column_dimensions["A"].width = 25
    ws_chart.column_dimensions["B"].width = 12
    ws_chart.column_dimensions["C"].width = 12
    
    # Create bar chart
    chart = BarChart()
    chart.type = "col"  # Column chart
    chart.title = "Bell Curve Distribution: Target vs Actual"
    chart.x_axis.title = "Rating Band"
    chart.y_axis.title = "Percentage (%)"
    
    # Add data to chart
    data = Reference(ws_chart, min_col=2, min_row=1, max_col=3, max_row=len(df_dist)+1)
    categories = Reference(ws_chart, min_col=1, min_row=2, max_row=len(df_dist)+1)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)
    
    # Color the bars by band
    chart.height = 12
    chart.width = 18
    
    # Add chart to sheet
    ws_chart.add_chart(chart, "A6")


def _add_histogram_chart(wb, df_ratings: pd.DataFrame) -> None:
    """Create a histogram chart of composite scores on a new sheet."""
    if df_ratings.empty:
        return

    ws = wb.create_sheet("Bell Curve Histogram")
    scores = df_ratings["Composite Score"].astype(float)
    bins = pd.cut(scores, bins=7, include_lowest=True)
    hist = bins.value_counts(sort=False)

    ws["A1"] = "Score Bin"
    ws["B1"] = "Count"
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    for idx, (interval, count) in enumerate(hist.items(), start=2):
        ws[f"A{idx}"] = f"{interval.left:.2f}–{interval.right:.2f}"
        ws[f"B{idx}"] = int(count)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 12

    data = Reference(ws, min_col=2, min_row=1, max_row=len(hist) + 1)
    cats = Reference(ws, min_col=1, min_row=2, max_row=len(hist) + 1)

    bar = BarChart()
    bar.type = "col"
    bar.title = "Composite Score Histogram"
    bar.x_axis.title = "Score Bin"
    bar.y_axis.title = "Count"
    bar.add_data(data, titles_from_data=True)
    bar.set_categories(cats)
    bar.width = 18
    bar.height = 12

    line = LineChart()
    line.title = "Score Trend"
    line.style = 12
    line.y_axis.title = "Count"
    line.add_data(data, titles_from_data=True)
    line.set_categories(cats)
    line.smooth = True
    line.y_axis.crosses = "min"

    bar += line
    ws.add_chart(bar, "D5")


def write_excel_report(
    final_ratings: list[dict],
    results: dict[str, dict],
    bands: list[dict],
    output_dir: str,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "yearend_review_report.xlsx"
    band_order = [b["band"] for b in bands]

    # ---- Sheet 1: Final Ratings -------------------------------------------
    rating_rows = []
    for f in final_ratings:
        rating_rows.append({
            "Employee ID": f["employee_id"],
            "Employee Name": f["employee_name"],
            "Role": f.get("employee_role", ""),
            **{f"{r} Score": f["source_scores"].get(r, "—") for r in REVIEWER_ROLES},
            "Composite Score": f["composite_score"],
            "Percentile": f["percentile"],
            "Rating Band": f["band"],
            "Final Rating": f["rating"],
        })
    df_ratings = pd.DataFrame(rating_rows)

    # ---- Sheet 2: Comparative Feedback ------------------------------------
    df_feedback = pd.DataFrame([
        {
            "Employee ID": f["employee_id"],
            "Employee Name": f["employee_name"],
            "Comparative Feedback": f["comparative_feedback"],
            "Key Themes": "; ".join(f["key_themes"]),
            "Consistency Flags": "\n".join(f["consistency_flags"]) or "None",
        }
        for f in final_ratings
    ])

    # ---- Sheet 3: Source Analysis -----------------------------------------
    src_rows = []
    for f in final_ratings:
        for role, a in results[f["employee_id"]]["source_analyses"].items():
            src_rows.append({
                "Employee ID": f["employee_id"],
                "Employee Name": f["employee_name"],
                "Source": role,
                "Score": a["score"],
                "Sentiment": a["sentiment"],
                "Confidence": a["confidence"],
                "Summary": a["summary"],
                "Strengths": "; ".join(a["strengths"]),
                "Concerns": "; ".join(a["concerns"]),
            })
    df_sources = pd.DataFrame(src_rows)

    # ---- Sheet 4: Distribution check ---------------------------------------
    n = len(final_ratings)
    dist_rows = []
    prev = 0.0
    for b in bands:
        target = float(b["top_pct"]) - prev
        prev = float(b["top_pct"])
        count = sum(1 for f in final_ratings if f["band"] == b["band"])
        dist_rows.append({
            "Rating Band": b["band"],
            "Rating": b["rating"],
            "Target %": round(target, 1),
            "Actual %": round(100.0 * count / n, 1) if n else 0.0,
            "Headcount": count,
        })
    df_dist = pd.DataFrame(dist_rows)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_ratings.to_excel(writer, sheet_name="Final Ratings", index=False)
        df_feedback.to_excel(writer, sheet_name="Comparative Feedback", index=False)
        df_sources.to_excel(writer, sheet_name="Source Analysis", index=False)
        df_dist.to_excel(writer, sheet_name="Distribution", index=False)

        wb = writer.book
        _style_sheet(wb["Final Ratings"], {1: 12, 2: 22, 3: 18, 4: 12, 5: 14, 6: 10, 7: 14, 8: 11, 9: 22, 10: 12})
        _style_sheet(wb["Comparative Feedback"], {1: 12, 2: 22, 3: 90, 4: 40, 5: 50})
        _style_sheet(wb["Source Analysis"], {1: 12, 2: 22, 3: 16, 4: 8, 5: 11, 6: 12, 7: 60, 8: 50, 9: 50})
        _style_sheet(wb["Distribution"], {1: 24, 2: 9, 3: 10, 4: 10, 5: 11})

        ws = wb["Final Ratings"]
        band_col = list(df_ratings.columns).index("Rating Band") + 1
        for row in range(2, ws.max_row + 1):
            band = ws.cell(row=row, column=band_col).value
            fill = _band_fill(band, band_order)
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col).fill = fill

        # ---- Add Bell Curve Chart Sheets -----------------------------------
        _add_bell_curve_chart(wb, df_dist, band_order)
        _add_histogram_chart(wb, df_ratings)

    return {"excel": str(path)}


def print_console_summary(final_ratings: list[dict], bands: list[dict], excel_path: str) -> None:
    band_order = [b["band"] for b in bands]
    style_map = {"Exceeds Expectations": "green", "Meets Expectations": "yellow",
                 "Below Expectations": "red"}

    table = Table(title="Year-End Review — Final Ratings", header_style="bold cyan")
    for col in ("ID", "Name", "PM", "AM", "HR", "Composite", "Pctile", "Band", "Rating"):
        table.add_column(col, justify="center" if col not in {"Name", "Band"} else "left")
    for f in final_ratings:
        s = f["source_scores"]
        table.add_row(
            f["employee_id"], f["employee_name"],
            str(s.get("People Manager", "—")), str(s.get("Account Manager", "—")),
            str(s.get("HR", "—")),
            f"{f['composite_score']:.2f}", f"{f['percentile']:.0f}",
            f"[{style_map.get(f['band'], 'white')}]{f['band']}[/]",
            str(f["rating"]),
        )
    console.print(table)

    dist = Table(title="Bell-Curve Distribution Check", header_style="bold magenta")
    for col in ("Band", "Target %", "Actual %", "Headcount"):
        dist.add_column(col, justify="center")
    prev = 0.0
    n = len(final_ratings)
    for b in bands:
        target = float(b["top_pct"]) - prev
        prev = float(b["top_pct"])
        count = sum(1 for f in final_ratings if f["band"] == b["band"])
        dist.add_row(b["band"], f"{target:.0f}", f"{100.0 * count / n:.1f}" if n else "0", str(count))
    console.print(dist)

    flagged = [f for f in final_ratings if f["consistency_flags"]]
    if flagged:
        console.print("\n[bold red]Consistency flags for calibration panel:[/]")
        for f in flagged:
            for flag in f["consistency_flags"]:
                console.print(f"  • {f['employee_name']}: {flag}")

    console.print(f"\n[bold green]Excel report written to:[/] {excel_path}")
