"""DuckDB storage layer.

Schema is TRD §3.1, verbatim in intent. DuckDB is file-based and zero-ops: a
judge can open data/vayu.duckdb and run SQL against everything VAYU claims,
which is the point — the numbers on screen are queryable, not asserted.

Concurrency note: DuckDB allows one writer. The API opens read-only connections
per request; the seeder/scheduler is the only writer.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

from vayu_core.config import get_settings

_write_lock = threading.Lock()

# DuckDB sizes its buffer pool off detected host memory. Locally that is what
# we want (unconstrained); set DUCKDB_MEMORY_LIMIT to cap it on a small host.
def _bound_memory(con: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    limit = get_settings().duckdb_memory_limit
    if limit:
        con.execute(f"PRAGMA memory_limit='{limit}'")
        con.execute("PRAGMA threads=2")
    return con

SCHEMA = """
CREATE TABLE IF NOT EXISTS measurements(
  city TEXT, station_id TEXT, param TEXT,          -- pm25|pm10|no2|so2|co|o3
  ts TIMESTAMPTZ, value DOUBLE, unit TEXT,
  source TEXT,                                     -- see provenance labels below
  PRIMARY KEY(city, station_id, param, ts));

CREATE TABLE IF NOT EXISTS stations(
  city TEXT, station_id TEXT PRIMARY KEY, name TEXT,
  lat DOUBLE, lon DOUBLE, provider TEXT,
  first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ);

-- Deviation from TRD 3.1, documented: a `grid` discriminator is added to the
-- primary key. The TRD assumes one weather grid, but the city grid (~12 km,
-- drives station features) and the airshed grid (~33 km over city+2deg, the
-- domain a 24h back-trajectory actually crosses) have different resolutions and
-- extents and must coexist. Without this, a trajectory to Punjab runs on Delhi's
-- edge wind extrapolated 200 km.
CREATE TABLE IF NOT EXISTS weather_hourly(
  city TEXT, grid TEXT DEFAULT 'city',             -- city|airshed
  grid_i INT, grid_j INT, ts TIMESTAMPTZ,
  temp_c DOUBLE, rh DOUBLE, wind_speed_10m DOUBLE, wind_dir_10m DOUBLE,
  wind_speed_100m DOUBLE, wind_dir_100m DOUBLE, pblh DOUBLE,
  precip DOUBLE, pressure DOUBLE,
  kind TEXT,                                       -- hist|forecast
  PRIMARY KEY(city, grid, grid_i, grid_j, ts, kind));

CREATE TABLE IF NOT EXISTS fires(
  city TEXT, fire_id TEXT PRIMARY KEY, lat DOUBLE, lon DOUBLE,
  frp DOUBLE, confidence TEXT, acq_ts TIMESTAMPTZ, sensor TEXT, source TEXT);

CREATE TABLE IF NOT EXISTS wards(
  city TEXT, ward_id TEXT, name TEXT, geom_geojson TEXT,
  centroid_lat DOUBLE, centroid_lon DOUBLE, area_km2 DOUBLE,
  population INT, pop_source TEXT,
  PRIMARY KEY(city, ward_id));

CREATE TABLE IF NOT EXISTS forecasts(
  city TEXT, ward_id TEXT, run_ts TIMESTAMPTZ, target_ts TIMESTAMPTZ,
  horizon_h INT, p10 DOUBLE, p50 DOUBLE, p90 DOUBLE, aqi_p50 INT, model_ver TEXT,
  PRIMARY KEY(city, ward_id, run_ts, target_ts));

CREATE TABLE IF NOT EXISTS attributions(
  city TEXT, ward_id TEXT, computed_ts TIMESTAMPTZ, category TEXT,
  share_pct DOUBLE, confidence DOUBLE, evidence_json TEXT,
  PRIMARY KEY(city, ward_id, computed_ts, category));

CREATE TABLE IF NOT EXISTS interventions(
  id TEXT PRIMARY KEY, city TEXT, ward_id TEXT, created_ts TIMESTAMPTZ,
  action_type TEXT, title TEXT, source_lat DOUBLE, source_lon DOUBLE,
  predicted_ugm3_averted DOUBLE, population_protected INT, effort_units INT,
  confidence DOUBLE, roi_score DOUBLE,
  status TEXT,                                     -- candidate|dispatched|executed|verified
  dossier_path TEXT, signal_ts TIMESTAMPTZ, dispatched_ts TIMESTAMPTZ,
  executed_ts TIMESTAMPTZ, seeded BOOLEAN DEFAULT FALSE);

CREATE TABLE IF NOT EXISTS verifications(
  intervention_id TEXT PRIMARY KEY, method TEXT,
  control_wards TEXT, predicted_reduction DOUBLE, observed_reduction DOUBLE,
  ci_low DOUBLE, ci_high DOUBLE, pct_realized DOUBLE, computed_ts TIMESTAMPTZ);

CREATE SEQUENCE IF NOT EXISTS audit_log_seq;
CREATE TABLE IF NOT EXISTS audit_log(
  id BIGINT PRIMARY KEY DEFAULT nextval('audit_log_seq'),
  ts TIMESTAMPTZ, agent TEXT, trigger TEXT,
  inputs_hash TEXT, decision TEXT, reasoning TEXT,
  confidence DOUBLE, duration_ms INT);

CREATE TABLE IF NOT EXISTS grap_drafts(
  id TEXT PRIMARY KEY, city TEXT, stage INT, trigger_forecast_ts TIMESTAMPTZ,
  measures_json TEXT, citations_json TEXT, status TEXT);

-- Weighted road km per km² per ward — the traffic proxy (TRD 5.3). Static.
CREATE TABLE IF NOT EXISTS ward_roads(
  city TEXT, ward_id TEXT,
  road_km DOUBLE, road_km_weighted DOUBLE, road_density DOUBLE,
  PRIMARY KEY(city, ward_id));

-- Construction permits. `source` is always 'sample': no public machine-readable
-- permit feed exists for these cities, so this layer is curated on real OSM
-- construction landuse and badged as sample wherever it surfaces.
CREATE TABLE IF NOT EXISTS permits(
  city TEXT, permit_id TEXT, name TEXT, site_type TEXT,
  lat DOUBLE, lon DOUBLE, status TEXT,
  dust_control_compliant BOOLEAN, last_inspected TEXT, source TEXT,
  PRIMARY KEY(city, permit_id));

-- Per-source freshness backing the honesty pills (PRD F2). The UI never guesses
-- whether a layer is live; it reads what the ingestor recorded.
CREATE TABLE IF NOT EXISTS data_status(
  city TEXT, source TEXT, status TEXT,             -- live|cached|sample|unavailable
  detail TEXT, rows_loaded INT, fetched_ts TIMESTAMPTZ,
  PRIMARY KEY(city, source));

"""

# Provenance labels for measurements.source / data_status.status.
# Honesty is a schema-level concern here, not a UI afterthought.
SOURCE_CPCB_LIVE = "cpcb-live"        # measured, CPCB CAAQMS via data.gov.in
SOURCE_OPENAQ = "openaq"              # measured, OpenAQ v3 (needs key)
SOURCE_CAMS = "cams-reanalysis"       # MODELLED, Open-Meteo/CAMS at station coords
SOURCE_SAMPLE = "sample"              # bundled offline copy of one of the above


def db_file() -> Path:
    p = get_settings().db_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def init_db(path: Path | None = None) -> None:
    target = path or db_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        con = _bound_memory(duckdb.connect(str(target)))
        try:
            con.execute(SCHEMA)
        finally:
            con.close()


@contextmanager
def write_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    """Exclusive writer connection (seeder / scheduler)."""
    target = db_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        con = _bound_memory(duckdb.connect(str(target)))
        try:
            con.execute(SCHEMA)
            yield con
        finally:
            con.close()


@contextmanager
def read_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    """Read-only connection for API requests.

    Falls back to a normal connection when the file does not exist yet so a
    fresh clone returns empty results (-> designed empty states) instead of
    a 500 before `make seed` has run.
    """
    target = db_file()
    if not target.exists():
        init_db(target)
    con = _bound_memory(duckdb.connect(str(target), read_only=True))
    try:
        yield con
    finally:
        con.close()


def upsert_df(con: duckdb.DuckDBPyConnection, table: str, df, keys: list[str]) -> int:
    """Idempotent INSERT OR REPLACE from a DataFrame (TRD §4: every ingestor is
    idempotent, so re-running `make seed` is always safe)."""
    if df is None or len(df) == 0:
        return 0
    con.register("_incoming", df)
    cols = ", ".join(df.columns)
    key_pred = " AND ".join(f"t.{k} = _incoming.{k}" for k in keys)
    con.execute(f"DELETE FROM {table} t WHERE EXISTS (SELECT 1 FROM _incoming WHERE {key_pred})")
    con.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _incoming")
    con.unregister("_incoming")
    return len(df)


def set_data_status(
    con: duckdb.DuckDBPyConnection,
    city: str,
    source: str,
    status: str,
    detail: str = "",
    rows: int = 0,
    fetched_ts=None,
) -> None:
    from datetime import datetime, timezone

    con.execute(
        """INSERT OR REPLACE INTO data_status(city, source, status, detail, rows_loaded, fetched_ts)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [city, source, status, detail, rows, fetched_ts or datetime.now(timezone.utc)],
    )
