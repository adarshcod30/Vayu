# VAYU — going-live plan (Phase L)

Turning the pinned-demo prototype into a live, deployed system: real current
data, live 0/24/48/72 h forecasts, an LLM+web-search evidence scout for the
layers that have no API (fire/construction/incident), Delhi-**NCR** coverage,
light/satellite basemaps with the official India boundary, and a deployment shape
that doesn't ship heavy files.

**Framing fact:** the science layer is already date-agnostic (every component
takes `at`), and the ingestors already have live-fetch paths. Going live is
**scheduling + speed + data residency + two new capabilities (NCR, scout)** — not
a rewrite.

---

## Target architecture

```
   EventBridge cron              AWS
   ┌─────────────┐      ┌───────────────┐      ┌────────────────┐
   │ hourly      ├─────▶│ Ingest+Score  │─────▶│  S3 data lake  │
   │ 6-hourly    │      │ (Fargate task)│      │ raw/ curated/  │
   │ weekly      ├─────▶│ Retrain+gate  │─────▶│ models/ hot.db │
   └─────────────┘      └───────────────┘      └───────┬────────┘
                                                       │ pull on boot
   Bedrock (Claude) ◀── scout job ──▶ search API       │
   Tavily/Brave                                ┌───────▼────────┐
                                               │ API service    │
                                               │ FastAPI + hot  │
                                               │ DuckDB + SSE   │  ?as_of=<ts>
                                               └───────┬────────┘
                                                       │ HTTPS
                                            Vercel ◀───┘  (Next.js web)
```

**Core principle — S3 is the source of truth; nothing heavy in git or the image.**
Repo carries code only. API pulls a "hot" DuckDB (last ~90 days + static layers,
~200–400 MB) from S3 on boot. Full history is partitioned Parquet on S3, queried
directly via DuckDB `httpfs` for backtests. Solves "heavy files can't deploy."

---

## Phase L1 — Live core (the engine)

- [x] **L1a. Fast windowed scoring.** `build_features(..., since=)` builds only the
      ~10 days before `at` (all lag/fire windows need), cutting scoring from ~80s
      to ~1.5s per city. Windowed output is bit-identical to full-history
      (pinned by `tests/test_forecast_windowing.py`). **This also fixed a latent
      bug:** the nowcast was feeding decade-old readings (2016/2018 stations) into
      the current forecast; `_latest_station_rows` now enforces a staleness
      cutoff so only recently-reporting stations are sources. *(done)*
- [x] **L1b. Live clock + time-travel.** *(done)* A runtime clock override in
      `config.now()` (set via `POST /clock`, cleared to demo/wall-clock with
      `{"as_of":null}`). Every read surface now keys off **`current_run_ts`**
      (`services/api/scoring.py`) instead of `max(run_ts)`, so the nowcast,
      forecast, alerts, GRAP and ROI all move together to the chosen hour.
      Forecasts for a not-yet-scored hour are **scored on demand** (~1.5 s,
      windowed) and cached. Verified: pinning to 2025-10-25 scored 290 Delhi
      wards live and stamped `run_ts` to that hour. Frontend: `ClockControl` in
      the nav — live/demo/pinned badge, datetime picker bounded to data
      coverage, "jump to now".
- [x] **L1c. Scheduled ingest+score.** *(done — `services/jobs/refresh.py`,
      `make refresh`.)* Pull hot DB ← S3 → live ingest (reuses the graceful
      per-source seed path) → score the current hour via the fast windowed
      `ensure_forecasts` (no training-frame rebuild) → push hot DB → S3. Optional
      `--scout`. EventBridge `rate(1 hour)` target in deploy/DEPLOY.md.
- [x] **L1d. Weekly retrain + promotion gate.** *(done —
      `services/jobs/retrain.py`, `make retrain-gated`.)* Back up artifacts →
      retrain in place → backtest → **promote only if VAYU beats persistence at
      t+24h**, else roll back. Keeps the honest-numbers claim true in production.
- [~] **L1e. Freshness honesty:** `/clock` now reports `data_min`/`data_max`
      (coverage) and the pills already show live/cached/sample per source. The
      "· 22 min ago" relative-age string on each pill is the remaining polish.

## Phase L2 — NCR, basemaps, official boundary

- [x] **L2a. Delhi → Delhi-NCR.** *(done — 76 live stations, 333 H3 zones,
      ingested + model retrained on all 3 cities, verified in UI: current AQI 349,
      forecast 328 t+24h, interventions + GRAP working. Data pills mostly LIVE.)* `config/cities/delhi_ncr.json` created: bbox to
      the peripheral ring road (KMP/KGP: Kundli–Palwal–Bahadurgarh), **76 live
      NCR CPCB/OpenAQ stations** (vs 52 Delhi-only), covering Delhi, Gurugram,
      Faridabad, Ghaziabad, Noida, Gr. Noida, Bahadurgarh, Sonipat, Palwal,
      Baghpat/Loni, Bhiwadi, etc. Analysis units: **333 H3 res-6 zones** (no
      single ward dataset spans NCR's 19 municipalities; Delhi's 290 real wards
      remain in the `delhi` config — non-destructive). Station selection is
      **bbox-based** (CPCB `bbox mode`, added to `cpcb.py`). GRAP is legally
      NCR-wide so this is *more* correct. Delhi's 290 real wards + per-city
      municipal wards are the upgrade path.
      **IMPORTANT — city_code retrain:** `add_city_code` derives codes from
      `sorted(list_cities())`, so adding `delhi_ncr` shifts lucknow 1→2. The
      model must be **retrained** (`score --retrain`) after adding a city so all
      three codes are learned; otherwise Lucknow forecasts use an unseen code.
      *(ingest running; retrain pending)*
- [x] **L2b. Basemap switcher:** dark / light / satellite, done as a robust
      *visibility toggle* of three raster layers in one persistent style — NOT
      setStyle (which wipes VAYU's layers and hangs on the throttled render loop).
      Carto dark/light + Esri World Imagery, all keyless. Verified via the style
      API: all three basemap layers + six VAYU layers coexist, toggle flips
      cleanly, VAYU layers persist. Tiles don't paint in the headless preview
      pane (documented render-throttle), but render in a real browser.
- [~] **L2c. Official India boundary / Mappls.** At NCR/city zoom the national
      boundary isn't in frame, so the disputed-depiction issue doesn't arise on
      these views. Mappls (official depiction) slots in when
      `NEXT_PUBLIC_MAPPLS_KEY` arrives — as a 4th raster source in the same
      toggle (no setStyle), URL to be set with the key. Fallback (Carto/Esri) is
      live now.

## Phase L3 — Live evidence scout (LLM + web search, via Bedrock)

For the layers with **no API**: construction activity, GRAP stage in force,
incidents. A scheduled job pairing a **Bedrock Claude model** with a **search
API** (Bedrock has no built-in web search):

Implemented in `vayu_core/scout/` (search → Bedrock `converse` extraction →
persist) + `POST /scout/run`, `GET /scout`, promote/dismiss, and a **review-queue
page** (`/scout`). Bedrock (Nova Pro, `us.amazon.nova-pro-v1:0`) + Tavily REST
are configured and `/scout` reports `enabled:true`. All three scouts share one
extraction shape:

- [x] **L3a. GRAP-stage watcher** — query for the CAQM stage in force. *(done)*
- [x] **L3b. Construction scout** — query RERA / large-project + dust reports.
      *(done — the honest replacement for the synthetic permits layer.)*
- [x] **L3c. Incident sweep** — industrial fires, demolitions, stubble reports.
      *(done)*
- [x] **L3d. Guardrail** *(done)* — every item lands in `scouted_evidence` as
      `pending`, badged "web-scouted · unverified", in a human review queue. An
      LLM finding never becomes an order by itself; a person promotes or
      dismisses. Degrades to a clear "not configured" state without keys.

## Phase L4 — Hardening

- [ ] Secrets in SSM/Secrets Manager; CloudWatch alarms on ingest failure +
      staleness; Sentry on frontend.
- [ ] DB decision: DuckDB fine at this scale (single-writer). If transactional
      writes multiply, move interventions/audit/verifications to a small RDS
      Postgres, keep timeseries as Parquet/DuckDB. Don't do pre-emptively.
- [ ] Optional: GEE service account → turns on the S5P NO₂ layer.

---

## Keys & accounts

| Item | Status |
|---|---|
| CPCB (data.gov.in) key | ✅ provided, in `.env` |
| OpenAQ, FIRMS | ✅ in `.env` |
| Open-Meteo | keyless (free tier is non-commercial — revisit for official deploy) |
| Bedrock model id + access | ⏳ needed for L3 |
| Search API (Tavily/Brave) | ⏳ needed for L3 |
| AWS account + creds | ⏳ needed for L1c/L1d + deploy |
| Mappls **or** MapTiler key | ⏳ needed for L2b |
| GEE service account JSON | ⏳ optional (L4, S5P) |

**AWS IAM (minimum to run app + scout):** S3 `GetObject/PutObject/ListBucket/
DeleteObject` on the data bucket; Bedrock `InvokeModel` +
`InvokeModelWithResponseStream` (and "request model access" in the Bedrock
console). For deploy: ECS/Fargate, ECR, EventBridge, Secrets Manager,
CloudWatch Logs.

## Constraints that survive going live (stated, not hidden)

1. **Verification is inherently T+48 h** — needs after-data.
2. **Retrain before trusting live forecasts** — validated through Nov 2025;
   weekly retrain + promotion gate keeps the backtest honest.
3. **"Live" = last reading** (30–120 min; FIRMS ~3 h).
4. **Scouted evidence is advisory until a human promotes it.**

## Estimated run cost
~$30–60/month (Fargate service + spot tasks, S3, Vercel, EventBridge; Bedrock
scout a few $/mo at 4–6 runs/day).

## Build order
L1 → L2 → L3 → L4. L1a (fast scoring) first — done. L1b (live clock/date picker)
next; it's unblocked. L1c/d and L3 unblock when AWS creds + Bedrock model land.
