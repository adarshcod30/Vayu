# How VAYU works — end to end

A plain-language walkthrough of the whole system: what data goes in, how the
model is trained, how it forecasts, how it finds the cause, how it decides what
to do, and how it checks whether it worked. Written so that when we move toward
**live use** (e.g. Nov 2026, pollution rising → "what do I do today, what happens
tomorrow, why is it happening"), you know exactly which part answers which
question.

Everything below points at the real code so you can read along.

---

## 0. The one-sentence version

VAYU turns **a pollution reading** into **a specific, evidence-backed enforcement
order**, and then **checks the order worked** — for any Indian city, from one
config file, on a laptop.

The loop:

```
READING  →  FORECAST  →  RESPONSIBLE SOURCE  →  RANKED INTERVENTION  →  ORDER  →  VERIFIED OUTCOME
 (now)     (tomorrow)      (why / who)            (what to do)         (PDF)      (did it work)
```

Each arrow is a component. Your live-use questions map onto them directly:

| Your question (live day) | Component | File |
|---|---|---|
| "What's the air right now?" | Observations (IDW snapshot) | `vayu_core/observations.py` |
| "What happens tomorrow / +48h?" | **Forecaster** | `vayu_core/forecast/` |
| "Why is it bad — real cause & factors?" | **Attributor** | `vayu_core/attribution/` |
| "What do I do today, ranked?" | **Interventions (ROI)** | `vayu_core/interventions/roi.py` |
| "Give me the order to dispatch" | **Dossier + GRAP** | `interventions/dossier.py`, `grap.py` |
| "Did it actually help?" | **Verifier (diff-in-diff)** | `vayu_core/verification/` |
| "Tell citizens what to do" | **Herald** | `vayu_core/herald.py` |

---

## 1. The clock — the single most important concept

Everything is computed relative to **one instant, `now`**.

```python
get_settings().now()   # vayu_core/config.py
```

In `DEMO_MODE=true` this is pinned to `DEMO_NOW` (currently `2025-11-03T06:00Z`)
so the whole app is deterministic and rehearsable. In a live deployment you'd set
`DEMO_MODE=false` and `now()` returns the real wall clock.

**Nothing in the science is hard-coded to a date.** The forecaster, attributor,
interventions, and verifier all take `at` (an instant) as a parameter and query
the database relative to it. That's why the same code that runs the Nov 2025 demo
will run a live Nov 2026 day — you feed it a different `now` and fresh data.

---

## 2. The data layer — what goes in

All data lands in one file: **`data/vayu.duckdb`** (DuckDB — you can open it and
inspect every number). It's filled by the ingest pipeline (`services/pipeline/`),
each source with a `retry → cache → bundled-fallback` chain so the app runs
offline.

| Table | What | Real source |
|---|---|---|
| `wards` | 290 Delhi / 112 Lucknow ward polygons + centroids + population | DataMeet |
| `stations` | monitor identity + location | CPCB / OpenAQ |
| `measurements` | hourly PM2.5 / PM10 / NO₂ per station | OpenAQ (measured) or CAMS reanalysis |
| `weather_hourly` | wind, boundary-layer height (PBLH), temp, humidity, etc. — history **and forecast** | Open-Meteo |
| `fires` | satellite fire detections (lat/lon/FRP/time) | NASA FIRMS VIIRS |
| `ward_roads` | road density per ward (traffic proxy) | OpenStreetMap |
| `permits` | construction sites (the one synthetic layer) | curated on OSM landuse |
| `forecasts` | model output per (ward, horizon) — **written by the pipeline** | computed |
| `attributions`, `interventions`, `verifications`, `grap_drafts`, `audit_log` | the loop's outputs | computed |

Two honesty notes baked into the data:
- CPCB publishes **sub-indices, not concentrations**; `vayu_core/aqi.py` inverts
  the published CPCB breakpoint table so a reading isn't mis-scaled.
- The offline history is **CAMS reanalysis** (physically-modelled, ~40 km grid)
  unless you add an OpenAQ key, which upgrades it to measured station data.

---

## 3. The Forecaster — "what happens tomorrow"

Files: `vayu_core/forecast/features.py`, `model.py`, `run.py`.

### 3a. What the model looks at (features)

One row per **(station, hour)**. `FEATURE_COLUMNS` in `features.py` — ~54 features
in four groups:

1. **PM2.5 history (lags & rollings)** — `pm25_lag1,3,6,12,24,48`, `pm25_roll6,24`,
   `pm25_delta_24h`. Strictly shifted so row `t` only ever sees `t` and earlier
   (no leakage). Also `pm10_lag1`, `no2_lag1`.
2. **Time** — `hour_sin/cos`, `dow`, `month`, `is_holiday`. Encodes the diurnal
   cycle and seasonality.
3. **Weather, twice** (this is the crux):
   - `<var>` = weather **at issue time `t`** (wind, `pblh`, `vent_index`, …).
   - `fx_<var>` = weather **forecast at the target hour `t + horizon`**. This is
     what actually decides the answer — a Delhi build-up is made by *tomorrow's*
     wind and mixing height, not today's. Open-Meteo publishes a 4-day forecast,
     so at issue time we genuinely know predicted wind at +72h. Not leakage: a
     live deployment really has this, and the backtest uses it too, so the
     reported skill is the skill you'd actually get.
   - `fx_d_*` = the **change** between now and then ("wind about to drop" is a
     stronger signal than either endpoint).
4. **Transport / upwind** — `upwind_pm25` (the nearest upwind station's current
   value), and fire features: `upwind_fire_frp_24h` (local, ≤50 km) and
   `upwind_fire_frp_regional_48h` / `_count_` (regional, 50–300 km, ±30° cone).
   The regional window is what lets the model see **Punjab stubble 200–300 km
   upwind** — the event that drives Delhi's November smog.

### 3b. How it's trained

`model.py` → `train()`. **LightGBM gradient-boosted trees, quantile objective.**

- **9 models**: 3 horizons (24/48/72 h) × 3 quantiles (p10/p50/p90). The quantiles
  are the point — a commissioner needs the *band*, not a false-precision single
  number. "p90 crosses 300" is an operational fact even when p50 doesn't.
- **Pooled across cities** with a `city_code` feature. This is what makes a new
  city viable on day one: Lucknow's ~6 stations can't learn a seasonal cycle
  alone, so it inherits the pooled model while its own features still steer it.
- **Residual target — the single most important design choice.** The model
  predicts the **change** `y − pm25(t)`, not the level. Prediction =
  `pm25(t) + delta`.

  Why: trees are piecewise-constant and **cannot extrapolate**. The holdout
  (stubble season, mean 205 µg/m³) is 3.6× hotter than training (mean 57). A
  level-target model asked about 400 returns the highest leaf it ever saw
  (~150–200) and under-predicts exactly the severe episodes we care about — it
  *lost to persistence by 53% on RMSE*. Predicting the residual fixes it
  structurally: the delta distribution is near-stationary across regimes,
  persistence becomes the model's natural zero (delta=0 *is* persistence, so it
  learns corrections to a strong baseline), and the level anchor carries the
  regime so a 500 µg/m³ morning is representable even though no training row
  reached it.

Training data includes **past stubble winters (2016–2018)** so the model has
actually seen a November; without them it had never learned the mechanism
(stagnation under an inversion) that makes November bad.

### 3c. How it forecasts (inference) — `run.py` → `run_forecast(city, …, at)`

For a given `now = at`:

1. `build_features(...)` builds the feature table from measurements/weather/fires.
2. `_latest_station_rows(feats, at)` takes each station's most recent row **at or
   before `at`** — this is "the state of the air being handed over."
3. For each horizon (24/48/72 h): attach the **weather forecast valid at
   `t+horizon`** (`model_frame`), then `fc.predict()` runs the p10/p50/p90 models.
   Output is per **station**.
4. **IDW interpolation** (`vayu_core/geo.py`, power=2, k=5 nearest) spreads the
   station predictions onto **ward centroids** — because we forecast at stations
   but act on wards. It also returns distance-to-nearest-station so far wards can
   be flagged low-confidence.
5. Band ordering (p10 ≤ p50 ≤ p90) is re-enforced after interpolation, AQI is
   computed from p50, and a **crossing ETA** (first horizon where AQI > 300) is
   recorded. Rows are written to the `forecasts` table.

**Key fact for live use:** `run_forecast` takes any `at`. Point it at a live
`now` with fresh data and it forecasts tomorrow. (Cost today: ~80 s per city,
because `build_features` rebuilds over all history — that's the thing to optimize
for a snappy live/date-picker experience; scoping features to a recent window
gets it to seconds.)

### 3d. How good is it (honest)

`make backtest` → `docs/evaluation.md` and `/methodology`. Rolling-origin, last
30 days held out entirely. At t+24 h: VAYU RMSE **85.9** vs persistence 86.1 vs
climatology 114.1; crossing recall 84%. Persistence is a genuinely strong 24 h
PM2.5 baseline; VAYU beats it narrowly and matches its hazard recall. p10–p90
band coverage 77/75/68% at 24/48/72 h (target 80%) — well-calibrated near-term,
slightly overconfident at 72 h. **We report the close race rather than hide it.**

### 3e. Why LightGBM — not an LSTM, GNN, or Transformer

The model was chosen to fit the **data and the constraints**, not the trend.
LightGBM wins on every axis that matters for *this* problem; the deep-learning
options lose on most of them.

1. **The data is small and sparse — the deciding factor.** Delhi has ~52
   stations, Lucknow ~6. That is the entire spatial signal.
   - **GNNs** learn by message-passing over a graph of nodes; ~52 nodes is not a
     graph worth learning. They earn their keep with hundreds-to-thousands of
     nodes, and here would overfit for no gain.
   - **LSTMs / Transformers** are data-hungry sequence learners; a few years of
     hourly data over 58 stations is far short of what they need to beat a
     well-engineered tabular model.
   - **GBDTs** are the empirically dominant class for small/medium **tabular**
     data (Grinsztajn et al., 2022) — which is exactly what we have.

2. **The signal is tabular, not sequence- or graph-shaped.** What drives the
   forecast is `pm25_now` + lag/rolling history + calendar + **tomorrow's
   forecast weather** (`fx_*`). A heterogeneous feature table where the dominant
   relationship is "today's level + tomorrow's wind/mixing height → the change."
   That is a GBDT's home turf.

3. **We didn't ignore space/physics — we used the right tool for each.** The
   spatiotemporal structure IS handled, just not by the forecaster: IDW for
   spatial spread, back-trajectory for advection, Gaussian plume for dispersion.
   A GNN would try to *learn* advection/dispersion from 52 nodes; we already
   *know* that physics, so we inject it directly and let the ML do only the
   pointwise temporal prediction — a far better use of scarce data.

4. **We need calibrated uncertainty bands.** The product is p10/p50/p90, not a
   point. LightGBM has a native quantile objective (one parameter). Getting
   well-calibrated, non-crossing quantiles from an LSTM/GNN means pinball loss and
   careful training — more fragility for a band we otherwise get for free.

5. **"Laptop, no supercomputer, new city on day one."** LightGBM trains in
   seconds-to-minutes on CPU; LSTMs/GNNs want a GPU and long runs — which would
   undercut the differentiator vs. IITM's supercomputer-bound DSS. Pooling cities
   with a `city_code` feature lets a 6-station city inherit the shared model; a
   GNN needs a per-city graph with enough nodes to learn.

6. **Auditability.** GBDTs give faithful SHAP attributions ("driven by tomorrow's
   collapsing mixing height + upwind fires"), feeding the "why" and the audit
   trail. Neural nets are genuinely harder to explain honestly.

**Where deep models WOULD win (honest):** hundreds+ of dense sensors → GNN;
long rich per-node sequences + GPU + much more data → LSTM/Transformer; satellite
imagery → CNN; a research budget → physics-informed GNN (advection-diffusion on a
graph). And trees have one real weakness — they can't extrapolate — which is
exactly why we predict the *residual* (§3b); an LSTM extrapolates levels more
naturally, but that single edge doesn't outweigh everything above, and the
residual reframing neutralizes it.

**Bottom line:** given ~58 stations, tabular heterogeneous features, a need for
calibrated quantile bands, CPU/laptop deployment, interpretability, and multi-city
cold-start, LightGBM dominates — and the physics a GNN would try to learn from too
little data is injected directly where it belongs. The backtest confirms it beats
persistence and climatology; a heavier model wouldn't have beaten *it* enough to
justify the cost, if at all, on data this small.

---

## 4. The Attributor — "why is it bad, real cause & factors"

Files: `vayu_core/attribution/trajectory.py`, `fusion.py`.

This is what turns "AQI is 380" into "42% of this ward's air is open burning,
here are the fire pixels." Two steps:

### 4a. Back-trajectory (`trajectory.py`)

Walk the air **backwards** from the ward along the wind field (`weather_hourly`,
the wide "airshed" grid), step by step, for N hours. This produces a **polyline**
(where the air came from) and a **cone** that widens with distance (uncertainty
grows upwind). If the wind is stagnant, there's no meaningful upwind — we say
"local sources dominant" instead of drawing a confident pie.

### 4b. Evidence fusion (`fusion.py`)

For each source category, score everything the cone passes through
(reproduced on `/methodology`):

```
S_burn        = Σ FRP · exp(−d/120km) · exp(−age/12h)        (FIRMS fires)
S_industry    = Σ area(industrial ∩ cone) · NO₂ anomaly       (OSM + S5P)
S_construction= Σ (2 if non-compliant else 1) · exp(−d/10km)  (permits)
S_traffic     = road_density · rush_hour(t) · NO₂ uplift      (OSM + CPCB)
S_regional    = (cone length outside city / total) · PM proxy

share_k = S_k / Σ S
```

Every term is **measured** (fire radiative power, NO₂, road length, geometry) or
a **documented constant**. Nothing is tuned to flatter the demo; the scale
factors are calibrated so a Delhi winter ward lands inside the published IITM DSS
/ SAFAR apportionment ranges, and `make backtest` reports where our shares
actually fall against those ranges.

Each share carries a **confidence** and the **evidence list** (real coordinates,
timestamps, FRP), so every percentage clicks through to the fire pixel or permit
behind it. That traceability is the product.

One documented deviation: fire decay is **120 km, not 20 km** — because Punjab
stubble sits 200–300 km upwind and a 20 km decay makes it arithmetically zero.

---

## 5. Interventions — "what do I do today, ranked"

Files: `vayu_core/dispersion/gaussian_plume.py`, `interventions/roi.py`.

Attribution says *who*. Interventions says *what to do, and is it worth it*.

### 5a. Dispersion counterfactual (the plume)

For a candidate action (halt this fire cluster / stop this site), run a **Gaussian
plume**: source running vs. source halted, stepped through the 48 h wind forecast.
The difference is the **µg/m³ averted** at the ward. Emission rates come from
published factors (fire FRP → Wooster 2005 + Andreae & Merlet 2001; industry
anchored to SAFAR's Delhi inventory). Hard limit: a straight-line plume is only
trusted to **50 km**; beyond that VAYU refuses to size the source and escalates to
CAQM instead (this is why Delhi's November stubble shows as "not yours to fix").

### 5b. ROI ranking

```
ROI = (µg/m³ averted at t+24h)  ×  (people protected)  ÷  (teams required)
```

Sorted descending, ties broken toward lower effort. Every row traces back through
evidence to a real coordinate — nothing is invented to fill the table. The output
is a **leaderboard** (`/interventions`) plus **advisories** for sources you can't
act on locally (the honest "escalate to CAQM" case).

### 5c. The order + GRAP

- **Dossier** (`dossier.py`): one click renders a PDF — map, evidence table,
  regulation citation, predicted impact, order ID, sign-off block, prototype
  watermark. This is the atomic unit of value.
- **GRAP Autopilot** (`grap.py`): when the city AQI is forecast to cross a GRAP
  stage boundary within 48 h, it drafts that stage's measures with clause
  citations — and stops. A human must approve (bans construction / restricts
  vehicles city-wide), so it wears a "human-in-the-loop" badge.

---

## 6. The Verifier — "did it actually work"

Files: `vayu_core/verification/did.py`, `series.py`.

After an order is executed, the ward's PM2.5 falls — but air moves for reasons
that have nothing to do with enforcement. **Difference-in-differences** subtracts
what would have happened anyway, estimated from control wards matched on their
**pre-period behaviour only**:

```
observed = (target_after − target_before) − mean(control_after − control_before)
```

A 95% interval comes from a block bootstrap (n=500). A verdict whose interval
spans zero is reported as **"not distinguishable from the weather"** — the seeded
demo record comes out that way, and we show it rather than claim a win. This is
the arrow that can embarrass us, which is exactly why it ships.

**Live-use caveat:** verification needs ~48 h of observed data *after* the action.
On a live "today" that future data doesn't exist yet — it fills in two days later.

---

## 7. The Herald — "tell citizens what to do"

File: `vayu_core/herald.py`. Same forecast, translated into a ≤80-word,
audience-specific health advisory in **English / Hindi / Punjabi**, plus a 48 h
"clean hours" strip and the best window to be outside. Deterministic templates
(not LLM), so a public-health message is never a hallucination.

---

## 8. How it all runs together

- **Pipeline** (`services/pipeline/seed.py`): ingest → build features → train (if
  needed) → **score forecasts at `now`** → seed demo records → write `data_status`.
  `make seed` runs this; it's idempotent and cached.
- **API** (`services/api/`, FastAPI): reads the DuckDB and serves the surfaces.
  Attribution/interventions/citizen/grap **compute live** relative to `now()`;
  forecasts are read from the pre-scored `forecasts` table.
- **Frontend** (`apps/web/`, Next.js): Command Center, Interventions, Verify,
  Citizen, Inspector, Methodology, and the Agent Activity drawer (SSE audit
  stream). State: TanStack Query + Zustand.
- **Audit** (`vayu_core/audit.py`): every automated step is logged with reasoning
  + confidence — the trust surface.

The cascade (TRD §7): `pipeline_refresh → forecaster.run → [threshold events] →
attributor.run(ward) → enforcer.build_candidates → herald.draft` — each step
audited.

---

## 9. What "going live" actually requires (for the afternoon)

The science is already date-agnostic; live use is mostly a **data-freshness + speed**
problem, not a rewrite. Concretely:

1. **`DEMO_MODE=false`** → `now()` becomes the real clock. Everything re-anchors.
2. **Live ingest on a schedule** — the ingestors already fetch live (Open-Meteo,
   FIRMS, OpenAQ/CPCB all have real-time feeds). Run the pipeline on a cron (e.g.
   hourly) instead of once.
3. **Score forecasts faster** — the ~80 s/city feature rebuild needs scoping to a
   recent window (last ~30 days) so a live/date-picked forecast returns in
   seconds. This is the main engineering task.
4. **Verification lag is inherent** — outcomes fill in ~48 h after an action, by
   design. The "predicted vs observed" card is a T+2day artifact, always.
5. **Retrain periodically** — the model is validated through Nov 2025; for live
   2026 use it should be retrained on data through the present, and the backtest
   re-run so the reported skill stays honest.

The thing that makes a live Nov 2026 day work — "pollution rising, what do I do
today, what's tomorrow, why, and what's contributing" — is exactly steps 2 + 3:
fresh data on a schedule, and fast forecast scoring. The forecasting, attribution,
intervention, and citizen logic are unchanged.

---

_Read the code alongside this: `vayu_core/` is the science, `services/` is the
plumbing, `apps/web/` is the UI, `data/vayu.duckdb` is every number VAYU claims._
