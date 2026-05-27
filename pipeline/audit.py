"""
pipeline/audit.py
──────────────────
Audit layer — writes a run summary to pipeline_audit_log after
every dataset is processed, whether it succeeded or failed.
"""

import psycopg2
from datetime import datetime, date


def write_audit_log(
    conn,
    run_id:        str,
    dataset:       str,
    rows_extracted: int,
    rows_rejected:  int,
    rows_loaded:    int,
    status:        str,          # "success" | "failed"
    started_at:    datetime,
    error_message: str = None,
) -> None:
    """
    Insert one audit record into pipeline_audit_log.
    """
    sql = """
        INSERT INTO pipeline_audit_log (
            run_id, dataset, run_date,
            rows_extracted, rows_rejected, rows_loaded,
            status, error_message,
            started_at, completed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        cur.execute(sql, (
            run_id,
            dataset,
            date.today(),
            rows_extracted,
            rows_rejected,
            rows_loaded,
            status,
            error_message,
            started_at,
            datetime.now(),
        ))

    print(
        f"  [audit] {dataset}: "
        f"status={status} | "
        f"extracted={rows_extracted} | "
        f"rejected={rows_rejected} | "
        f"loaded={rows_loaded}"
    )