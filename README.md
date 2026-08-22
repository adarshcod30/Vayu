# VAYU — Verifiable Airshed Intelligence & Enforcement

**Dashboards measure pollution. VAYU prosecutes it — and now sees the whole country doing it.**

[![Live Demo](https://img.shields.io/badge/live%20demo-vayu--802568501157.asia--south1.run.app-22D3EE?style=for-the-badge)](https://vayu-802568501157.asia-south1.run.app)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/)
[![Next.js 16](https://img.shields.io/badge/next.js-16-black?style=flat-square)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688?style=flat-square)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/db-DuckDB-FFF000?style=flat-square)](https://duckdb.org/)
[![Tests](https://img.shields.io/badge/tests-324%20passing-brightgreen?style=flat-square)](#testing)
[![Deployed on Cloud Run](https://img.shields.io/badge/deployed-Google%20Cloud%20Run-4285F4?style=flat-square)](https://cloud.google.com/run)

> **[→ Open the live deployment](https://vayu-802568501157.asia-south1.run.app)** — no signup, no install. Everything described below is running there right now.

---

## Table of contents

- [About](#about)
- [The problem](#the-problem)
- [What VAYU does](#what-vayu-does)
- [Feature tour](#feature-tour)
- [System architecture](#system-architecture)
- [Tech stack](#tech-stack)
- [The national satellite layer (ISRO PS-3)](#the-national-satellite-layer-isro-ps-3)
- [Economic corridors](#economic-corridors)
- [Citizen reporting + Google Gemini](#citizen-reporting--google-gemini)
- [Data sources & API keys](#data-sources--api-keys)
- [Model performance](#model-performance)
- [How VAYU differs](#how-vayu-differs)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Deployment](#deployment)
- [Project structure](#project-structure)
- [Testing](#testing)
- [API reference](#api-reference)
- [Honesty & known limitations](#honesty--known-limitations)
- [Roadmap](#roadmap)
- [Project history](#project-history)
- [License](#license)

---

## About

VAYU started as a single-city ("Delhi, winter") air-quality prototype for the
**ET AI Hackathon 2026** and has since grown through two more targets, each one
adding a real capability rather than a coat of paint:

1. **ET AI Hackathon** — the original closed-loop engine: forecast → attribute
   → rank an intervention → dispatch an enforcement order → verify the outcome,
   for Delhi and Lucknow, on a laptop, with zero mandatory API keys.
2. **ISRO PS-3 ("Surface AQI & HCHO Hotspots from Satellite Data")** — pushed
   the same engine to **national scale**: a real 15,360-cell satellite grid
   over all of India (HCHO, NO₂, SO₂, CO, O₃, AOD), HCHO hotspot detection,
   VIIRS fire attribution, and a CNN-LSTM that predicts ground-level PM2.5
   from satellite inputs alone (Objective-1).
3. **Build with AI: Code for Communities** — added the pieces that make it a
   *federated, citizen-in-the-loop, Google-AI-native* platform: Gemini Vision
   reads citizen-submitted pollution photos, a corroboration engine
   cross-checks every citizen claim against independent satellite/fire
   evidence before trusting it, and five economic corridors turn the national
   grid into versioned bulletins any state agency can consume over plain HTTP.

Every phase's work is still live in the same codebase — nothing was thrown
away to build the next thing. The result is one system that answers three
different questions at three different scales: *"what should Delhi's
enforcement team do this afternoon"*, *"what does India's satellite record
say happened over the last 60 days"*, and *"can a citizen's photo be trusted
without anyone driving out to check."*

## The problem

India runs 900+ CAAQMS air-quality monitoring stations, yet a 2024 CAG audit
found **69% of monitored cities have no actionable response protocol**
connected to those readings. Existing systems stop at measurement (CPCB
SAMEER), forecast (SAFAR, 4 cities), or attribution without action (IITM's
Delhi DSS — Delhi-only, winter-only, supercomputer-bound). None of them close
the loop, none of them work outside a handful of metros, and none of them let
a citizen's own photo become verified evidence.

## What VAYU does

The atomic unit of value is not a chart — it is an **Intervention Order**: a
dispatch-ready evidence dossier (PDF, with a map, an evidence table, a
regulation citation, a predicted impact and a sign-off block) that a
commissioner can act on and that VAYU later checks actually worked.

```
READING → RESPONSIBLE SOURCE → RANKED INTERVENTION → ENFORCEMENT ORDER → VERIFIED OUTCOME
```

That loop runs at city scale (Delhi, Delhi-NCR, Lucknow) on real CPCB station
history. Layered on top of it, a second loop runs at country scale:

```
SATELLITE GRID → HOTSPOT / CNN-LSTM SURFACE AQI → CORRIDOR BULLETIN → CITIZEN CROSS-CHECK
```

## Feature tour

Every route below is live on the [deployed instance](https://vayu-802568501157.asia-south1.run.app):

| Surface | Route | What it does |
|---|---|---|
| **Command Center** | `/` | Live ward choropleth, stations, hazard alerts, trajectory/dispersion cone, KPIs; Delhi ↔ Lucknow in < 2 s |
| **Interventions** | `/interventions` | ROI-ranked leaderboard, expandable counterfactuals, one-click dispatch → dossier PDF, GRAP Autopilot card |
| **Inspector** | `/inspector` | Mobile order list, evidence checklist, dossier download, mark-executed |
| **Verify** | `/verify` | Difference-in-differences: predicted vs. observed, with a confidence interval and a null-result verdict when honest |
| **Corridors** | `/corridors` | Five national economic corridors, each with a versioned (`vayu.corridor.v1`) daily bulletin: satellite coverage, HCHO hotspots, fire counts, citizen corroboration |
| **Citizen report** | `/report` | Submit a pollution photo or sensor reading; Gemini Vision classifies it, satellite/fire evidence corroborates or flags it |
| **Public Citizen view** | `/citizen` | Public AQI + clean-hours + health advisories in **English, हिंदी, ਪੰਜਾਬੀ** |
| **Methodology** | `/methodology` | Backtest tables, the formulas, and a limitations section written for a skeptical judge |
| **Agent Activity drawer** | everywhere | Streams every automated decision with its reasoning and confidence (SSE) |

## System architecture

```
                     ┌─────────────────────────────────────────────┐
                     │         apps/web  (Next.js 16 / React 19)     │
                     │  Command · Interventions · Corridors · Report │
                     └───────────────────────┬───────────────────────┘
                                              │ /api/v1  (same-origin, proxied)
                     ┌───────────────────────▼───────────────────────┐
                     │            services/api  (FastAPI)             │
                     │  meta · cities · forecast · attribution ·      │
                     │  interventions · verification · citizen ·      │
                     │  citizen_reports · corridors · grap · audit    │
                     └──────┬───────────────────────────┬─────────────┘
                             │                            │
          ┌──────────────────▼───────────────┐  ┌─────────▼──────────────────┐
          │           vayu_core                │  │      services/pipeline      │
          │  aqi · geo/IDW · forecast          │  │  cpcb · openaq · firms ·     │
          │  (LightGBM) · attribution          │  │  meteo · osm · s5p (DLR) ·   │
          │  (evidence fusion + trajectory) ·  │  │  satellite (GEE) · seed ·    │
          │  dispersion (Gaussian plume) ·     │  │  live (periodic CPCB) ·      │
          │  interventions (ROI+dossier) ·     │  │  national                    │
          │  national/surface_aqi (CNN-LSTM) · │  └─────────────────────────────┘
          │  citizen (ingest+crosscheck) ·     │
          │  google_ai (Gemini client+vision)  │
          └──────────────────┬──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  data/vayu.duckdb   │   one embedded OLAP file —
                    │  (single-file OLAP) │   open it, check any number
                    └─────────────────────┘
```

A city is one config file. `config/cities/{delhi,delhi_ncr,lucknow}.json` and
`config/regions/india.json` / `config/corridors/india.json` are the only
place-specific artifacts; no code branches on a city or corridor id.

## Tech stack

| Layer | What | Why |
|---|---|---|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS, TanStack Query, Zustand | App Router SSR + one static build baked into the deploy image; TanStack Query owns all server-state caching, Zustand owns UI-only state (selected ward, layer toggles) |
| **Map** | MapLibre GL 5 (native vector/raster layers), deck.gl | Chosen over a deck.gl-only stack for reliable hit-testing, feature-state hover/selection and GPU-side data-driven styling with no version coupling between two GL renderers — see `MapCanvas.tsx`'s own design note |
| **Charts** | Recharts, Framer Motion | Forecast bands, ROI leaderboards, corridor stat tiles |
| **API** | FastAPI, Pydantic v2, Uvicorn | RFC 7807 problem+json errors everywhere; every route answers even against an unseeded DB |
| **Database** | DuckDB (single embedded file, no server) | Columnar OLAP fast enough to score 290 wards live and small enough to bake into a container image; `data/vayu.duckdb` — open it yourself |
| **Forecasting** | LightGBM (quantile regression, p10/p50/p90) | Rolling-origin backtested against persistence and climatology baselines, not just trained-and-trusted |
| **Surface-AQI ML** | PyTorch — a per-station CNN (3×3 satellite patch → spatial embedding) feeding an LSTM (5-day sequence + meteorology + lagged PM2.5) | Deliberately kept **out of the API's request path** — trained/scored offline, writes to `aqi_grid`, the live app never imports torch per request |
| **Attribution** | Evidence fusion (fires, industry, construction, traffic) + HYSPLIT-style back-trajectory + Gaussian dispersion cone | Every attribution percentage clicks through to the literal evidence point (lat/lon, timestamp, source) behind it |
| **Generative AI** | Google Gemini (`gemini-3.6-flash`) via plain REST, no SDK | Reads a citizen's photo into a structured `{is_outdoor, haze_severity, source_type, confidence}` observation — never asked to estimate a numeric AQI from a picture |
| **Satellite ingestion** | DLR Sentinel-5P L3 STAC (keyless: HCHO, SO₂, O₃, AOD) + Google Earth Engine (NO₂, CO, MODIS/MAIAC AOD) | Two independent sources unified through one `to_grid()` binning function into the same `satellite_grid` table |
| **Fire detections** | NASA FIRMS VIIRS | Both a per-city point table (ward-level attribution/evidence) and a national grid (corridor bulletins, hotspot cross-checks) |
| **Deployment** | Single-container Google Cloud Run (FastAPI + Next.js in one image, Next proxying `/api/v1` to a local FastAPI process) | One URL, no CORS, no cross-service latency — the whole demo behind one link |
| **CI-grade hygiene** | pytest, pytest-timeout, ruff | 324 tests; pytest-timeout added after two real multi-hour test hangs were found and fixed this session (see [Honesty & known limitations](#honesty--known-limitations)) |

## The national satellite layer (ISRO PS-3)

Built against ISRO's problem statement *"Surface AQI & HCHO Hotspots from
Satellite Data."*

- **Real national coverage.** A 0.25°×0.25° grid over all of India (bbox
  `[68, 6, 98, 38]`, ~15,360 cells), six pollutant channels: **HCHO, NO₂,
  SO₂, CO, O₃, AOD** — from DLR's keyless Sentinel-5P STAC (four channels)
  and Google Earth Engine (NO₂, CO, and MODIS/MAIAC AOD), unified through one
  shared `to_grid()` function so both sources land in the same
  `satellite_grid` table with the same schema.
- **HCHO hotspot detection.** A robust (MAD-based, not mean/std, so a handful
  of extreme days can't hide the rest) per-cell anomaly score against a
  60-day rolling baseline, cross-checked against VIIRS fire counts in the
  same cell/day.
- **Objective-1: surface AQI from satellite, via CNN-LSTM.** Per station-day,
  a small CNN reads a 3×3 satellite patch (5 channels — O₃ is deliberately
  excluded from training; see below) into a spatial embedding; an LSTM
  reads a 5-day sequence of that embedding plus meteorology and yesterday's
  PM2.5 into a predicted PM2.5 today. Trained and evaluated on the one
  corridor with real matched ground truth (Delhi, Delhi-NCR, Lucknow — 3,727
  station-days), with a genuine time-based holdout and a persistence
  baseline as the honesty check:

  | | RMSE (µg/m³) | MAE (µg/m³) | Pearson r |
  |---|---:|---:|---:|
  | **CNN-LSTM v1** | 51.14 | 39.01 | **0.838** |
  | Persistence baseline | 43.37 | — | — |

  Read honestly: **R = 0.838 is a genuinely strong satellite-driven signal**,
  but the model does not yet beat "today looks like yesterday" on RMSE for
  this holdout — reported in `docs/objective1_evaluation.json` rather than
  hidden. The satellite inputs are national; the *validated* claim is scoped
  to the one corridor with real CPCB + reanalysis history to check it
  against — extending that is a region-config change, not a rewrite (every
  other national layer in this codebase already works that way).

## Economic corridors

Pollution follows freight and wind, not municipal boundaries — the
Amritsar–Kolkata spine alone crosses seven states. `config/corridors/india.json`
defines five, each a route waypoints + buffer, producing a versioned
(`vayu.corridor.v1`), self-describing daily bulletin over plain HTTP:

| Corridor | States |
|---|---|
| Delhi–Mumbai Industrial Corridor (DMIC) | Delhi, Haryana, Rajasthan, Gujarat, Maharashtra |
| Amritsar–Delhi–Kolkata Corridor (the IGP stubble-burning spine) | Punjab, Haryana, Delhi, Uttar Pradesh, Bihar, Jharkhand, West Bengal |
| Chennai–Bengaluru Industrial Corridor (CBIC) | Tamil Nadu, Andhra Pradesh, Karnataka |
| Visakhapatnam–Chennai Industrial Corridor (VCIC) | Andhra Pradesh, Tamil Nadu |
| Bengaluru–Mumbai Economic Corridor (BMEC) | Karnataka, Maharashtra |

Every bulletin (`GET /api/v1/corridors/{id}/bulletin?date=`) carries units and
provenance on every number — `schema`, `coverage.coverage_pct` (so a cell the
satellite couldn't see is never mistaken for a clean one), `hcho`, `fire`,
`citizen`, and `top_hotspots` — so a state agency can consume it without
adopting VAYU's database, models, or code.

## Citizen reporting + Google Gemini

`/report` lets anyone submit a photo or a sensor reading. Two Gemini-backed
pieces make that trustworthy rather than just crowdsourced noise:

1. **Vision classification** (`vayu_core/google_ai/vision.py`) — Gemini reads
   the photo into a strict JSON schema: `is_outdoor`, `haze_severity`
   (clear → severe), `source_type` (crop burning, garbage burning, industrial
   plume, construction dust, vehicle exhaust, brick kiln, dust storm, none
   visible), and a confidence score. It is never asked for a numeric AQI —
   estimating a concentration from a photo is a claim the model can't back up.
2. **Independent-evidence corroboration** (`vayu_core/citizen/crosscheck.py`)
   — a citizen's report is only marked `corroborated` when the same
   grid-cell/day shows a real HCHO anomaly (≥ 2.5σ, the same threshold the
   hotspot detector uses) **and/or** a real VIIRS fire count — never by
   reporter reputation. The logic distinguishes four outcomes, including the
   easy-to-get-wrong case of *no fire pixel* (could be a small fire, or smoke
   that drifted in) from *actively contradicted*.

`GET /api/v1/citizen/reports` exposes `google_ai_enabled` explicitly, and the
whole pipeline degrades to an honest "unavailable" — never a guessed
reading — when no `GOOGLE_API_KEY` is configured.

The Gemini client itself (`vayu_core/google_ai/client.py`) is a plain REST
wrapper with real production hardening found by testing against the live
API: retry-with-backoff on 429/500/503 (immediate raise on 401/404), a
`maxOutputTokens` floor discovered because Gemini's "thinking" tokens can
silently consume the entire budget before any output token is emitted, and
JSON recovery for replies wrapped in prose or code fences.

## Data sources & API keys

Every layer is real data from a free or freely-tiered source. Anything
modelled rather than measured says so — in the database (`source` column),
in the API (`data_status`), and on a pill in the UI. **Every key below is
optional** — the app runs fully with none set (`make seed && make dev`).

| Layer | Source | Key needed? |
|---|---|---|
| Ward boundaries — 290 Delhi, 112 Lucknow | DataMeet municipal spatial data | no |
| Station identity + current AQI | CPCB CAAQMS via data.gov.in | no (ships with the portal's public demo key; `DATA_GOV_IN_API_KEY` gets you your own higher rate limit) |
| Historical hourly AQ | ECMWF CAMS reanalysis via Open-Meteo | no |
| Weather (history + forecast) | Open-Meteo | no |
| Roads / industry / schools | OpenStreetMap (Overpass) | no |
| National satellite grid — HCHO, SO₂, O₃, AOD | DLR Sentinel-5P L3 STAC | no |
| National satellite grid — NO₂, CO, MODIS/MAIAC AOD | Google Earth Engine | `GEE_SERVICE_ACCOUNT_JSON` |
| Fire detections (city + national) | NASA FIRMS VIIRS | `FIRMS_API_KEY` (falls back to a bundled 7-day CSV) |
| Measured station history *(upgrade)* | OpenAQ v3 | `OPENAQ_API_KEY` |
| Citizen photo classification, advisories | Google Gemini | `GOOGLE_API_KEY` (or `GOOGLE_CLOUD_PROJECT` for Vertex) |
| LLM advisories / GRAP RAG *(legacy path)* | Anthropic | `ANTHROPIC_API_KEY` |

Findings VAYU surfaces rather than hides (see `/methodology` and
`docs/DATA_PROVENANCE.md`):

- **CPCB publishes sub-indices, not concentrations**, despite field names
  that say otherwise. Read naively, every Delhi station reads "AQI 500
  Severe" in monsoon. VAYU inverts the published CPCB breakpoint table.
- **Delhi's November stubble burns 200–300 km upwind in Punjab** — beyond a
  Gaussian plume's 50 km local range and outside municipal jurisdiction.
  VAYU declines to fabricate an averted-µg/m³ number for that share and
  issues an escalation advisory to CAQM instead.
- **Ward population is split equally**, per the delimitation principle
  (wards are drawn to equal population) — not by polygon area, which
  inverts the ROI leaderboard.
- The bundled demo record's diff-in-diff verdict comes out **statistically
  insignificant** ("not distinguishable from the weather"), and VAYU shows
  that rather than claim a win.
- **The CNN-LSTM does not beat its own persistence baseline** on RMSE (see
  above) — reported plainly, not smoothed over by only quoting R.

## Model performance

**Short-term city forecast (LightGBM, quantile regression)** — rolling-origin
holdout, the last 30 days held out entirely, models see only data before each
issue time, compared against two honest baselines:

| Model (t+24 h) | RMSE | MAE | Crossing precision | Crossing recall |
|---|---:|---:|---:|---:|
| **VAYU** (LightGBM quantile) | **85.9** | **58.1** | 85% | 84% |
| Persistence (tomorrow = today) | 86.1 | 59.6 | 86% | 84% |
| Climatology (seasonal normal) | 114.1 | 92.2 | 73% | 91% |

At 24 h, persistence is a genuinely strong PM2.5 baseline — VAYU beats it by a
narrow margin on error and matches it on the crossing recall an operator can't
afford to miss. Interval calibration (p10–p90, target 80% coverage): **77.3% /
75.1% / 68.2%** at 24/48/72 h — well-calibrated near-term, slightly
overconfident at 72 h, stated not smoothed. Full charts in `docs/img/` and
`docs/evaluation.md`; regenerate with `make backtest`.

**National surface-AQI (CNN-LSTM, Objective-1)** — see
[The national satellite layer](#the-national-satellite-layer-isro-ps-3) above
for the full table and honest read.

## How VAYU differs

| | CPCB SAMEER | SAFAR | IITM Delhi DSS | Dashboards | **VAYU** |
|---|:---:|:---:|:---:|:---:|:---:|
| Measurement | ✅ | ✅ | ✅ | ✅ | ✅ |
| Forecast | — | ✅ (4 cities) | ✅ | some | ✅ |
| Source attribution | — | — | ✅ (Delhi, winter) | — | ✅ |
| **National satellite grid** | — | — | — | — | ✅ (15,360 cells) |
| **Surface AQI from satellite alone** | — | — | — | — | ✅ (CNN-LSTM) |
| **Citizen photo → verified evidence** | — | — | — | — | ✅ (Gemini + corroboration) |
| **Federated corridor bulletins** | — | — | — | — | ✅ (5 corridors, versioned) |
| **Ranked intervention** | — | — | — | — | ✅ |
| **Dispatch-ready order** | — | — | — | — | ✅ |
| **Verified outcome** | — | — | — | — | ✅ |
| Runs on a laptop, any city | — | — | supercomputer | — | ✅ (1 config file) |

## Getting started

```bash
git clone https://github.com/adarshcod30/vayu.git && cd vayu
cp .env.example .env      # every key is optional; the app runs with none
make seed                 # real data → data/samples → DuckDB, forecasts, demo records
make dev                  # API :8000 · web :3000
```

No API keys required, no signup. `make seed` pulls real ward boundaries, CPCB
station metadata, air-quality history and Open-Meteo weather, trains the
forecaster, scores it, and seeds the demo records — then runs fully offline.
Setting `GOOGLE_API_KEY` and `GEE_SERVICE_ACCOUNT_JSON` upgrades the citizen
Gemini analysis and the national NO₂/CO satellite layers from absent to live.

To train Objective-1's CNN-LSTM (a training/offline-scoring-only path, never
imported by the live API), install PyTorch separately — it is deliberately
excluded from `requirements.txt` so the deployed container doesn't carry its
weight:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m scripts.train_surface_aqi
```

## Environment variables

Full reference in [`.env.example`](.env.example). The short version:

| Variable | Default | What it unlocks |
|---|---|---|
| `DEMO_MODE` | `true` | `true` = bundled data, clock pinned to `DEMO_NOW`, deterministic/rehearsable demo. `false` = live wall clock + a periodic live CPCB refresh for the ground-truth cities |
| `DEMO_NOW` | `2025-11-03T06:00:00Z` | The pinned "now" in demo mode — a real, measured Delhi stubble-season episode |
| `DATA_GOV_IN_API_KEY` | *(public demo key)* | Your own data.gov.in rate limit for the CPCB CAAQMS feed |
| `OPENAQ_API_KEY` | — | Upgrades station history from CAMS reanalysis to OpenAQ v3 measurements |
| `FIRMS_API_KEY` | — | Live NASA FIRMS fire detections (else a bundled 7-day CSV) |
| `GOOGLE_API_KEY` | — | Enables Gemini: citizen photo classification, generated advisories |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Pinned, not `-latest` — see the code comment on why |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` | — / `asia-south1` | Vertex AI path instead of an AI Studio key |
| `GEE_SERVICE_ACCOUNT_JSON` | — | Path to a GCP service-account key — enables the national NO₂/CO/AOD (GEE) satellite ingestion |
| `ANTHROPIC_API_KEY` | — | Legacy live-LLM advisory path (pre-Gemini) |
| `NEXT_PUBLIC_MAPPLS_KEY` | — | Official India-boundary basemap (Mappls/MapmyIndia); falls back to Carto + Esri |
| `VAYU_DB_PATH` | `data/vayu.duckdb` | Which DuckDB file the app reads/writes |

**Never commit real keys.** `.env` and `secrets/` are gitignored; the deploy
scripts read keys from your shell/`.env` and pass them to Cloud Run as
`--set-env-vars` at deploy time, never baking them into the image.

## Deployment

VAYU ships as **one container** — FastAPI and the built Next.js app in the
same image, Next proxying `/api/v1` to a local FastAPI process on
`127.0.0.1:8000`. One URL for judges, no CORS, no cross-service latency.

```bash
# 1. Build a slim deploy database (trims 2016-era training history the
#    deployed app never reads; keeps satellite/fire/AQI layers whole)
python -m scripts.build_deploy_db

# 2. Deploy (gcloud auto-detects deploy/Dockerfile via the repo-root symlink)
gcloud run deploy vayu --source . --region asia-south1 \
  --allow-unauthenticated --memory 2Gi --cpu 2 --timeout 300 \
  --set-env-vars "GOOGLE_API_KEY=...,GEMINI_MODEL=gemini-3.6-flash,DEMO_MODE=true"
```

**Live instance:** **https://vayu-802568501157.asia-south1.run.app**

Two non-obvious things the deploy scripts handle for you:

- `gcloud run deploy --source .` only auto-detects a `Dockerfile` at the
  *repo root* — `deploy/Dockerfile` stays where it documents the whole deploy
  story, and a root-level `Dockerfile` symlink points at it.
- With no `.gcloudignore` present, `gcloud` silently falls back to
  `.gitignore` to decide what to upload — which excludes the deploy database
  itself (correctly, for git). `.gcloudignore` exists explicitly so that
  git-only exclusion doesn't also strip what the deployed image actually
  needs.

## Project structure

```
apps/web/            Next.js 16 · React 19 · Tailwind · MapLibre · TanStack Query · Zustand
  src/app/              one route per page: (command), interventions, corridors, report,
                        citizen, verify, inspector, methodology
  src/components/map/   MapCanvas.tsx — the declarative MapLibre layer registry

services/api/         FastAPI · pydantic · RFC7807 errors · SSE audit stream
  routers/              meta, cities, forecast, attribution, interventions, verification,
                        citizen, citizen_reports, corridors, grap, audit

services/pipeline/    ingestors — each retry → cache → bundled fallback
  cpcb.py, openaq.py, firms.py, meteo.py, osm.py     city-scale ingestion
  s5p.py                                              DLR Sentinel-5P (keyless)
  satellite.py                                        Google Earth Engine (NO2/CO/AOD)
  live.py                                             periodic live CPCB refresh (non-demo mode)
  national.py, seed.py                                national + city seeding

vayu_core/            the science
  aqi.py                CPCB sub-index → AQI, band-edge exact
  geo.py                IDW interpolation, grid snapping
  forecast/             LightGBM quantile forecaster + rolling-origin backtest
  attribution/           evidence fusion, back-trajectory, dispersion cone, ROI
  national/             satellite_aqi.py — the CNN-LSTM (Objective-1)
  citizen/               ingest.py, crosscheck.py — photo/sensor intake + corroboration
  google_ai/             client.py (Gemini REST), vision.py (photo classification)
  interventions/         ROI ranking, dossier PDF, GRAP autopilot
  verification/          difference-in-differences

config/
  cities/               one JSON per city — the only city-specific artifact
  regions/india.json    the national satellite grid definition
  corridors/india.json  the five economic corridors

scripts/
  build_deploy_db.py    slim DB for the container image
  train_surface_aqi.py  trains + evaluates the CNN-LSTM, writes aqi_grid

deploy/
  Dockerfile             single-container build (Next.js stage + Python runtime)
  start.sh                boots both processes

data/vayu.duckdb       DuckDB — open it and check every number VAYU claims
docs/                  DATA_PROVENANCE.md, HOW_IT_WORKS.md, evaluation.md/json,
                       objective1_evaluation.json
```

## Testing

```bash
make test        # pytest — 324 passing
make lint        # ruff + tsc
```

The suite pins the claims that would silently corrupt an enforcement order —
or a national bulletin — if they broke: the CPCB AQI conversion band-edge by
band-edge; the Gaussian plume against its closed form and mass conservation;
the ROI ranking's monotonicity and its refusal to recommend an upwind source;
the diff-in-diff refusing to credit the weather; every advisory in all three
languages never telling a citizen to go outside in severe air; the HCHO
hotspot detector's robustness to a collapsed-variance cell; the corridor
distance math's `cos(latitude)` correction; the citizen corroboration logic
never claiming "no fire" when fires are actually present; and the CNN-LSTM's
time-based train/holdout split never leaking future data backward.

`pytest-timeout` is wired in as a dev dependency after two real multi-hour
hangs were found and fixed this session — see
[Honesty & known limitations](#honesty--known-limitations).

## API reference

All routes are under `/api/v1`. Interactive docs at `/docs` (Swagger) and
`/openapi.json` on any running instance.

| Router | Key routes |
|---|---|
| `meta` | `GET /clock`, `POST /clock` (time-travel), `GET /health`, `GET /notable-dates` |
| `cities` | `GET /cities`, `GET /cities/{id}/current`, `GET /cities/{id}/wards.geojson`, `GET /cities/{id}/data_status` |
| `forecast` | `GET /cities/{id}/forecast?h=24\|48\|72` |
| `attribution` | `GET /cities/{id}/attribution/{ward_id}`, `GET /cities/{id}/trajectory/{ward_id}` |
| `interventions` | `GET /cities/{id}/interventions?ward_id=`, `POST /interventions/dispatch`, `POST /interventions/{id}/execute`, `GET /interventions/{id}/dossier` |
| `verification` | difference-in-differences results for dispatched orders |
| `citizen` | public advisory surfaces |
| `citizen_reports` | `POST /citizen/report/photo`, `POST /citizen/report/sensor`, `GET /citizen/reports` |
| `corridors` | `GET /corridors`, `GET /corridors/{id}/bulletin?date=` |
| `grap` | GRAP-stage autopilot + approval flow |
| `audit` | `GET /audit` — SSE stream of every automated decision |

## Honesty & known limitations

VAYU's whole design philosophy is *state the scope, don't imply more than the
data supports.* The concrete list, as of this README:

- **The CNN-LSTM doesn't beat persistence** on RMSE (it does show a strong
  R = 0.838). Stated in `docs/objective1_evaluation.json`, not hidden.
- **National coverage vs. validated coverage are different claims.** The
  satellite grid is genuinely national; ground-truth CPCB + reanalysis
  history to *validate* a model against exists only for Delhi/Delhi-NCR/
  Lucknow. Extending validated coverage is a region-config change, not a
  rewrite — but it hasn't happened yet.
- **Live CPCB fetch is blocked from Cloud Run's network.** `services/pipeline/live.py`
  was built, tested, and works correctly against real data — but
  `api.data.gov.in` rejects connections from Google Cloud's IP ranges
  specifically (works locally, fails identically for every city when
  deployed). The deployed instance therefore runs in `DEMO_MODE=true`
  (a real, complete Nov 2025 stubble-season snapshot) rather than showing an
  honestly-empty live AQI. Fixing this needs a different egress path
  (residential-IP proxy or different hosting network), not a code change.
- **The corridor/satellite view is a historical case study, not a live
  feed** — stated explicitly on `/corridors` itself. There's no standing
  scheduled ingestion job yet; every deploy bakes in a snapshot built at
  that moment.
- **Heat grid is a stub** (`Phase 6`), visibly marked "Soon" rather than a
  silently-dead toggle.
- Two real bugs were found by *testing the deployed app against a live
  network*, not by reading the code, and both are fixed: an unbounded
  `(hours × fires)` array in the forecast feature pipeline that
  out-of-memory'd once `measurements` grew to 9 years of history, and a
  macOS dual-OpenMP-runtime deadlock between scikit-learn and PyTorch in the
  same test process. A third — `scripts/build_deploy_db.py` silently
  dropping the city-scoped `fires` table from every deploy (74k+ rows lost,
  every ward's fire evidence empty) — was found the same way and is fixed.

## Roadmap

- **Heat grid** (Phase 6) — a continuous density surface over the national
  grid, not just discrete hotspot cells.
- **A standing daily ingestion job** (Cloud Scheduler + Cloud Run Jobs) so
  the corridor/satellite view stops being a fixed historical snapshot.
  Latency-bound by the satellite products themselves (1–3+ day processing
  lag), not by VAYU's own pipeline.
- **A different egress path for live CPCB** (a residential-IP proxy or a
  different hosting network) now that `api.data.gov.in`'s cloud-IP block is
  the confirmed blocker, not the already-working `services/pipeline/live.py`
  code itself.
- **National ground truth.** Extending the CNN-LSTM's *validated* scope
  beyond Delhi-NCR/Lucknow needs national CPCB history + ERA5/IMDAA
  reanalysis access — architecturally a region-config addition, already
  proven out by `config/regions/india.json`.
- **O₃ back into Objective-1's training set** once its ingestion gaps close
  enough to stop halving the usable 5-day training window.

## Project history

Built across three targets without ever starting over:

| Hackathon | What it added |
|---|---|
| **ET AI Hackathon 2026** | The closed-loop engine itself — forecast, attribution, ranked intervention, dispatch, verification, for Delhi and Lucknow |
| **ISRO PS-3** *(Surface AQI & HCHO Hotspots from Satellite Data)* | National 15,360-cell satellite grid, HCHO hotspot detection, and the CNN-LSTM surface-AQI model (Objective-1) |
| **Build with AI: Code for Communities** | Google Gemini citizen-photo classification, independent-evidence corroboration, five federated economic-corridor bulletins, and the single-container Cloud Run deployment this README points you to |

## License

No license file is currently published in this repository — treat the code
as all-rights-reserved unless the maintainer adds one. Open an issue if you'd
like to use it and a license hasn't been added yet.

---

_Prototype. Not an official government system. Regulation text is an abridged
restatement for demonstration — verify against the current CAQM order before
any real enforcement._
