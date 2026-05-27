"""
tests/test_transform.py
────────────────────────
Unit tests for pipeline/transform.py.

Run with:
    pytest tests/test_transform.py -v
"""

import pandas as pd
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.transform import (
    transform_vehicle_locations,
    transform_passenger_counts,
    transform_weather_conditions,
)


# ════════════════════════════════════════════════════════════
# FIXTURES — minimal DataFrames with known quality issues
# ════════════════════════════════════════════════════════════

@pytest.fixture
def vehicle_df():
    """Raw vehicle DataFrame with one of every quality issue."""
    return pd.DataFrame([
        # Good row
        {"vehicle_id": "VH_001", "route_id": "Route_A", "timestamp": "2026-05-26 08:00:00",
         "latitude": 6.52, "longitude": 3.38, "speed_kmh": 40.0, "heading": 90, "status": "in_service"},
        # Duplicate of first row
        {"vehicle_id": "VH_001", "route_id": "Route_A", "timestamp": "2026-05-26 08:00:00",
         "latitude": 6.52, "longitude": 3.38, "speed_kmh": 40.0, "heading": 90, "status": "in_service"},
        # Missing GPS
        {"vehicle_id": "VH_002", "route_id": "Route_B", "timestamp": "2026-05-26 08:05:00",
         "latitude": None, "longitude": None, "speed_kmh": 30.0, "heading": 180, "status": "in_service"},
        # Negative speed
        {"vehicle_id": "VH_003", "route_id": "Route_C", "timestamp": "2026-05-26 08:10:00",
         "latitude": 6.53, "longitude": 3.39, "speed_kmh": -15.0, "heading": 0, "status": "in_service"},
        # Null status
        {"vehicle_id": "VH_004", "route_id": "Route_A", "timestamp": "2026-05-26 08:15:00",
         "latitude": 6.55, "longitude": 3.37, "speed_kmh": 55.0, "heading": 270, "status": None},
        # Coordinates outside Lagos bounding box
        {"vehicle_id": "VH_005", "route_id": "Route_D", "timestamp": "2026-05-26 08:20:00",
         "latitude": 9.00, "longitude": 7.50, "speed_kmh": 20.0, "heading": 45, "status": "in_service"},
    ])


@pytest.fixture
def passenger_df():
    """Raw passenger DataFrame with one of every quality issue."""
    return pd.DataFrame([
        # Good row
        {"trip_id": "TRP_001", "vehicle_id": "VH_001", "stop_id": "STOP_01",
         "route_id": "Route_A", "timestamp": "2026-05-26 08:00:00",
         "boarded": 10, "alighted": 5, "current_load": 20, "capacity": 60},
        # Boarded as string (wrong type from source)
        {"trip_id": "TRP_002", "vehicle_id": "VH_002", "stop_id": "STOP_02",
         "route_id": "Route_B", "timestamp": "2026-05-26 08:05:00",
         "boarded": "15", "alighted": 3, "current_load": 18, "capacity": 60},
        # Null boarded — sensor offline
        {"trip_id": "TRP_003", "vehicle_id": "VH_003", "stop_id": "STOP_03",
         "route_id": "Route_C", "timestamp": "2026-05-26 08:10:00",
         "boarded": None, "alighted": 2, "current_load": 10, "capacity": 60},
        # Negative alighted — data entry mistake
        {"trip_id": "TRP_004", "vehicle_id": "VH_004", "stop_id": "STOP_04",
         "route_id": "Route_A", "timestamp": "2026-05-26 08:15:00",
         "boarded": 8, "alighted": -3, "current_load": 25, "capacity": 60},
        # current_load > capacity — manual entry error
        {"trip_id": "TRP_005", "vehicle_id": "VH_005", "stop_id": "STOP_05",
         "route_id": "Route_B", "timestamp": "2026-05-26 08:20:00",
         "boarded": 5, "alighted": 2, "current_load": 80, "capacity": 60},
    ])


@pytest.fixture
def weather_df():
    """Raw weather DataFrame with one of every quality issue."""
    return pd.DataFrame([
        # Good row
        {"reading_id": "WTH_001", "station": "Ikeja", "timestamp": "2026-05-26 07:00:00",
         "condition": "Clear", "temperature_c": 28.5, "humidity_pct": 70,
         "wind_speed_kmh": 12.0, "rainfall_mm": 0.0},
        # Null temperature — station offline
        {"reading_id": "WTH_002", "station": "Lekki", "timestamp": "2026-05-26 08:00:00",
         "condition": "Cloudy", "temperature_c": None, "humidity_pct": 75,
         "wind_speed_kmh": 8.0, "rainfall_mm": 0.0},
        # Humidity > 100 — sensor spike
        {"reading_id": "WTH_003", "station": "Yaba", "timestamp": "2026-05-26 09:00:00",
         "condition": "Rainy", "temperature_c": 25.0, "humidity_pct": 120,
         "wind_speed_kmh": 20.0, "rainfall_mm": 5.0},
        # Negative rainfall — sensor error
        {"reading_id": "WTH_004", "station": "Surulere", "timestamp": "2026-05-26 10:00:00",
         "condition": "Stormy", "temperature_c": 24.0, "humidity_pct": 85,
         "wind_speed_kmh": 30.0, "rainfall_mm": -2.5},
        # Null condition
        {"reading_id": "WTH_005", "station": "Ikeja", "timestamp": "2026-05-26 11:00:00",
         "condition": None, "temperature_c": 30.0, "humidity_pct": 60,
         "wind_speed_kmh": 5.0, "rainfall_mm": 0.0},
    ])


# ════════════════════════════════════════════════════════════
# VEHICLE LOCATION TESTS
# ════════════════════════════════════════════════════════════

class TestTransformVehicleLocations:

    def test_removes_duplicate_rows(self, vehicle_df):
        """VH_001 appears twice — only one should remain."""
        clean = transform_vehicle_locations(vehicle_df)
        vh001_rows = clean[clean["vehicle_id"] == "VH_001"]
        assert len(vh001_rows) == 1

    def test_rejects_missing_gps(self, vehicle_df):
        """VH_002 has null lat/lon — must not appear in clean output."""
        clean = transform_vehicle_locations(vehicle_df)
        assert "VH_002" not in clean["vehicle_id"].values

    def test_clips_negative_speed_to_zero(self, vehicle_df):
        """VH_003 has speed -15 — must be clipped to 0, not dropped."""
        clean = transform_vehicle_locations(vehicle_df)
        vh003 = clean[clean["vehicle_id"] == "VH_003"]
        assert len(vh003) == 1
        assert vh003.iloc[0]["speed_kmh"] == 0.0

    def test_fills_null_status_with_unknown(self, vehicle_df):
        """VH_004 has null status — must be filled with 'unknown'."""
        clean = transform_vehicle_locations(vehicle_df)
        vh004 = clean[clean["vehicle_id"] == "VH_004"]
        assert vh004.iloc[0]["status"] == "unknown"

    def test_rejects_coordinates_outside_lagos(self, vehicle_df):
        """VH_005 is in Abuja (lat 9.0) — must be rejected."""
        clean = transform_vehicle_locations(vehicle_df)
        assert "VH_005" not in clean["vehicle_id"].values

    def test_timestamp_parsed_to_datetime(self, vehicle_df):
        """Timestamp column must be datetime dtype after transform."""
        clean = transform_vehicle_locations(vehicle_df)
        assert pd.api.types.is_datetime64_any_dtype(clean["timestamp"])

    def test_no_negative_speeds_in_output(self, vehicle_df):
        """All speed values in clean output must be >= 0."""
        clean = transform_vehicle_locations(vehicle_df)
        assert (clean["speed_kmh"] >= 0).all()

    def test_output_smaller_than_input(self, vehicle_df):
        """Clean output must have fewer rows than raw input (rejections)."""
        clean = transform_vehicle_locations(vehicle_df)
        assert len(clean) < len(vehicle_df)


# ════════════════════════════════════════════════════════════
# PASSENGER COUNT TESTS
# ════════════════════════════════════════════════════════════

class TestTransformPassengerCounts:

    def test_rejects_null_boarded(self, passenger_df):
        """TRP_003 has null boarded — must not appear in clean output."""
        clean = transform_passenger_counts(passenger_df)
        assert "TRP_003" not in clean["trip_id"].values

    def test_converts_string_boarded_to_int(self, passenger_df):
        """TRP_002 has boarded='15' (string) — must be cast to integer 15."""
        clean = transform_passenger_counts(passenger_df)
        trp002 = clean[clean["trip_id"] == "TRP_002"]
        assert trp002.iloc[0]["boarded"] == 15
        # numpy int64 is a valid integer type — accept both
        import numpy as np
        assert isinstance(trp002.iloc[0]["boarded"], (int, np.integer))

    def test_clips_negative_alighted_to_zero(self, passenger_df):
        """TRP_004 has alighted=-3 — must be clipped to 0."""
        clean = transform_passenger_counts(passenger_df)
        trp004 = clean[clean["trip_id"] == "TRP_004"]
        assert trp004.iloc[0]["alighted"] == 0

    def test_caps_load_at_capacity(self, passenger_df):
        """TRP_005 has current_load=80 > capacity=60 — must be capped at 60."""
        clean = transform_passenger_counts(passenger_df)
        trp005 = clean[clean["trip_id"] == "TRP_005"]
        assert trp005.iloc[0]["current_load"] == 60

    def test_occupancy_rate_computed(self, passenger_df):
        """occupancy_rate must be added and equal current_load/capacity * 100."""
        clean = transform_passenger_counts(passenger_df)
        assert "occupancy_rate" in clean.columns
        trp001 = clean[clean["trip_id"] == "TRP_001"]
        expected = round((20 / 60) * 100, 2)
        assert trp001.iloc[0]["occupancy_rate"] == expected

    def test_occupancy_rate_between_0_and_100(self, passenger_df):
        """All occupancy_rate values must be within 0–100%."""
        clean = transform_passenger_counts(passenger_df)
        assert clean["occupancy_rate"].between(0, 100).all()

    def test_no_negative_alighted_in_output(self, passenger_df):
        """All alighted values in output must be >= 0."""
        clean = transform_passenger_counts(passenger_df)
        assert (clean["alighted"] >= 0).all()


# ════════════════════════════════════════════════════════════
# WEATHER CONDITION TESTS
# ════════════════════════════════════════════════════════════

class TestTransformWeatherConditions:

    def test_imputes_null_temperature_with_median(self, weather_df):
        """WTH_002 has null temperature — must be filled with column median."""
        clean = transform_weather_conditions(weather_df)
        wth002 = clean[clean["reading_id"] == "WTH_002"]
        assert wth002.iloc[0]["temperature_c"] is not None
        assert not pd.isna(wth002.iloc[0]["temperature_c"])

    def test_clips_humidity_above_100(self, weather_df):
        """WTH_003 has humidity=120 — must be clipped to 100."""
        clean = transform_weather_conditions(weather_df)
        wth003 = clean[clean["reading_id"] == "WTH_003"]
        assert wth003.iloc[0]["humidity_pct"] == 100

    def test_clips_negative_rainfall_to_zero(self, weather_df):
        """WTH_004 has rainfall=-2.5 — must be clipped to 0."""
        clean = transform_weather_conditions(weather_df)
        wth004 = clean[clean["reading_id"] == "WTH_004"]
        assert wth004.iloc[0]["rainfall_mm"] == 0.0

    def test_fills_null_condition_with_unknown(self, weather_df):
        """WTH_005 has null condition — must be filled with 'Unknown'."""
        clean = transform_weather_conditions(weather_df)
        wth005 = clean[clean["reading_id"] == "WTH_005"]
        assert wth005.iloc[0]["condition"] == "Unknown"

    def test_no_null_temperatures_in_output(self, weather_df):
        """All temperature values must be non-null after imputation."""
        clean = transform_weather_conditions(weather_df)
        assert clean["temperature_c"].isna().sum() == 0

    def test_humidity_within_valid_range(self, weather_df):
        """All humidity values must be between 0 and 100."""
        clean = transform_weather_conditions(weather_df)
        assert clean["humidity_pct"].between(0, 100).all()

    def test_no_negative_rainfall_in_output(self, weather_df):
        """All rainfall values must be >= 0."""
        clean = transform_weather_conditions(weather_df)
        assert (clean["rainfall_mm"] >= 0).all()

    def test_row_count_unchanged(self, weather_df):
        """Weather transform imputes/clips — no rows should be dropped."""
        clean = transform_weather_conditions(weather_df)
        assert len(clean) == len(weather_df)