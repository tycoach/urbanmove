"""
pipeline/runner.py
───────────────────
Pipeline runner — orchestrates the full ETL flow for all three datasets.
"""

import os
import psycopg2
from datetime import datetime

from pipeline.extract   import extract_vehicle_locations, extract_passenger_counts, extract_weather_conditions
from pipeline.transform import transform_vehicle_locations, transform_passenger_counts, transform_weather_conditions
from pipeline.validate  import validate_vehicle_locations, validate_passenger_counts, validate_weather_conditions, ValidationError
from pipeline.load      import load_vehicle_locations, load_passenger_counts, load_weather_conditions
from pipeline.audit     import write_audit_log


# ── Database connection settings ─────────────────────────────
# Reads from environment variables so the same code works

DB_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST",     "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname":   os.getenv("POSTGRES_DB",       "urbanmove_db"),
    "user":     os.getenv("POSTGRES_USER",     "urbanmove"),
    "password": os.getenv("POSTGRES_PASSWORD", "urbanmove_pass"),
}


def get_connection():
    """Open and return a psycopg2 connection."""
    return psycopg2.connect(**DB_CONFIG)


# ── Pipeline registry ─────────────────────────────────────────
# Each entry wires one dataset's extract, transform, validate,
# and load functions together.
# Adding a new dataset = adding one entry here

PIPELINES = [
    {
        "name":      "vehicle_locations",
        "extract":   extract_vehicle_locations,
        "transform": transform_vehicle_locations,
        "validate":  validate_vehicle_locations,
        "load":      load_vehicle_locations,
    },
    {
        "name":      "passenger_counts",
        "extract":   extract_passenger_counts,
        "transform": transform_passenger_counts,
        "validate":  validate_passenger_counts,
        "load":      load_passenger_counts,
    },
    {
        "name":      "weather_conditions",
        "extract":   extract_weather_conditions,
        "transform": transform_weather_conditions,
        "validate":  validate_weather_conditions,
        "load":      load_weather_conditions,
    },
]


def run_pipeline() -> dict:
    """
    Run the full UrbanMove ETL pipeline.
    """
    run_id  = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    results = {}

    print("=" * 55)
    print(f"UrbanMove ETL Pipeline")
    print(f"Run ID   : {run_id}")
    print(f"Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    conn = get_connection()
    conn.autocommit = False  # We control commits explicitly

    for pipeline in PIPELINES:
        name       = pipeline["name"]
        started_at = datetime.now()

        print(f"\n── {name} ──")

        rows_extracted = 0
        rows_rejected  = 0
        rows_loaded    = 0

        try:
            # ── EXTRACT ──────────────────────────────────────
            raw_df         = pipeline["extract"]()
            rows_extracted = len(raw_df)

            # ── TRANSFORM ────────────────────────────────────
            clean_df      = pipeline["transform"](raw_df)
            rows_rejected = rows_extracted - len(clean_df)

            # ── VALIDATE ─────────────────────────────────────
            pipeline["validate"](clean_df)

            # ── LOAD ─────────────────────────────────────────
            rows_loaded = pipeline["load"](clean_df, conn)
            conn.commit()   # Commit this dataset independently

            # ── AUDIT ─────────────────────────────────────────
            write_audit_log(
                conn           = conn,
                run_id         = run_id,
                dataset        = name,
                rows_extracted = rows_extracted,
                rows_rejected  = rows_rejected,
                rows_loaded    = rows_loaded,
                status         = "success",
                started_at     = started_at,
            )
            conn.commit()

            results[name] = "success"
            print(f"   {name} complete")

        except (ValidationError, Exception) as e:
            conn.rollback()  # Roll back any uncommitted writes for this dataset

            write_audit_log(
                conn           = conn,
                run_id         = run_id,
                dataset        = name,
                rows_extracted = rows_extracted,
                rows_rejected  = rows_rejected,
                rows_loaded    = 0,
                status         = "failed",
                started_at     = started_at,
                error_message  = str(e),
            )
            conn.commit()

            results[name] = "failed"
            print(f"   {name} FAILED: {e}")

    conn.close()

    print("\n" + "=" * 55)
    print("Pipeline complete")
    print(f"Finished : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for name, status in results.items():
        icon = "✓" if status == "success" else "✗"
        print(f"  {icon}  {name}: {status}")
    print("=" * 55)

    return results


if __name__ == "__main__":
    run_pipeline()