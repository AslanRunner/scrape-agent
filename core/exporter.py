"""Export utility for ScrapeAgent (CSV and JSON output)."""
import csv
import json
import os
from typing import Sequence


def export_data(data: Sequence[dict], output_path: str) -> str:
    """
    Export data to CSV or JSON based on file extension.

    Args:
        data: List of extracted dictionaries.
        output_path: Target file path (.csv or .json).

    Returns:
        Absolute path to the created file.
    """
    if not data:
        raise ValueError("Cannot export empty dataset.")

    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)

    if output_path.lower().endswith(".json"):
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        # Default to CSV
        fieldnames = list(dict.fromkeys(k for row in data for k in row.keys()))
        with open(abs_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    return abs_path
