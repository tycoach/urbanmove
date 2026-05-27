"""
dags/urbanmove_daily_etl.py
────────────────────────────
Airflow DAG for the UrbanMove daily ETL pipeline.

Schedule: Every day at 06:00 WAT 
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty  import EmptyOperator


# ── Default arguments applied to every task ──────────────────
default_args = {
    "owner":             "taiwo.hassan",
    "depends_on_past":   False,        # Each run is independent
    "email_on_failure":  False,        # Set to True with real email config
    "email_on_retry":    False,
    "retries":           2,            # Retry twice before marking failed
    "retry_delay":       timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=20),
}


# ════════════════════════════════════════════════════════════
# TASK CALLABLES
# Each function is one task. They import pipeline modules
# locally  to avoid import errors at
# DAG parse time when the pipeline package may not be loaded.
# ════════════════════════════════════════════════════════════

def task_generate_data(**context):
    """
    Generate fresh CSV files in data/raw/.
    """
    import sys
    sys.path.insert(0, "/opt/airflow")

    from scripts.generate_data import (
        generate_vehicle_locations,
        generate_passenger_counts,
        generate_weather_conditions,
    )

    print("Generating synthetic datasets...")
    generate_vehicle_locations()
    generate_passenger_counts()
    generate_weather_conditions()
    print("Data generation complete.")


def task_etl_vehicle_locations(**context):
    """Extract, transform, validate and load vehicle locations."""
    import sys
    sys.path.insert(0, "/opt/airflow")

    from pipeline.extract   import extract_vehicle_locations
    from pipeline.transform import transform_vehicle_locations
    from pipeline.validate  import validate_vehicle_locations
    from pipeline.load      import load_vehicle_locations
    from pipeline.audit     import write_audit_log
    from pipeline.runner    import get_connection

    name       = "vehicle_locations"
    started_at = datetime.now()
    conn       = get_connection()
    conn.autocommit = False

    try:
        raw       = extract_vehicle_locations()
        clean     = transform_vehicle_locations(raw)
        validate_vehicle_locations(clean)
        loaded    = load_vehicle_locations(clean, conn)
        conn.commit()

        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=len(raw), rows_rejected=len(raw) - len(clean),
            rows_loaded=loaded, status="success", started_at=started_at,
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=0, rows_rejected=0, rows_loaded=0,
            status="failed", started_at=started_at, error_message=str(e),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def task_etl_passenger_counts(**context):
    """Extract, transform, validate and load passenger counts."""
    import sys
    sys.path.insert(0, "/opt/airflow")

    from pipeline.extract   import extract_passenger_counts
    from pipeline.transform import transform_passenger_counts
    from pipeline.validate  import validate_passenger_counts
    from pipeline.load      import load_passenger_counts
    from pipeline.audit     import write_audit_log
    from pipeline.runner    import get_connection

    name       = "passenger_counts"
    started_at = datetime.now()
    conn       = get_connection()
    conn.autocommit = False

    try:
        raw    = extract_passenger_counts()
        clean  = transform_passenger_counts(raw)
        validate_passenger_counts(clean)
        loaded = load_passenger_counts(clean, conn)
        conn.commit()

        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=len(raw), rows_rejected=len(raw) - len(clean),
            rows_loaded=loaded, status="success", started_at=started_at,
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=0, rows_rejected=0, rows_loaded=0,
            status="failed", started_at=started_at, error_message=str(e),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def task_etl_weather_conditions(**context):
    """Extract, transform, validate and load weather conditions."""
    import sys
    sys.path.insert(0, "/opt/airflow")

    from pipeline.extract   import extract_weather_conditions
    from pipeline.transform import transform_weather_conditions
    from pipeline.validate  import validate_weather_conditions
    from pipeline.load      import load_weather_conditions
    from pipeline.audit     import write_audit_log
    from pipeline.runner    import get_connection

    name       = "weather_conditions"
    started_at = datetime.now()
    conn       = get_connection()
    conn.autocommit = False

    try:
        raw    = extract_weather_conditions()
        clean  = transform_weather_conditions(raw)
        validate_weather_conditions(clean)
        loaded = load_weather_conditions(clean, conn)
        conn.commit()

        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=len(raw), rows_rejected=len(raw) - len(clean),
            rows_loaded=loaded, status="success", started_at=started_at,
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        write_audit_log(
            conn=conn, run_id=context["run_id"], dataset=name,
            rows_extracted=0, rows_rejected=0, rows_loaded=0,
            status="failed", started_at=started_at, error_message=str(e),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def task_check_audit_log(**context):
    """
    Post-load check — queries pipeline_audit_log to confirm
    all three datasets loaded successfully in this run.
    Fails the task if any dataset shows status='failed'.
    """
    import sys
    sys.path.insert(0, "/opt/airflow")

    import psycopg2
    from pipeline.runner import get_connection

    conn = get_connection()
    run_id = context["run_id"]

    with conn.cursor() as cur:
        cur.execute("""
            SELECT dataset, rows_loaded, status
            FROM   pipeline_audit_log
            WHERE  run_id = %s
            ORDER  BY dataset
        """, (run_id,))
        rows = cur.fetchall()

    conn.close()

    print(f"\nAudit summary for run {run_id}:")
    failures = []
    for dataset, rows_loaded, status in rows:
        icon = "✓" if status == "success" else "✗"
        print(f"  {icon}  {dataset}: {rows_loaded} rows loaded — {status}")
        if status != "success":
            failures.append(dataset)

    if failures:
        raise RuntimeError(
            f"Audit check failed — these datasets did not load successfully: {failures}"
        )

    print("\nAll datasets loaded successfully ✓")


# ════════════════════════════════════════════════════════════
# DAG DEFINITION
# ════════════════════════════════════════════════════════════

with DAG(
    dag_id="urbanmove_daily_etl",
    description="Daily ETL pipeline — UrbanMove transportation data",
    default_args=default_args,
    start_date=datetime(2026, 5, 26),
    schedule_interval="0 5 * * *",   # 05:00 UTC = 06:00 WAT daily
    catchup=False,                   # Don't backfill missed runs
    max_active_runs=1,               # Only one run at a time
    tags=["urbanmove", "etl", "daily"],
) as dag:

    start = EmptyOperator(task_id="start")
    end   = EmptyOperator(task_id="end")

    generate_data = PythonOperator(
        task_id="generate_data",
        python_callable=task_generate_data,
    )

    etl_vehicles = PythonOperator(
        task_id="etl_vehicle_locations",
        python_callable=task_etl_vehicle_locations,
        op_kwargs={"run_id": "RUN_{{ ds_nodash }}_{{ ts_nodash }}"},
    )

    etl_passengers = PythonOperator(
        task_id="etl_passenger_counts",
        python_callable=task_etl_passenger_counts,
        op_kwargs={"run_id": "RUN_{{ ds_nodash }}_{{ ts_nodash }}"},
    )

    etl_weather = PythonOperator(
        task_id="etl_weather_conditions",
        python_callable=task_etl_weather_conditions,
        op_kwargs={"run_id": "RUN_{{ ds_nodash }}_{{ ts_nodash }}"},
    )

    check_audit = PythonOperator(
        task_id="check_audit_log",
        python_callable=task_check_audit_log,
        op_kwargs={"run_id": "RUN_{{ ds_nodash }}_{{ ts_nodash }}"},
    )

    # ── Dependency graph ─────────────────────────────────────
    #
    #  start → generate_data → etl_vehicles    ┐
    #                        → etl_passengers  ├→ check_audit → end
    #                        → etl_weather     ┘
    #
    start >> generate_data >> [etl_vehicles, etl_passengers, etl_weather]
    [etl_vehicles, etl_passengers, etl_weather] >> check_audit >> end