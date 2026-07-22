"""Live gap-fill: make ANY present-day instant fully served (the product rule).

The contract VAYU promises:

    * date inside the archive  -> serve from the database
    * date beyond the archive  -> fetch it live, right now, and serve that

This module implements the second half for "now": one call pulls every live
layer the science needs for the current hour and writes it into the same tables
the archive uses — so the model, trajectory, plume, attribution and scout all
run on today exactly as they do on 3 Nov:

    measurements  CPCB current snapshot (+ OpenAQ recent days when keyed)
    weather       Open-Meteo forecast API with past_days: 10 days of analysis
                  behind + 4 days ahead, city grid (all vars) AND airshed grid
                  (wind — what the back-trajectory integrates through)
    fires         NASA FIRMS NRT, last 7 days
    forecast      scored on demand for the current hour (windowed, ~1.5 s)

The LLM+Tavily scout is the separate /scout/run sweep — evidence, not data.
Everything degrades per-source: a failed feed logs + records its status and the
rest still lands (same philosophy as seed.py).
"""

from __future__ import annotations

import gc
import threading
from datetime import timedelta

import pandas as pd
from loguru import logger

from vayu_core.config import CityConfig, get_settings, load_city
from vayu_core.db import set_data_status, upsert_df, write_conn

MEAS_COLS = ["city", "station_id", "param", "ts", "value", "unit", "source"]

# The model's true longest lookback is MAX_LOOKBACK_HOURS=48h (features.py) —
# pm25_lag48 and the 48h regional fire window. 4 days gives 2 days of slack for
# gappy stations while keeping the live-fill's peak pandas footprint safely
# under Render's 512MB free-tier ceiling (a 6-day window peaked at ~510MB — one
# bad moment from an OOM kill). "Use only 5 days of data" — this is that.
# 3 days ahead covers fx_* out to t+72h exactly.
PAST_DAYS = 4
FORECAST_DAYS = 3

_lock = threading.Lock()
_running: set[str] = set()


def _fill_measurements(city: CityConfig, now) -> dict:
    from services.pipeline import cpcb, openaq

    out = {"stations": 0, "rows": 0}
    frames: list[pd.DataFrame] = []

    # CPCB: the freshest official reading per station (fast, ~15 s).
    try:
        st, cur = cpcb.fetch_stations(city)
        if not st.empty:
            with write_conn() as con:
                out["stations"] += upsert_df(
                    con, "stations", st.drop(columns=["sensors"], errors="ignore"), ["station_id"]
                )
        if not cur.empty:
            frames.append(cur.reindex(columns=MEAS_COLS))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[{city.id}] livefill CPCB failed: {exc}")

    # OpenAQ: hourly history for the lag features (needs a key; optional).
    try:
        if openaq.available():
            start, end = now.date() - timedelta(days=PAST_DAYS), now.date()
            loc = openaq.fetch_locations(city, start, end)
            if not loc.empty:
                with write_conn() as con:
                    out["stations"] += upsert_df(
                        con, "stations", loc.drop(columns=["sensors"], errors="ignore"), ["station_id"]
                    )
                hist = openaq.fetch_measurements(city, loc, start, end)
                if not hist.empty:
                    frames.append(hist.reindex(columns=MEAS_COLS))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[{city.id}] livefill OpenAQ failed: {exc}")

    if frames:
        meas = pd.concat(frames, ignore_index=True).drop_duplicates(
            subset=["city", "station_id", "param", "ts"], keep="last"
        )
        with write_conn() as con:
            out["rows"] = upsert_df(con, "measurements", meas, ["city", "station_id", "param", "ts"])
            set_data_status(con, city.id, "measurements", "live", f"live gap-fill · {out['rows']} rows", out["rows"])
            set_data_status(con, city.id, "stations", "live", f"live gap-fill · {out['stations']} stations", out["stations"])
        del meas
    del frames
    gc.collect()
    return out


def _fill_weather(city: CityConfig, now) -> int:
    """Past 10 d analysis + 4 d forecast, both grids, one endpoint (past_days)."""
    from services.pipeline.meteo import FORECAST, HOURLY_WIND_ONLY, _fetch

    total = 0
    for grid, hourly in (("city", None), ("airshed", HOURLY_WIND_ONLY)):
        try:
            df = _fetch(
                city,
                FORECAST,
                {"past_days": PAST_DAYS, "forecast_days": FORECAST_DAYS},
                "forecast",
                ttl=timedelta(hours=1),
                grid=grid,
                hourly=hourly,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{city.id}] livefill weather {grid} failed: {exc}")
            continue
        if df.empty:
            continue
        # Rows at or before "now" are analysis of what happened — the feature
        # builder and wind field read kind='hist'. Ahead of now stays 'forecast'
        # so model_frame picks it up as fx_* at the target hour.
        df.loc[pd.to_datetime(df["ts"], utc=True) <= now, "kind"] = "hist"
        with write_conn() as con:
            total += upsert_df(con, "weather_hourly", df, ["city", "grid", "grid_i", "grid_j", "ts", "kind"])
        del df
        gc.collect()  # each grid iteration should not still be holding the last one's frame
    with write_conn() as con:
        set_data_status(con, city.id, "weather", "live" if total else "unavailable",
                        f"live gap-fill · {total} rows (±{PAST_DAYS}/+{FORECAST_DAYS}d)", total)
    return total


def _fill_fires(city: CityConfig, now) -> int:
    from services.pipeline import firms

    if not firms.available():
        return 0
    try:
        df, status = firms.fetch_fires(city, days=7)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[{city.id}] livefill FIRMS failed: {exc}")
        return 0
    n = 0
    if not df.empty:
        with write_conn() as con:
            n = upsert_df(con, "fires", df, ["city", "fire_id"])
            set_data_status(con, city.id, "fires", status, f"live gap-fill · {n} detections (7d)", n)
    del df
    gc.collect()
    return n


def fill_city(city_id: str, scout: bool = True) -> dict:
    """Fetch all live layers for `city_id` and score the current hour.

    `scout=True` also sweeps Tavily+Bedrock for construction/incidents/GRAP —
    so one click of "Live · today" assembles the complete present-day picture,
    whether it's clicked today or 25 days from now.
    """
    s = get_settings()
    city = load_city(city_id)
    now = s.now()
    logger.info(f"[{city_id}] live gap-fill for {now:%Y-%m-%d %H:%M UTC}…")

    # Sequential, not parallel: each stage's pandas frames are scoped to its own
    # function and freed (gc.collect()) before the next stage starts, so peak
    # memory is one stage's footprint, not the sum of all four.
    meas = _fill_measurements(city, now)
    wx = _fill_weather(city, now)
    fires = _fill_fires(city, now)

    scouted = 0
    if scout and s.scout_enabled:
        try:
            from vayu_core.scout import run_scout

            scouted = run_scout(city_id).written
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{city_id}] livefill scout failed: {exc}")
    gc.collect()

    # Invalidate the API's per-city caches that were built from pre-fill data.
    from . import compute

    compute.wind_field.cache_clear()
    compute.city_wind.cache_clear()
    compute._fires.cache_clear()

    from .scoring import ensure_forecasts, reset_forecaster

    reset_forecaster()
    run_ts = ensure_forecasts(city_id, now)

    result = {
        "city": city_id,
        "now": now.isoformat(),
        "stations": meas["stations"],
        "measurement_rows": meas["rows"],
        "weather_rows": wx,
        "fire_rows": fires,
        "scouted": scouted,
        "forecast_run_ts": run_ts.isoformat() if run_ts else None,
    }
    logger.success(f"[{city_id}] live gap-fill done: {result}")
    return result


def fill_city_async(city_id: str) -> bool:
    """Kick a fill in a background thread (used by the mode toggle). Returns
    False if one is already running for this city."""
    with _lock:
        if city_id in _running:
            return False
        _running.add(city_id)

    def _run():
        try:
            fill_city(city_id)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{city_id}] live gap-fill crashed: {exc}")
        finally:
            with _lock:
                _running.discard(city_id)

    threading.Thread(target=_run, name=f"livefill-{city_id}", daemon=True).start()
    return True


def filling(city_id: str) -> bool:
    with _lock:
        return city_id in _running


def active() -> list[str]:
    """Cities with a gap-fill in flight — the UI polls this to know when to
    refetch after switching to live."""
    with _lock:
        return sorted(_running)
