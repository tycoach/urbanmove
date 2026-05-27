
"""
pipeline/validate.py
─────────────────────
Validation layer — quality gate between transform and load.
"""

import pandas as pd


class ValidationError(Exception):
    """Raised when a dataset fails a quality check."""
    pass


def _check(condition: bool, message: str) -> None:
    """Fail loudly with a clear message if a check doesn't pass."""
    if not condition:
        raise ValidationError(message)


# ════════════════════════════════════════════════════════════
#  VEHICLE LOCATIONS
# ════════════════════════════════════════════════════════════

def validate_vehicle_locations(df: pd.DataFrame) -> None:
    """
    Quality checks for cleaned vehicle location data.
    """
    print(f"  [validate] vehicle_locations: running checks on {len(df)} rows...")

    # ----- Not empty
    _check(
        len(df) > 0,
        "vehicle_locations: DataFrame is empty after transformation"
    )

    # ----- No nulls in critical columns
    critical = ["vehicle_id", "route_id", "timestamp", "latitude", "longitude"]
    for col in critical:
        null_count = df[col].isna().sum()
        _check(
            null_count == 0,
            f"vehicle_locations: {null_count} null values found in critical column '{col}'"
        )

    # ---- No negative speeds
    negative_speeds = (df["speed_kmh"] < 0).sum()
    _check(
        negative_speeds == 0,
        f"vehicle_locations: {negative_speeds} rows still have negative speed_kmh"
    )

    #----- Coordinates within Lagos bounding box
    bad_coords = ~(
        df["latitude"].between(6.40, 6.70) &
        df["longitude"].between(3.20, 3.60)
    )
    _check(
        bad_coords.sum() == 0,
        f"vehicle_locations: {bad_coords.sum()} rows have coordinates outside Lagos bounding box"
    )

    # ---- Minimum row threshold
    if len(df) < 10:
        print(f"  [validate] WARNING: vehicle_locations has only {len(df)} rows — unusually low")

    print(f"  [validate] vehicle_locations: all checks passed ")


# ════════════════════════════════════════════════════════════
#  PASSENGER COUNTS
# ════════════════════════════════════════════════════════════

def validate_passenger_counts(df: pd.DataFrame) -> None:
    """
    Quality checks for cleaned passenger count data.
    """
    print(f"  [validate] passenger_counts: running checks on {len(df)} rows...")

    # --- Not empty
    _check(
        len(df) > 0,
        "passenger_counts: DataFrame is empty after transformation"
    )

    # ---- No nulls in critical columns
    critical = ["trip_id", "vehicle_id", "stop_id", "route_id", "timestamp", "boarded"]
    for col in critical:
        null_count = df[col].isna().sum()
        _check(
            null_count == 0,
            f"passenger_counts: {null_count} null values in critical column '{col}'"
        )

    # ---- No negative counts
    _check(
        (df["boarded"]  >= 0).all(),
        "passenger_counts: negative values found in 'boarded' column"
    )
    _check(
        (df["alighted"] >= 0).all(),
        "passenger_counts: negative values found in 'alighted' column"
    )

    # ---- Load does not exceed capacity
    overloaded = (df["current_load"] > df["capacity"]).sum()
    _check(
        overloaded == 0,
        f"passenger_counts: {overloaded} rows have current_load > capacity"
    )

    # ---- Occupancy rate in valid range
    bad_occupancy = ~df["occupancy_rate"].between(0, 100)
    _check(
        bad_occupancy.sum() == 0,
        f"passenger_counts: {bad_occupancy.sum()} rows have occupancy_rate outside 0–100%"
    )

    print(f"  [validate] passenger_counts: all checks passed ")


# ════════════════════════════════════════════════════════════
#  WEATHER CONDITIONS
# ════════════════════════════════════════════════════════════

def validate_weather_conditions(df: pd.DataFrame) -> None:
    """
    Quality checks for cleaned weather condition data.
    """
    print(f"  [validate] weather_conditions: running checks on {len(df)} rows...")

    # ---- Not empty
    _check(
        len(df) > 0,
        "weather_conditions: DataFrame is empty after transformation"
    )

    # ----- No nulls in critical columns
    critical = ["reading_id", "station", "timestamp", "temperature_c"]
    for col in critical:
        null_count = df[col].isna().sum()
        _check(
            null_count == 0,
            f"weather_conditions: {null_count} null values in critical column '{col}'"
        )

    # ----- Humidity in valid range
    bad_humidity = ~df["humidity_pct"].between(0, 100)
    _check(
        bad_humidity.sum() == 0,
        f"weather_conditions: {bad_humidity.sum()} rows have humidity_pct outside 0–100"
    )

    # ---- No negative rainfall
    _check(
        (df["rainfall_mm"] >= 0).all(),
        "weather_conditions: negative rainfall_mm values found"
    )

    # --- No negative wind speed
    _check(
        (df["wind_speed_kmh"] >= 0).all(),
        "weather_conditions: negative wind_speed_kmh values found"
    )

    print(f"  [validate] weather_conditions: all checks passed ✓")