"""
pipeline/extract.py
────────────────────
Extraction layer — reads raw CSV files into pandas DataFrames.
"""

import os
import pandas as pd


# ── Where raw files live ─────────────────────────────────────
RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw")


def extract_csv(filename: str) -> pd.DataFrame:
    """
    Read a single CSV file from the raw data directory.
    """
    path = os.path.join(RAW_DIR, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Source file not found: {path}\n"
            f"Run 'python scripts/generate_data.py' first."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"Source file is empty: {path}")

    print(f"  [extract] {filename:<30} {len(df):>4} rows extracted")
    return df


def extract_vehicle_locations() -> pd.DataFrame:
    return extract_csv("vehicle_locations.csv")


def extract_passenger_counts() -> pd.DataFrame:
    return extract_csv("passenger_counts.csv")


def extract_weather_conditions() -> pd.DataFrame:
    return extract_csv("weather_conditions.csv")