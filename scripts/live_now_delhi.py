"""Fast live nowcast pull: today's CPCB snapshot for Delhi, measurements only.

Skips the heavy historical-weather archive (that's the scheduled deploy job).
Enough to make live mode show today's REAL AQI. Run with DEMO_MODE=false.
"""
from loguru import logger

from vayu_core.config import get_settings, load_city
from vayu_core.db import init_db, set_data_status, upsert_df, write_conn
from services.pipeline import cpcb

MEAS_COLS = ["city", "station_id", "param", "ts", "value", "unit", "source"]

s = get_settings()
init_db()
city = load_city("delhi")
logger.info(f"live pull: demo_mode={s.demo_mode}  now={s.now():%Y-%m-%d %H:%M %Z}")

stations, current = cpcb.fetch_stations(city)  # live CPCB snapshot (fast)
logger.info(f"CPCB returned {len(stations)} stations, {len(current)} measurement rows")

with write_conn() as con:
    n_s = upsert_df(con, "stations", stations.drop(columns=["sensors"], errors="ignore"), ["station_id"])
    meas = current.reindex(columns=MEAS_COLS)
    n_m = upsert_df(con, "measurements", meas, ["city", "station_id", "param", "ts"])
    set_data_status(con, city.id, "measurements", "live", f"CPCB live · {len(current)} rows", n_m)
    set_data_status(con, city.id, "stations", "live", f"CPCB live · {n_s} stations", n_s)

# show the freshest pm25 readings we just stored
pm = current[current["param"] == "pm25"] if "param" in current else current
logger.success(f"stored {n_m} rows / {n_s} stations. latest ts={current['ts'].max() if not current.empty else 'n/a'}")
if not pm.empty:
    top = pm.sort_values("value", ascending=False).head(5)
    for r in top.itertuples():
        logger.info(f"  {r.value:.0f} µg/m³ PM2.5 @ {r.station_id}")
