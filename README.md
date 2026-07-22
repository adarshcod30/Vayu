# VAYU — Verifiable Airshed Intelligence & Enforcement

**Dashboards measure pollution. VAYU prosecutes it.**

India runs 900+ air-quality monitoring stations, yet a 2024 CAG audit found **69% of
monitored cities have no actionable response protocol** connected to those readings.
Existing systems stop at measurement (CPCB SAMEER), forecast (SAFAR, 4 cities), or
attribution without action (IITM's Delhi DSS — Delhi-only, winter-only,
supercomputer-bound). VAYU closes the loop, end to end, on a laptop:

```
READING → RESPONSIBLE SOURCE → RANKED INTERVENTION → ENFORCEMENT ORDER → VERIFIED OUTCOME
```

Its atomic unit of value is not a chart — it is an **Intervention Order**: a
dispatch-ready evidence dossier (PDF, with a map, an evidence table, a regulation
citation, a predicted impact and a sign-off block) that a commissioner can act on and
that VAYU later checks actually worked.

> _Golden-flow demo GIF placeholder — `docs/demo.gif`._

## What works

All six build phases are complete. Every route below is live for **Delhi and Lucknow**,
running fully offline on bundled data with zero API keys:

| Surface | What it does |
|---|---|
| **Command Center** (`/`) | Live ward choropleth, stations, hazard alerts, KPIs; Delhi↔Lucknow in <2 s |
| **Interventions** (`/interventions`) | ROI leaderboard, expandable counterfactuals, one-click dispatch → dossier PDF, GRAP Autopilot card |
| **Inspector** (`/inspector`) | Mobile order list, evidence checklist, dossier download, mark-executed |
| **Verify** (`/verify`) | Difference-in-differences: predicted vs. observed, with a confidence interval and a null-result verdict when honest |
| **Citizen** (`/citizen`) | Public AQI + clean-hours + health advisories in **English, हिंदी, ਪੰਜਾਬੀ** |
| **Methodology** (`/methodology`) | Backtest tables, the formulas, and a limitations section written for a skeptical judge |
| **Agent Activity drawer** | Streams every automated decision with its reasoning and confidence (SSE) |

## Forecast backtest (real numbers)

Rolling-origin holdout — the last 30 days are held out entirely; models see only data
before each issue time. Compared against two honest baselines. From `make backtest` /
`/api/v1/meta/evaluation`:

| Model (t+24 h) | RMSE | MAE | Crossing precision | Crossing recall |
|---|---:|---:|---:|---:|
| **VAYU** (LightGBM quantile) | **85.9** | **58.1** | 85% | 84% |
| Persistence (tomorrow = today) | 86.1 | 59.6 | 86% | 84% |
| Climatology (seasonal normal) | 114.1 | 92.2 | 73% | 91% |

**Read honestly:** at 24 h, persistence is a genuinely strong PM2.5 baseline. VAYU beats
it by a narrow margin on error and matches it on the crossing recall an operator cannot
afford to miss. We report the close race rather than cherry-pick a horizon. Interval
calibration (p10–p90, target 80% coverage): **77.3% / 75.1% / 68.2%** at 24/48/72 h —
well-calibrated near-term, slightly overconfident at 72 h, stated not smoothed.

## How VAYU differs

| | CPCB SAMEER | SAFAR | IITM Delhi DSS | Dashboards | **VAYU** |
|---|:---:|:---:|:---:|:---:|:---:|
| Measurement | ✅ | ✅ | ✅ | ✅ | ✅ |
| Forecast | — | ✅ (4 cities) | ✅ | some | ✅ |
| Source attribution | — | — | ✅ (Delhi, winter) | — | ✅ |
| **Ranked intervention** | — | — | — | — | ✅ |
| **Dispatch-ready order** | — | — | — | — | ✅ |
| **Verified outcome** | — | — | — | — | ✅ |
| Runs on a laptop, any city | — | — | supercomputer | — | ✅ (1 config file) |

## 60-second quickstart

```bash
git clone <repo> && cd Vayu
cp .env.example .env      # every key is optional; the app runs with none
make seed                 # real data → data/samples → DuckDB, forecasts, demo records
make dev                  # API :8000 · web :3000
```

No API keys required, no signup. `make seed` pulls real ward boundaries, CPCB station
metadata, air-quality history and Open-Meteo weather, trains the forecaster, scores it,
and seeds the demo records — then runs fully offline. Adding `OPENAQ_API_KEY` and
`FIRMS_API_KEY` upgrades two layers from sample to live.

## Data sources & honesty statement

Every layer is real data from a free source. Anything modelled rather than measured says
so — in the database (`source`), in the API (`data_status`), and on a pill in the UI.

| Layer | Source | Key? |
|---|---|---|
| Ward boundaries — 290 Delhi, 112 Lucknow | DataMeet municipal spatial data | no |
| Station identity + current AQI | CPCB CAAQMS via data.gov.in | no (public demo key) |
| Historical hourly AQ | ECMWF CAMS reanalysis via Open-Meteo | no |
| Weather (history + forecast) | Open-Meteo | no |
| Roads / industry / schools | OpenStreetMap (Overpass) | no |
| Measured station history *(upgrade)* | OpenAQ v3 | `OPENAQ_API_KEY` |
| Fire detections | NASA FIRMS VIIRS | `FIRMS_API_KEY` |

Findings we surface rather than hide (see `/methodology` and `docs/DATA_PROVENANCE.md`):

- **CPCB publishes sub-indices, not concentrations**, despite field names that say
  otherwise. Read naively, every Delhi station reads "AQI 500 Severe" in monsoon. VAYU
  inverts the published CPCB breakpoint table.
- **Delhi's November stubble burns 200–300 km upwind in Punjab** — beyond a Gaussian
  plume's 50 km range and outside municipal jurisdiction. VAYU declines to fabricate an
  averted-µg/m³ number and issues an escalation advisory to CAQM instead.
- **Ward population is split equally**, per the delimitation principle (wards are drawn
  to equal population) — not by polygon area, which inverts it.
- The bundled demo record's diff-in-diff verdict comes out **statistically insignificant**
  ("not distinguishable from the weather"), and we show that rather than claim a win.

The demo clock (`DEMO_NOW=2025-11-03T06:00Z`) is pinned to a real stubble-season episode:
Delhi is Very Poor and forecast to stay there, with hundreds of wards crossing AQI 300.

## Evaluation focus (where to look)

| Judging dimension | Where |
|---|---|
| Forecast skill vs. baselines | `/methodology`, `docs/evaluation.md`, `make backtest` |
| Attribution traceability | any ward → 100% of shares click through to evidence |
| Closed-loop / verification | `/verify` (diff-in-diff), the dossier PDF |
| Honesty & auditability | data pills, Agent Activity drawer, limitations section |
| Scalability | Delhi → Lucknow switch, one config file |
| Multilingual reach | `/citizen` — EN / हिंदी / ਪੰਜਾਬੀ |

## Architecture

```
apps/web/           Next.js 16 · React 19 · Tailwind · MapLibre · TanStack Query · Zustand
services/api/       FastAPI · pydantic · RFC7807 errors · SSE audit stream
services/pipeline/  ingestors, each retry → cache → bundled fallback; seed + demo records
vayu_core/          the science — AQI, geo/IDW, forecast (LightGBM), attribution (evidence
                    fusion + back-trajectory), dispersion (Gaussian plume), interventions
                    (ROI + dossier + GRAP), herald (advisories), verification (diff-in-diff)
data/vayu.duckdb    DuckDB — open it and check every number VAYU claims
```

A city is one config file. `config/cities/{delhi,lucknow}.json` are the only
city-specific artifacts; no code branches on a city id.

## Commands

```bash
make seed        # fetch/refresh data → DuckDB, train + score forecasts, seed demo records
make reseed      # force re-download
make dev         # API + web together
make test        # pytest — 256 tests
make lint        # ruff + tsc
make backtest    # regenerate docs/evaluation.md + charts
```

## Tests

`make test` — **256 passing**. The suite pins the claims that would silently corrupt an
enforcement order if they broke: the CPCB AQI conversion band-edge by band-edge; the
Gaussian plume against its closed form and mass conservation; the ROI ranking's
monotonicity and its refusal to recommend an upwind source; the diff-in-diff refusing to
credit the weather; and every advisory in all three languages never telling a citizen to
go outside in severe air.

## Team

Built for the ET AI Hackathon 2026.

---

_Prototype. Not an official government system. Regulation text is an abridged restatement
for demonstration — verify against the current CAQM order before any real enforcement._
