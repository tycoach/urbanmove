-- ============================================================
-- sql/queries/ridership_summary.sql
-- UrbanMove Analytics — Sample Analyst Queries
-- ============================================================
-- These are the kinds of questions the UrbanMove analytics
-- team can now answer once the pipeline has loaded data.
-- Run these in pgAdmin or any PostgreSQL client.
-- ============================================================


-- ── 1. RIDERSHIP BY ROUTE AND HOUR ───────────────────────────
-- Which routes are busiest and at what time of day?
-- Uses the pre-built analyst view from schema.sql

SELECT
    route_id,
    hour,
    total_boarded,
    total_alighted,
    avg_load,
    avg_occupancy_pct,
    total_stop_visits
FROM vw_ridership_by_route_hour
ORDER BY total_boarded DESC;


-- ── 2. PEAK HOUR PER ROUTE ───────────────────────────────────
-- For each route, which hour had the most boardings?

SELECT DISTINCT ON (route_id)
    route_id,
    hour,
    total_boarded           AS peak_boardings
FROM vw_ridership_by_route_hour
ORDER BY route_id, total_boarded DESC;


-- ── 3. MOST CONGESTED STOPS ──────────────────────────────────
-- Which stops are handling the highest passenger volumes?

SELECT
    stop_id,
    route_id,
    SUM(boarded)                        AS total_boarded,
    SUM(alighted)                       AS total_alighted,
    ROUND(AVG(occupancy_rate), 1)       AS avg_occupancy_pct,
    COUNT(*)                            AS total_visits
FROM passenger_counts
GROUP BY stop_id, route_id
ORDER BY total_boarded DESC
LIMIT 10;


-- ── 4. VEHICLES WITH HIGHEST AVERAGE OCCUPANCY ───────────────
-- Which vehicles are consistently running close to full capacity?

SELECT
    pc.vehicle_id,
    COUNT(*)                            AS total_stop_visits,
    ROUND(AVG(pc.occupancy_rate), 1)    AS avg_occupancy_pct,
    MAX(pc.occupancy_rate)              AS peak_occupancy_pct
FROM passenger_counts pc
GROUP BY pc.vehicle_id
ORDER BY avg_occupancy_pct DESC;


-- ── 5. WEATHER IMPACT ON RIDERSHIP ───────────────────────────
-- Does bad weather reduce ridership?
-- Joins passenger counts to the nearest weather reading by hour.

SELECT
    wc.condition                        AS weather_condition,
    COUNT(pc.trip_id)                   AS total_trips,
    SUM(pc.boarded)                     AS total_boarded,
    ROUND(AVG(pc.occupancy_rate), 1)    AS avg_occupancy_pct
FROM passenger_counts pc
JOIN weather_conditions wc
    ON DATE_TRUNC('hour', pc.timestamp) = DATE_TRUNC('hour', wc.timestamp)
GROUP BY wc.condition
ORDER BY total_boarded DESC;


-- ── 6. OUT-OF-SERVICE VEHICLES ────────────────────────────────
-- Which vehicles were out of service and for how long today?

SELECT
    vehicle_id,
    COUNT(*)                            AS out_of_service_pings,
    MIN(timestamp)                      AS first_seen,
    MAX(timestamp)                      AS last_seen
FROM vehicle_locations
WHERE status = 'out_of_service'
  AND timestamp::date = CURRENT_DATE
GROUP BY vehicle_id
ORDER BY out_of_service_pings DESC;


-- ── 7. PIPELINE AUDIT SUMMARY ────────────────────────────────
-- How did the last pipeline run perform?

SELECT
    run_id,
    dataset,
    rows_extracted,
    rows_rejected,
    rows_loaded,
    ROUND(
        (rows_rejected::decimal / NULLIF(rows_extracted, 0)) * 100, 1
    )                                   AS rejection_rate_pct,
    status,
    EXTRACT(EPOCH FROM (completed_at - started_at))::int
                                        AS duration_seconds
FROM pipeline_audit_log
WHERE run_date = CURRENT_DATE
ORDER BY started_at;


-- ── 8. DATA FRESHNESS CHECK ───────────────────────────────────
-- When was each table last updated?
-- Use this to confirm the pipeline ran successfully today.

SELECT 'vehicle_locations'  AS dataset, MAX(loaded_at) AS last_loaded FROM vehicle_locations
UNION ALL
SELECT 'passenger_counts',             MAX(loaded_at)               FROM passenger_counts
UNION ALL
SELECT 'weather_conditions',           MAX(loaded_at)               FROM weather_conditions
ORDER BY last_loaded DESC;