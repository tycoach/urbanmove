"""
pipeline/transform.py
──────────────────────
Transformation layer — cleans and standardises raw DataFrames.
"""

import os
import pandas as pd
from datetime import datetime


REJECTED_DIR = os.path.join(os.path.dirname(__file__), "../data/rejected")
os.makedirs(REJECTED_DIR, exist_ok=True)


# ── Helper: save rejected rows to CSV ────────────────────────

def _save_rejected(df: pd.DataFrame, dataset: str) -> None:
    """Write rejected rows to data/rejected/ with a timestamp."""
    if df.empty:
        return
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REJECTED_DIR, f"{dataset}_rejected_{ts}.csv")
    df.to_csv(path, index=False)
    print(f"  [transform] {len(df)} rejected rows saved → {os.path.basename(path)}")


# ════════════════════════════════════════════════════════════
#  VEHICLE LOCATIONS
# ════════════════════════════════════════════════════════════

def transform_vehicle_locations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw vehicle location records.

    """
    raw_count = len(df)
    rejected  = []

    #  Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    #  Drop duplicates — keep first occurrence
    before = len(df)
    df = df.drop_duplicates(subset=["vehicle_id", "timestamp"], keep="first")
    dupes = before - len(df)
    if dupes:
        print(f"  [transform] vehicle_locations: {dupes} duplicate rows removed")

    #  Rows with missing GPS — reject entirely, cannot impute coordinates
    mask_no_gps = df["latitude"].isna() | df["longitude"].isna()
    rejected.append(df[mask_no_gps].copy().assign(_rejection_reason="missing GPS coordinates"))
    df = df[~mask_no_gps]

    #  Negative speed — clip to 0 (sensor malfunction, not a real value)
    negative_speed = df["speed_kmh"] < 0
    if negative_speed.any():
        print(f"  [transform] vehicle_locations: {negative_speed.sum()} negative speeds clipped to 0")
    df["speed_kmh"] = df["speed_kmh"].clip(lower=0)

    #  Fill null status
    df["status"] = df["status"].fillna("unknown")

    #  Validate coordinates within Lagos bounding box
    mask_bad_coords = ~(
        df["latitude"].between(6.40, 6.70) &
        df["longitude"].between(3.20, 3.60)
    )
    rejected.append(df[mask_bad_coords].copy().assign(_rejection_reason="coordinates outside Lagos bounding box"))
    df = df[~mask_bad_coords]

    # Collect and save all rejected rows
    rejected_df = pd.concat([r for r in rejected if not r.empty], ignore_index=True)
    _save_rejected(rejected_df, "vehicle_locations")

    print(
        f"  [transform] vehicle_locations: "
        f"{raw_count} in → {len(df)} clean, {len(rejected_df)} rejected"
    )
    return df.reset_index(drop=True)


# ════════════════════════════════════════════════════════════
#  PASSENGER COUNTS
# ════════════════════════════════════════════════════════════

def transform_passenger_counts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw passenger count records.

    """
    raw_count = len(df)
    rejected  = []

    # Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    #  Fix data type — boarded may be stored as string "12"
    df["boarded"] = pd.to_numeric(df["boarded"], errors="coerce")

    # Drop rows where boarded is null — core metric, cannot impute
    mask_null_boarded = df["boarded"].isna()
    rejected.append(df[mask_null_boarded].copy().assign(_rejection_reason="null boarded count"))
    df = df[~mask_null_boarded].copy()  # .copy() prevents SettingWithCopyWarning

    #  Cast to integer now that nulls are removed
    df["boarded"]  = df["boarded"].astype(int)
    df["alighted"] = df["alighted"].astype(int)

    #  Clip negative alighted to 0 — data entry mistake
    negative_alighted = df["alighted"] < 0
    if negative_alighted.any():
        print(f"  [transform] passenger_counts: {negative_alighted.sum()} negative alighted values clipped to 0")
    df["alighted"] = df["alighted"].clip(lower=0)

    #  Clip current_load to capacity maximum
    overloaded = df["current_load"] > df["capacity"]
    if overloaded.any():
        print(f"  [transform] passenger_counts: {overloaded.sum()} current_load values capped at capacity")
    df["current_load"] = df[["current_load", "capacity"]].min(axis=1)

    #  Compute occupancy rate as a percentage
    df["occupancy_rate"] = ((df["current_load"] / df["capacity"]) * 100).round(2)

    # Collect and save rejected rows
    rejected_df = pd.concat([r for r in rejected if not r.empty], ignore_index=True)
    _save_rejected(rejected_df, "passenger_counts")

    print(
        f"  [transform] passenger_counts: "
        f"{raw_count} in → {len(df)} clean, {len(rejected_df)} rejected"
    )
    return df.reset_index(drop=True)


# ════════════════════════════════════════════════════════════
#  WEATHER CONDITIONS
# ════════════════════════════════════════════════════════════

def transform_weather_conditions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw weather condition records.
    """
    raw_count = len(df)

    #  Parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    #  Impute null temperature with column median
    null_temp_count = df["temperature_c"].isna().sum()
    if null_temp_count:
        median_temp = df["temperature_c"].median()
        df["temperature_c"] = df["temperature_c"].fillna(median_temp)
        print(
            f"  [transform] weather_conditions: "
            f"{null_temp_count} null temperatures imputed with median ({median_temp}°C)"
        )

    #  Clip humidity to valid range 0–100
    invalid_humidity = (df["humidity_pct"] < 0) | (df["humidity_pct"] > 100)
    if invalid_humidity.any():
        print(f"  [transform] weather_conditions: {invalid_humidity.sum()} invalid humidity values clipped to 0–100")
    df["humidity_pct"] = df["humidity_pct"].clip(lower=0, upper=100)

    #  Clip negative rainfall to 0
    negative_rain = df["rainfall_mm"] < 0
    if negative_rain.any():
        print(f"  [transform] weather_conditions: {negative_rain.sum()} negative rainfall values clipped to 0")
    df["rainfall_mm"] = df["rainfall_mm"].clip(lower=0)

    #  Fill null condition label
    df["condition"] = df["condition"].fillna("Unknown")

    print(
        f"  [transform] weather_conditions: "
        f"{raw_count} in → {len(df)} clean, 0 rejected"
    )
    return df.reset_index(drop=True)