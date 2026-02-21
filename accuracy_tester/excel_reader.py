"""
accuracy_tester/excel_reader.py

Reads an Excel file that conforms to the Shelf Analyzer 2.0 output schema and
returns a list of row dicts keyed by the JSON column keys defined in COLUMN_SCHEMA.

Works with both:
  - Ground-truth files (manually verified .xlsx)
  - Generated files (produced by modules/excel_generator.py)

Both are expected to have the same header row ("SKU Data" sheet, or first sheet).
Column matching is done by header name (case-insensitive, whitespace-stripped),
so minor header variations don't break the reader.
"""

from __future__ import annotations

import io
from typing import Union

import pandas as pd

# Import the canonical column schema so we can map display names → JSON keys
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import COLUMN_SCHEMA


# Build a lookup: normalised display name → JSON key
_NAME_TO_KEY: dict[str, str] = {
    col["name"].strip().lower(): col["key"]
    for col in COLUMN_SCHEMA
}

# Columns that are Excel formulas — their values in the file may be cached
# numbers or empty; we include them but flag them separately.
FORMULA_COLUMNS: set[str] = {"price_per_liter_eur"}

# Metadata columns (user-supplied, not AI output) — excluded from accuracy scoring
METADATA_COLUMNS: set[str] = {
    "country", "city", "retailer", "store_format",
    "store_name", "shelf_location", "currency",
}


def read_excel(source: Union[bytes, str, io.BytesIO]) -> list[dict]:
    """
    Read a Shelf Analyzer Excel file and return a list of row dicts.

    Each dict is keyed by the JSON key from COLUMN_SCHEMA (e.g. "brand",
    "facings", "price_local"). Missing columns get None values. Cells
    containing Excel formulas are returned as-is (pandas reads cached values).

    Args:
        source: Raw bytes, a file path string, or a BytesIO object.

    Returns:
        List of dicts, one per data row. Empty list if the sheet has no data rows.

    Raises:
        ValueError: If the file cannot be parsed or has no recognisable headers.
    """
    if isinstance(source, bytes):
        source = io.BytesIO(source)

    try:
        # Use openpyxl engine (already a project dependency).
        # data_only=True makes openpyxl return cached formula values instead of
        # formula strings (e.g. =IFERROR(...) becomes the last computed number).
        df = pd.read_excel(
            source,
            sheet_name=0,       # First sheet (covers both "SKU Data" and any name)
            engine="openpyxl",
            dtype=str,           # Read everything as string first; we normalise below
            na_values=["", "NA", "N/A", "None", "none", "null"],
            keep_default_na=True,
        )
    except Exception as exc:
        raise ValueError(f"Could not read Excel file: {exc}") from exc

    if df.empty:
        return []

    # --- Map header names to JSON keys ---
    column_map: dict[str, str] = {}  # original df column name → JSON key
    unrecognised: list[str] = []

    for col_name in df.columns:
        normalised = str(col_name).strip().lower()
        if normalised in _NAME_TO_KEY:
            column_map[col_name] = _NAME_TO_KEY[normalised]
        else:
            unrecognised.append(col_name)

    if not column_map:
        raise ValueError(
            "No recognisable column headers found. "
            "Make sure the file was produced by Shelf Analyzer 2.0."
        )

    # Rename columns to JSON keys, drop unrecognised ones
    df = df.rename(columns=column_map)
    df = df[[k for k in column_map.values()]]  # keep only known columns, in schema order

    # --- Ensure every JSON key is present (fill missing columns with None) ---
    all_keys = [col["key"] for col in COLUMN_SCHEMA]
    for key in all_keys:
        if key not in df.columns:
            df[key] = None

    df = df[all_keys]  # enforce canonical column order

    # --- Type coercion: convert numeric columns from string back to numbers ---
    for col_spec in COLUMN_SCHEMA:
        key = col_spec["key"]
        col_type = col_spec["type"]

        if col_type == "integer":
            df[key] = pd.to_numeric(df[key], errors="coerce").apply(
                lambda x: int(x) if pd.notna(x) else None
            )
        elif col_type == "float":
            df[key] = pd.to_numeric(df[key], errors="coerce").apply(
                lambda x: float(x) if pd.notna(x) else None
            )
        else:
            # text: strip whitespace, convert NaN → None
            df[key] = df[key].apply(
                lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else None
            )

    # Drop rows where every cell is None (completely blank rows)
    df = df.dropna(how="all")

    return df.to_dict(orient="records")


def get_comparable_columns() -> list[dict]:
    """
    Return the subset of COLUMN_SCHEMA columns that are used in accuracy scoring.

    Excluded:
    - Metadata columns (user-supplied, not Claude output)
    - Formula column (price_per_liter_eur — Excel-computed, not in JSON)
    """
    return [
        col for col in COLUMN_SCHEMA
        if col["key"] not in METADATA_COLUMNS
        and col["key"] not in FORMULA_COLUMNS
    ]
