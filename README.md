# Year-End Review Agent

An agentic Python application that automates year-end employee reviews. It reads
feedback from **People Managers**, **Account Managers**, and **HR**, analyses each
source with dedicated LLM agents, calibrates them into a comparative review, and
fits the whole population into a **bell-curve rating distribution**.

Built with **LangGraph + OpenAI**, reading **Excel/CSV** input and producing a
styled **Excel report + console summary**.

---

## How it works

```
START
  └─ load_data ───────────── reads Excel/CSV, groups rows per employee
        │  (Send: one parallel branch per employee)
        ├─▶ review_employee ─┐
        │    • PM analyst agent      → structured summary + score (1–5)
        │    • AM analyst agent      → structured summary + score (1–5)
        │    • HR analyst agent      → structured summary + score (1–5)
        │    • Calibration agent     → comparative narrative + consistency flags
        │    • composite = weighted avg of source scores (deterministic, in code)
        └─▶ bell_curve ────── ranks by composite score, forces 20/70/10 bands
              └─▶ report ──── styled Excel workbook + console summary → END
```

Design principle: **the LLM writes prose; arithmetic stays in code.** Composite
scores and the bell curve are computed deterministically so every number in the
report is auditable and reproducible.

## Setup

```bash
cd yearend_review_app
pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY
```

## Quick start (no API key needed)

```bash
python main.py --make-sample --dry-run
```

`--dry-run` swaps the LLM for a deterministic heuristic stub with the same
interface, so you can test the whole pipeline offline. Scores will be crude —
use a real key for real reviews.

## Real run

```bash
python main.py --input my_feedback.xlsx            # uses config.yaml + .env key
python main.py --input data.csv --config mycfg.yaml --output reports/
```

### Input format (.xlsx / .xls / .csv)

| employee_id | employee_name | employee_role | reviewer_role  | feedback |
|-------------|---------------|---------------|----------------|----------|
| E001 | Aisha Verma | Senior SWE | People Manager | …text… |
| E001 | Aisha Verma | Senior SWE | Account Manager | …text… |
| E001 | Aisha Verma | Senior SWE | HR | …text… |

- `reviewer_role` must be exactly `People Manager`, `Account Manager`, or `HR`.
- `employee_role` is optional. Column-name variants (`Emp ID`, `Name`, `Source`,
  `Comments`, …) are recognised automatically.
- Missing sources are tolerated: weights are renormalised and a flag is raised.

## Configuration (`config.yaml`)

| Key | Meaning | Default |
|---|---|---|
| `llm.model` | OpenAI chat model | `gpt-4o-mini` |
| `llm.temperature` | Sampling temperature | `0.1` |
| `weights` | Weight per reviewer role (sums to 1.0) | 0.5 / 0.3 / 0.2 |
| `bell_curve.bands` | Ordered bands with cumulative `top_pct` cut-offs and rating values | 20% → 5, next 70% → 3, bottom 10% → 1 |

Edit bands to change the distribution (e.g. 5 bands 10/20/40/20/10).

## Output

**`output/yearend_review_report.xlsx`** with four sheets:

1. **Final Ratings** — per-source scores, composite, percentile, band, final rating (colour-coded by band).
2. **Comparative Feedback** — the calibration agent's narrative, key themes, and consistency flags per employee.
3. **Source Analysis** — full detail of every analyst agent: summary, strengths, concerns, sentiment, confidence, score.
4. **Distribution** — target vs. actual headcount per band for the calibration panel.

The console prints the same ratings table, the distribution check, and every
consistency flag that needs human attention (score divergence > 1.5, missing
feedback, suspected bias).

## Project layout

```
yearend_review_app/
├── main.py               # CLI entry point
├── config.yaml           # model, weights, bell-curve bands
├── requirements.txt
├── .env.example
├── sample_data/          # generated demo input
├── output/               # generated reports
└── src/
    ├── schemas.py        # pydantic models (structured LLM output)
    ├── data_loader.py    # Excel/CSV ingestion + validation
    ├── llm.py            # ChatOpenAI factory + dry-run stub
    ├── agents.py         # analyst & calibration prompts / logic
    ├── graph.py          # LangGraph pipeline (parallel per-employee Sends)
    ├── bell_curve.py     # deterministic distribution fitment
    ├── report.py         # Excel workbook + console summary
    └── sample_data.py    # demo dataset generator
```

## Notes & responsible use

- Ratings are decision **support**, not decision replacement — route the
  consistency flags to a human calibration panel before finalising.
- Employee feedback is personal data: keep the input/output files within your
  organisation's approved storage and review your OpenAI data-usage terms
  (or point `OPENAI_BASE_URL` at an approved Azure/proxy endpoint).
