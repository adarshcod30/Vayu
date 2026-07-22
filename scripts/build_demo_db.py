"""Build a small demo DuckDB that runs comfortably on a 512MB host.

The full seed DB is ~517MB — 2.4M measurement rows + 2.9M weather rows across
2016-2025, which existed to TRAIN the model. The model is already trained
(models/artifacts, in git), so the live demo needs none of that history: only
a window around each of the 5 curated demo dates (enough for the 10-day feature
lookback + 72h forecast horizon), plus the static layers and the 5 pre-scored
forecast runs. Everything past the archive still works — Live mode fetches it
fresh at click time. Result: a ~30-40MB DB that every query can touch without
OOM-ing the free tier.
"""
import duckdb, pathlib, datetime as dt

SRC = "data/vayu.duckdb"
DST = "data/vayu_demo.duckdb"
pathlib.Path(DST).unlink(missing_ok=True)

# 5 curated demo instants (UTC). Window: 14 days before (feature lookback +
# slack) to 4 days after (72h forecast + weather fx + buffer).
DEMO = ["2025-09-03T17:00:00Z","2025-09-17T17:00:00Z","2025-10-24T17:00:00Z",
        "2025-11-03T06:00:00Z","2025-11-24T00:00:00Z"]
windows = []
for s in DEMO:
    d = dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    windows.append((d - dt.timedelta(days=14), d + dt.timedelta(days=4)))

def in_windows(col):
    return " OR ".join(f"({col} >= TIMESTAMPTZ '{a.isoformat()}' AND {col} <= TIMESTAMPTZ '{b.isoformat()}')"
                       for a,b in windows)

from vayu_core.db import SCHEMA
con = duckdb.connect(DST)
con.execute(SCHEMA)
con.execute(f"ATTACH '{SRC}' AS src (READ_ONLY)")

# Time-filtered heavy tables
con.execute(f"INSERT INTO measurements  SELECT * FROM src.measurements  WHERE {in_windows('ts')}")
con.execute(f"INSERT INTO weather_hourly SELECT * FROM src.weather_hourly WHERE {in_windows('ts')}")
con.execute(f"INSERT INTO fires         SELECT * FROM src.fires          WHERE {in_windows('acq_ts')}")
# Forecasts: keep only the historical demo runs (< 2026); Live re-scores today's.
con.execute("INSERT INTO forecasts SELECT * FROM src.forecasts WHERE run_ts < TIMESTAMPTZ '2026-01-01T00:00:00Z'")
# Static / small tables copied whole
for t in ["stations","wards","ward_roads","permits","attributions","interventions",
          "verifications","grap_drafts","data_status","scouted_evidence"]:
    con.execute(f"INSERT INTO {t} SELECT * FROM src.{t}")
# audit_log has a sequence-backed id — copy explicit columns
cols = [r[1] for r in con.execute("PRAGMA table_info(audit_log)").fetchall()]
con.execute(f"INSERT INTO audit_log ({','.join(cols)}) SELECT {','.join(cols)} FROM src.audit_log")

con.execute("DETACH src")
for t in ["measurements","weather_hourly","fires","forecasts"]:
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"{t:16} {n:>9,}")
con.close()

# CHECKPOINT + reconnect to compact
con = duckdb.connect(DST); con.execute("CHECKPOINT"); con.close()
mb = pathlib.Path(DST).stat().st_size/1e6
print(f"\ndemo DB: {DST}  {mb:.1f} MB")
