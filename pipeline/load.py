"""
pipeline/load.py
─────────────────
Load layer — writes cleaned DataFrames to PostgreSQL
"""

import psycopg2
from psycopg2.extras import execute_values
import pandas as pd


# ════════════════════════════════════════════════════════════
#  VEHICLE LOCATIONS
# ════════════════════════════════════════════════════════════

def load_vehicle_locations(df: pd.DataFrame, conn) -> int:
    """
    Bulk insert vehicle location records into PostgreSQL.
    """
    sql = """
        INSERT INTO vehicle_locations
            (vehicle_id, route_id, timestamp, latitude, longitude,
             speed_kmh, heading, status)
        VALUES %s
        ON CONFLICT (vehicle_id, timestamp) DO NOTHING
    """

    rows = [
        (
            row.vehicle_id,
            row.route_id,
            row.timestamp,
            row.latitude,
            row.longitude,
            row.speed_kmh,
            row.heading,
            row.status,
        )
        for row in df.itertuples(index=False)
    ]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=100)

    print(f"  [load] vehicle_locations: {len(rows)} rows inserted")
    return len(rows)


# ════════════════════════════════════════════════════════════
# PASSENGER COUNTS
# ════════════════════════════════════════════════════════════

def load_passenger_counts(df: pd.DataFrame, conn) -> int:
    """
    Bulk insert passenger count records into PostgreSQL.
    """
    sql = """
        INSERT INTO passenger_counts
            (trip_id, vehicle_id, stop_id, route_id, timestamp,
             boarded, alighted, current_load, capacity, occupancy_rate)
        VALUES %s
        ON CONFLICT (trip_id) DO NOTHING
    """

    rows = [
        (
            row.trip_id,
            row.vehicle_id,
            row.stop_id,
            row.route_id,
            row.timestamp,
            int(row.boarded),
            int(row.alighted),
            int(row.current_load),
            int(row.capacity),
            float(row.occupancy_rate),
        )
        for row in df.itertuples(index=False)
    ]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=100)

    print(f"  [load] passenger_counts: {len(rows)} rows inserted")
    return len(rows)


# ════════════════════════════════════════════════════════════
#  WEATHER CONDITIONS
# ════════════════════════════════════════════════════════════

def load_weather_conditions(df: pd.DataFrame, conn) -> int:
    """
    Bulk insert weather condition records into PostgreSQL.
    """
    sql = """
        INSERT INTO weather_conditions
            (reading_id, station, timestamp, condition,
             temperature_c, humidity_pct, wind_speed_kmh, rainfall_mm)
        VALUES %s
        ON CONFLICT (reading_id) DO NOTHING
    """

    rows = [
        (
            row.reading_id,
            row.station,
            row.timestamp,
            row.condition,
            row.temperature_c,
            int(row.humidity_pct),
            row.wind_speed_kmh,
            row.rainfall_mm,
        )
        for row in df.itertuples(index=False)
    ]

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=100)

    print(f"  [load] weather_conditions: {len(rows)} rows inserted")
    return len(rows)