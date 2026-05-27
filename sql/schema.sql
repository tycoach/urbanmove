-- ============================================================
-- sql/schema.sql
-- UrbanMove Analytics — PostgreSQL Schema
-- ============================================================
-- Run this once before the pipeline:
--   psql -U urbanmove -d urbanmove_db -f sql/schema.sql
-- Or it runs automatically via docker-compose on first boot.
-- ============================================================


-- ── Drop existing tables (clean re-run during dev) ──────────
DROP TABLE IF EXISTS pipeline_audit_log  CASCADE;
DROP TABLE IF EXISTS passenger_counts    CASCADE;
DROP TABLE IF EXISTS vehicle_locations   CASCADE;
DROP TABLE IF EXISTS weather_conditions  CASCADE;


-- ════════════════════════════════════════════════════════════
-- VEHICLE LOCATIONS
-- One row per GPS ping from a vehicle.
-- Unique constraint on (vehicle_id, timestamp) prevents
-- duplicate network retries from loading twice.
-- ════════════════════════════════════════════════════════════

CREATE TABLE vehicle_locations (
    id          SERIAL          PRIMARY KEY,
    vehicle_id  VARCHAR(10)     NOT NULL,
    route_id    VARCHAR(10)     NOT NULL,
    timestamp   TIMESTAMP       NOT NULL,
    latitude    DECIMAL(9, 6)   NOT NULL,
    longitude   DECIMAL(9, 6)   NOT NULL,
    speed_kmh   DECIMAL(5, 1)   NOT NULL  CHECK (speed_kmh >= 0),
    heading     INTEGER                   CHECK (heading BETWEEN 0 AND 359),
    status      VARCHAR(20)     NOT NULL  DEFAULT 'unknown',
    loaded_at   TIMESTAMP                 DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (vehicle_id, timestamp)
);


-- ════════════════════════════════════════════════════════════
-- PASSENGER COUNTS
-- One row per boarding/alighting event at a stop.
-- trip_id is the natural key from the source system.
-- occupancy_rate is computed during transformation and stored
-- here so analysts don't have to recalculate it every query.
-- ════════════════════════════════════════════════════════════

CREATE TABLE passenger_counts (
    id              SERIAL          PRIMARY KEY,
    trip_id         VARCHAR(10)     NOT NULL  UNIQUE,
    vehicle_id      VARCHAR(10)     NOT NULL,
    stop_id         VARCHAR(10)     NOT NULL,
    route_id        VARCHAR(10)     NOT NULL,
    timestamp       TIMESTAMP       NOT NULL,
    boarded         INTEGER         NOT NULL  DEFAULT 0  CHECK (boarded  >= 0),
    alighted        INTEGER         NOT NULL  DEFAULT 0  CHECK (alighted >= 0),
    current_load    INTEGER         NOT NULL  DEFAULT 0  CHECK (current_load >= 0),
    capacity        INTEGER         NOT NULL  DEFAULT 60 CHECK (capacity > 0),
    occupancy_rate  DECIMAL(5, 2),                       -- current_load / capacity × 100
    loaded_at       TIMESTAMP                 DEFAULT CURRENT_TIMESTAMP
);


-- ════════════════════════════════════════════════════════════
-- WEATHER CONDITIONS
-- One row per weather reading from a monitoring station.
-- reading_id is the natural key from the station system.
-- ════════════════════════════════════════════════════════════

CREATE TABLE weather_conditions (
    id              SERIAL          PRIMARY KEY,
    reading_id      VARCHAR(10)     NOT NULL  UNIQUE,
    station         VARCHAR(30)     NOT NULL,
    timestamp       TIMESTAMP       NOT NULL,
    condition       VARCHAR(20),
    temperature_c   DECIMAL(4, 1),
    humidity_pct    INTEGER                   CHECK (humidity_pct BETWEEN 0 AND 100),
    wind_speed_kmh  DECIMAL(5, 1)             CHECK (wind_speed_kmh >= 0),
    rainfall_mm     DECIMAL(5, 1)             CHECK (rainfall_mm >= 0),
    loaded_at       TIMESTAMP                 DEFAULT CURRENT_TIMESTAMP
);


-- ════════════════════════════════════════════════════════════
-- PIPELINE AUDIT LOG
-- One row written after every pipeline run, per dataset.
-- Lets us track: what ran, when, how many rows were
-- accepted vs rejected, and whether it succeeded.
-- This is what you'd show an ops team or a data manager.
-- ════════════════════════════════════════════════════════════

CREATE TABLE pipeline_audit_log (
    id              SERIAL          PRIMARY KEY,
    run_id          VARCHAR(30)     NOT NULL,   -- e.g. RUN_20260526_060000
    dataset         VARCHAR(30)     NOT NULL,   -- vehicle_locations, passenger_counts, weather_conditions
    run_date        DATE            NOT NULL,
    rows_extracted  INTEGER         DEFAULT 0,
    rows_rejected   INTEGER         DEFAULT 0,
    rows_loaded     INTEGER         DEFAULT 0,
    status          VARCHAR(10)     NOT NULL,   -- success | failed
    error_message   TEXT,
    started_at      TIMESTAMP       NOT NULL,
    completed_at    TIMESTAMP
);


-- ════════════════════════════════════════════════════════════
-- INDEXES
-- Added on columns analysts and the pipeline query most often.
-- Without indexes, a full table scan on 1M vehicle pings
-- for a single route would take seconds instead of milliseconds.
-- ════════════════════════════════════════════════════════════

-- Vehicle locations — filter by route or vehicle, order by time
CREATE INDEX idx_vl_route_id   ON vehicle_locations (route_id);
CREATE INDEX idx_vl_vehicle_id ON vehicle_locations (vehicle_id);
CREATE INDEX idx_vl_timestamp  ON vehicle_locations (timestamp);

-- Passenger counts — filter by stop, route, time
CREATE INDEX idx_pc_stop_id    ON passenger_counts (stop_id);
CREATE INDEX idx_pc_route_id   ON passenger_counts (route_id);
CREATE INDEX idx_pc_timestamp  ON passenger_counts (timestamp);

-- Weather — filter by station and time
CREATE INDEX idx_wc_station    ON weather_conditions (station);
CREATE INDEX idx_wc_timestamp  ON weather_conditions (timestamp);


-- ════════════════════════════════════════════════════════════
-- ANALYST VIEW — Ridership summary by route and hour
-- Analysts query this instead of writing complex JOINs every time.
-- Teaching point: views are a contract between engineers and analysts.
-- ════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW vw_ridership_by_route_hour AS
SELECT
    route_id,
    DATE_TRUNC('hour', timestamp)       AS hour,
    SUM(boarded)                        AS total_boarded,
    SUM(alighted)                       AS total_alighted,
    ROUND(AVG(current_load), 1)         AS avg_load,
    ROUND(AVG(occupancy_rate), 1)       AS avg_occupancy_pct,
    COUNT(*)                            AS total_stop_visits
FROM
    passenger_counts
GROUP BY
    route_id,
    DATE_TRUNC('hour', timestamp)
ORDER BY
    hour,
    route_id;