"""CLI entry point for the Year-End Review Agent.

Examples
--------
# Offline demo with deterministic stub (no API key needed):
    python main.py --make-sample --dry-run

# Real run against your own data:
    python main.py --input my_feedback.xlsx
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_SAMPLE = Path("sample_data") / "feedback_input.xlsx"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Agentic year-end employee review & bell-curve rating pipeline."
    )
    p.add_argument("--input", help="Path to feedback file (.xlsx/.xls/.csv)")
    p.add_argument("--config", default="config.yaml", help="YAML config (default: config.yaml)")
    p.add_argument("--output", default="output", help="Output directory (default: output)")
    p.add_argument("--make-sample", action="store_true",
                   help="Generate a sample input workbook before running")
    p.add_argument("--dry-run", action="store_true",
                   help="Run with a deterministic stub instead of a real LLM (no API key needed)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()

    if args.make_sample:
        from src.sample_data import create_sample
        create_sample(args.input or DEFAULT_SAMPLE)

    input_path = args.input or (str(DEFAULT_SAMPLE) if DEFAULT_SAMPLE.exists() else None)
    if not input_path:
        sys.exit("No --input given and no sample found. Use --make-sample to create one.")

    if not args.dry_run and not os.environ.get("OPENAI_API_KEY"):
        sys.exit(
            "OPENAI_API_KEY is not set. Add it to a .env file (see .env.example), "
            "or run with --dry-run for an offline demo."
        )

    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    from src.graph import build_app
    from src.llm import build_llm

    llm = build_llm(cfg, dry_run=args.dry_run)
    app = build_app(cfg, llm, args.output)
    app.invoke({"input_path": input_path})


if __name__ == "__main__":
    main()
