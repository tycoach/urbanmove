"""
tests/test_validate.py
───────────────────────
Unit tests for pipeline/validate.py.
Run with:
    pytest tests/test_validate.py -v
"""

import pandas as pd
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.validate import (
    validate_vehicle_locations,
    validate_passenger_counts,
    validate_weather_conditions,
    ValidationError,
)


# ════════════════════════════════════════════════════════════
# FIXTURES — clean DataFrames that should pass all checks
# ════════════════════════════════════════════════════════════

@pytest.fixture
def clean_vehicle_df():
    return pd.DataFrame([
        {"vehicle_id": "VH_001", "route_id": "Route_A",
         "timestamp": pd.Timestamp("2026-05-26 08:00:00"),
         "latitude": 6.52, "longitude": 3.38, "speed_kmh": 40.0,
         "heading": 90, "status": "in_service"},
        {"vehicle_id": "VH_002", "route_id": "Route_B",
         "timestamp": pd.Timestamp("2026-05-26 08:05:00"),
         "latitude": 6.55, "longitude": 3.37, "speed_kmh": 55.0,
         "heading": 270, "status": "in_service"},
    ])


@pytest.fixture
def clean_passenger_df():
    return pd.DataFrame([
        {"trip_id": "TRP_001", "vehicle_id": "VH_001", "stop_id": "STOP_01",
         "route_id": "Route_A", "timestamp": pd.Timestamp("2026-05-26 08:00:00"),
         "boarded": 10, "alighted": 5, "current_load": 20,
         "capacity": 60, "occupancy_rate": 33.33},
        {"trip_id": "TRP_002", "vehicle_id": "VH_002", "stop_id": "STOP_02",
         "route_id": "Route_B", "timestamp": pd.Timestamp("2026-05-26 08:05:00"),
         "boarded": 8, "alighted": 3, "current_load": 15,
         "capacity": 60, "occupancy_rate": 25.00},
    ])


@pytest.fixture
def clean_weather_df():
    return pd.DataFrame([
        {"reading_id": "WTH_001", "station": "Ikeja",
         "timestamp": pd.Timestamp("2026-05-26 07:00:00"),
         "condition": "Clear", "temperature_c": 28.5, "humidity_pct": 70,
         "wind_speed_kmh": 12.0, "rainfall_mm": 0.0},
        {"reading_id": "WTH_002", "station": "Lekki",
         "timestamp": pd.Timestamp("2026-05-26 08:00:00"),
         "condition": "Cloudy", "temperature_c": 27.0, "humidity_pct": 75,
         "wind_speed_kmh": 8.0, "rainfall_mm": 0.0},
    ])


# ════════════════════════════════════════════════════════════
# VEHICLE LOCATION VALIDATION TESTS
# ════════════════════════════════════════════════════════════

class TestValidateVehicleLocations:

    def test_passes_clean_data(self, clean_vehicle_df):
        """Clean DataFrame should not raise any exception."""
        validate_vehicle_locations(clean_vehicle_df)  # No exception = pass

    def test_fails_on_empty_dataframe(self, clean_vehicle_df):
        """Empty DataFrame must raise ValidationError."""
        empty = clean_vehicle_df.iloc[0:0]
        with pytest.raises(ValidationError, match="empty"):
            validate_vehicle_locations(empty)

    def test_fails_on_null_vehicle_id(self, clean_vehicle_df):
        """Null vehicle_id must raise ValidationError."""
        bad = clean_vehicle_df.copy()
        bad.loc[0, "vehicle_id"] = None
        with pytest.raises(ValidationError, match="vehicle_id"):
            validate_vehicle_locations(bad)

    def test_fails_on_null_latitude(self, clean_vehicle_df):
        """Null latitude must raise ValidationError."""
        bad = clean_vehicle_df.copy()
        bad.loc[0, "latitude"] = None
        with pytest.raises(ValidationError, match="latitude"):
            validate_vehicle_locations(bad)

    def test_fails_on_negative_speed(self, clean_vehicle_df):
        """Negative speed must raise ValidationError."""
        bad = clean_vehicle_df.copy()
        bad.loc[0, "speed_kmh"] = -5.0
        with pytest.raises(ValidationError, match="speed"):
            validate_vehicle_locations(bad)

    def test_fails_on_coordinates_outside_lagos(self, clean_vehicle_df):
        """Coordinates outside Lagos bounding box must raise ValidationError."""
        bad = clean_vehicle_df.copy()
        bad.loc[0, "latitude"]  = 9.0  # Abuja
        bad.loc[0, "longitude"] = 7.5
        with pytest.raises(ValidationError, match="bounding box"):
            validate_vehicle_locations(bad)


# ════════════════════════════════════════════════════════════
# PASSENGER COUNT VALIDATION TESTS
# ════════════════════════════════════════════════════════════

class TestValidatePassengerCounts:

    def test_passes_clean_data(self, clean_passenger_df):
        """Clean DataFrame should not raise any exception."""
        validate_passenger_counts(clean_passenger_df)

    def test_fails_on_empty_dataframe(self, clean_passenger_df):
        """Empty DataFrame must raise ValidationError."""
        empty = clean_passenger_df.iloc[0:0]
        with pytest.raises(ValidationError, match="empty"):
            validate_passenger_counts(empty)

    def test_fails_on_null_trip_id(self, clean_passenger_df):
        """Null trip_id must raise ValidationError."""
        bad = clean_passenger_df.copy()
        bad.loc[0, "trip_id"] = None
        with pytest.raises(ValidationError, match="trip_id"):
            validate_passenger_counts(bad)

    def test_fails_on_negative_boarded(self, clean_passenger_df):
        """Negative boarded count must raise ValidationError."""
        bad = clean_passenger_df.copy()
        bad.loc[0, "boarded"] = -1
        with pytest.raises(ValidationError, match="boarded"):
            validate_passenger_counts(bad)

    def test_fails_when_load_exceeds_capacity(self, clean_passenger_df):
        """current_load > capacity must raise ValidationError."""
        bad = clean_passenger_df.copy()
        bad.loc[0, "current_load"] = 75  # capacity is 60
        with pytest.raises(ValidationError, match="capacity"):
            validate_passenger_counts(bad)

    def test_fails_on_occupancy_above_100(self, clean_passenger_df):
        """occupancy_rate > 100 must raise ValidationError."""
        bad = clean_passenger_df.copy()
        bad.loc[0, "occupancy_rate"] = 120.0
        with pytest.raises(ValidationError, match="occupancy"):
            validate_passenger_counts(bad)


# ════════════════════════════════════════════════════════════
# WEATHER CONDITION VALIDATION TESTS
# ════════════════════════════════════════════════════════════

class TestValidateWeatherConditions:

    def test_passes_clean_data(self, clean_weather_df):
        """Clean DataFrame should not raise any exception."""
        validate_weather_conditions(clean_weather_df)

    def test_fails_on_empty_dataframe(self, clean_weather_df):
        """Empty DataFrame must raise ValidationError."""
        empty = clean_weather_df.iloc[0:0]
        with pytest.raises(ValidationError, match="empty"):
            validate_weather_conditions(empty)

    def test_fails_on_null_temperature(self, clean_weather_df):
        """Null temperature must raise ValidationError."""
        bad = clean_weather_df.copy()
        bad.loc[0, "temperature_c"] = None
        with pytest.raises(ValidationError, match="temperature_c"):
            validate_weather_conditions(bad)

    def test_fails_on_humidity_above_100(self, clean_weather_df):
        """humidity_pct > 100 must raise ValidationError."""
        bad = clean_weather_df.copy()
        bad.loc[0, "humidity_pct"] = 110
        with pytest.raises(ValidationError, match="humidity"):
            validate_weather_conditions(bad)

    def test_fails_on_negative_rainfall(self, clean_weather_df):
        """Negative rainfall must raise ValidationError."""
        bad = clean_weather_df.copy()
        bad.loc[0, "rainfall_mm"] = -1.0
        with pytest.raises(ValidationError, match="rainfall"):
            validate_weather_conditions(bad)

    def test_fails_on_negative_wind_speed(self, clean_weather_df):
        """Negative wind speed must raise ValidationError."""
        bad = clean_weather_df.copy()
        bad.loc[0, "wind_speed_kmh"] = -5.0
        with pytest.raises(ValidationError, match="wind"):
            validate_weather_conditions(bad)