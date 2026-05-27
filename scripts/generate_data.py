"""
scripts/generate_data.py
─────────────────────────
Generates synthetic UrbanMove transportation data and saves as CSV files.
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

# ── Output directory ─────────────────────────────────────────
RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ── Reference data ───────────────────────────────────────────
ROUTES     = ["Route_A", "Route_B", "Route_C", "Route_D", "Route_E"]
VEHICLES   = [f"VH_{str(i).zfill(3)}" for i in range(1, 16)]    # 15 vehicles
STOPS      = [f"STOP_{str(i).zfill(2)}" for i in range(1, 21)]  # 20 stops
CONDITIONS = ["Clear", "Cloudy", "Rainy", "Foggy", "Stormy"]
STATIONS   = ["Ikeja", "Lagos_Island", "Lekki", "Surulere", "Yaba"]

BASE_DATE  = datetime(2026, 5, 26, 6, 0, 0)  # Pipeline run date — 6AM


# ════════════════════════════════════════════════════════════
#   VEHICLE LOCATIONS
#    Source: GPS transponders on each vehicle, pinging every 5 min
#    Real-world issues: lost GPS signal, sensor glitches, duplicated
#    packets from network retries


def generate_vehicle_locations(n: int = 200) -> pd.DataFrame:
    """
    Simulates GPS location pings from the UrbanMove fleet.
    """
    records = []

    for i in range(n):
        record = {
            "vehicle_id": random.choice(VEHICLES),
            "route_id":   random.choice(ROUTES),
            "timestamp":  (BASE_DATE + timedelta(minutes=i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
            "latitude":   round(6.524 + random.uniform(-0.08, 0.08), 6),
            "longitude":  round(3.379 + random.uniform(-0.07, 0.07), 6),
            "speed_kmh":  round(random.uniform(5, 75), 1),
            "heading":    random.randint(0, 359),
            "status":     random.choice(["in_service", "in_service", "in_service", "out_of_service"]),
        }

        # Every 20th record: lost GPS signal
        if i % 20 == 0:
            record["latitude"]  = None
            record["longitude"] = None

        # Every 35th record: sensor sends negative speed
        if i % 35 == 0:
            record["speed_kmh"] = round(random.uniform(-20, -1), 1)

        # Every 50th record: status missing from payload
        if i % 50 == 0:
            record["status"] = None

        records.append(record)

    df = pd.DataFrame(records)

    # Inject 12 duplicate rows (network retry simulation)
    duplicates = df.sample(12, random_state=1)
    df = pd.concat([df, duplicates], ignore_index=True)

    path = os.path.join(RAW_DIR, "vehicle_locations.csv")
    df.to_csv(path, index=False)

    print(f"  vehicle_locations.csv  →  {len(df):>4} rows  ({len(df) - n} duplicates injected)")
    return df


# ════════════════════════════════════════════════════════════
#    PASSENGER COUNTS
#    Source: Manual counters at stops + automated door sensors
#    Real-world issues: sensors missing counts, manual entry errors,
#    load exceeding capacity


def generate_passenger_counts(n: int = 150) -> pd.DataFrame:
    """
    Simulates passenger boarding and alighting counts at each stop.
    """
    records = []

    for i in range(n):
        boarded  = random.randint(0, 45)
        alighted = random.randint(0, max(1, boarded))
        load     = max(0, boarded - alighted + random.randint(0, 15))

        record = {
            "trip_id":      f"TRP_{str(i + 1).zfill(4)}",
            "vehicle_id":   random.choice(VEHICLES),
            "stop_id":      random.choice(STOPS),
            "route_id":     random.choice(ROUTES),
            "timestamp":    (BASE_DATE + timedelta(minutes=i * 4)).strftime("%Y-%m-%d %H:%M:%S"),
            "boarded":      boarded,
            "alighted":     alighted,
            "current_load": load,
            "capacity":     60,
        }

        # Every 25th: sensor offline — no boarding count
        if i % 25 == 0:
            record["boarded"] = None

        # Every 40th: load exceeds capacity (manual entry error)
        if i % 40 == 0:
            record["current_load"] = random.randint(61, 100)

        # Every 60th: negative alighted (data entry mistake)
        if i % 60 == 0:
            record["alighted"] = -random.randint(1, 5)

        # Every 30th: boarded stored as string not integer
        if i % 30 == 0 and record["boarded"] is not None:
            record["boarded"] = str(record["boarded"])

        records.append(record)

    df = pd.DataFrame(records)
    path = os.path.join(RAW_DIR, "passenger_counts.csv")
    df.to_csv(path, index=False)

    print(f"  passenger_counts.csv   →  {len(df):>4} rows")
    return df


# ════════════════════════════════════════════════════════════
#  WEATHER CONDITIONS
#    Source: Lagos State weather monitoring stations
#    Real-world issues: station outages, faulty sensor spikes


def generate_weather_conditions(n: int = 100) -> pd.DataFrame:
    """
    Simulates hourly weather readings across Lagos monitoring stations.
    """
    records = []

    for i in range(n):
        condition = random.choice(CONDITIONS)

        record = {
            "reading_id":     f"WTH_{str(i + 1).zfill(4)}",
            "station":        random.choice(STATIONS),
            "timestamp":      (BASE_DATE + timedelta(hours=i // 5)).strftime("%Y-%m-%d %H:%M:%S"),
            "condition":      condition,
            "temperature_c":  round(random.uniform(24, 35), 1),
            "humidity_pct":   random.randint(50, 90),
            "wind_speed_kmh": round(random.uniform(0, 35), 1),
            "rainfall_mm":    round(random.uniform(0, 15), 1) if condition in ["Rainy", "Stormy"] else 0.0,
        }

        # Every 15th: station offline — no temperature reading
        if i % 15 == 0:
            record["temperature_c"] = None

        # Every 22nd: humidity sensor spike (impossible value)
        if i % 22 == 0:
            record["humidity_pct"] = random.randint(101, 150)

        # Every 45th: negative rainfall from sensor error
        if i % 45 == 0:
            record["rainfall_mm"] = round(random.uniform(-5, -0.1), 1)

        # Every 33rd: condition description missing from report
        if i % 33 == 0:
            record["condition"] = None

        records.append(record)

    df = pd.DataFrame(records)
    path = os.path.join(RAW_DIR, "weather_conditions.csv")
    df.to_csv(path, index=False)

    print(f"  weather_conditions.csv →  {len(df):>4} rows")
    return df


# ════════════════════════════════════════════════════════════
# MAIN


if __name__ == "__main__":
    print("UrbanMove — Generating synthetic datasets")
    print(f"Output: {os.path.abspath(RAW_DIR)}")
    print("=" * 52)

    generate_vehicle_locations()
    generate_passenger_counts()
    generate_weather_conditions()

    print("=" * 52)
    print("Done. Run the ETL pipeline next:")
    print("  python pipeline/runner.py")
    print("=" * 52)