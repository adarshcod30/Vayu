# VAYU — MASTER BUILD PROMPT (ET AI Hackathon 2026, PS 5)

> **To Claude Code:** This file is the entry point of a four-document specification. Read ALL FOUR documents fully, in this order, before writing any code:
>
> 1. **This file** — scope, principles, build order (§14), golden demo flow (§13). Governs WHAT is in/out of scope and WHEN it gets built.
> 2. **`01_PRD.md`** — personas, user stories with acceptance criteria (P0/P1/P2), success metrics, risks. Governs WHY and defines DONE: a phase is complete only when its P0 acceptance criteria pass.
> 3. **`02_TRD.md`** — architecture, DuckDB schemas, pipeline endpoints, algorithm formulas (trajectory, plume, fusion, ROI, DiD, backtest protocol), API contracts, testing, deployment. Governs HOW. Implement formulas and schemas exactly as written there.
> 4. **`03_App_Flow.md`** — navigation map, persona journeys, screen-by-screen states (loading/ready/empty/error for every async region), state machines, timed demo shot list, edge cases, microcopy tone. Governs UX BEHAVIOR. If a screen behavior is ambiguous, this doc decides.
>
> **Precedence on conflict:** scope/build-order → this file; technical detail → TRD; UX behavior → App Flow; acceptance/definition-of-done → PRD.
>
> **Working rules:** (a) at the start of each phase, re-read the relevant PRD stories and App Flow sections; (b) at the end of each phase, verify the phase's "Done when" here PLUS its P0 acceptance criteria in the PRD PLUS run `make demo-check` once it exists; (c) when a decision is still ambiguous after all four docs, choose the option that makes the 3-minute demo path (§13 / App Flow §6) more impressive. This is a hackathon-winning prototype that must LOOK and FEEL production-grade.

---

## 0. MISSION CONTEXT (why every decision below exists)

We are competing in the ET AI Hackathon 2026, Problem Statement 5: **"AI-Powered Urban Air Quality Intelligence for Smart City Intervention."**

Judging: Innovation 25%, Business Impact 25%, Technical Excellence 20%, Scalability 15%, User Experience 15%.

Official Evaluation Focus (answer ALL of these with visible artifacts):
1. Source attribution accuracy vs ground-truth emission inventories
2. AQI forecast accuracy at hyperlocal resolution — **RMSE vs persistence baseline**
3. Enforcement recommendation quality
4. Citizen advisory relevance and language coverage
5. Demonstrated reduction in response time from signal → intervention

**The core thesis:** Every other team builds a dashboard that *measures* pollution. VAYU *prosecutes* it. The unit of output is an evidence-backed **Intervention Order**, and the loop is:

```
READING → RESPONSIBLE SOURCE → RANKED INTERVENTION → ENFORCEMENT ORDER → VERIFIED OUTCOME
```

Existing systems we beat (mention in README/About page): IITM's Delhi DSS (Delhi-only, winter-only, supercomputer-based, no enforcement workflow), SAFAR (4 cities, forecast-only), CPCB SAMEER (monitoring only). VAYU: any city, 365 days, free public data, closes the loop.

---

## 1. PRODUCT DEFINITION

**Name:** VAYU — Verifiable Airshed Intelligence & Enforcement
**Tagline:** "Dashboards measure pollution. VAYU prosecutes it."

**Three personas, three surfaces:**
1. **Commissioner** (primary) — dark "command center" web app: city map, forecasts, attribution, intervention leaderboard, verification.
2. **Field Inspector** — mobile-width view: receives dispatched Intervention Orders with evidence dossier, marks executed.
3. **Citizen** — clean light-theme public page: ward AQI, 48h forecast, multilingual health advisories, "clean hours" windows.

**Demo cities:** Delhi (primary) + Lucknow (proves scalability). City switching must be instant and config-driven (`config/cities/*.json`).

---

## 2. NON-NEGOTIABLE PRINCIPLES

1. **Demo path first.** The golden flow in §13 must work flawlessly before any secondary feature is built.
2. **Real data wherever free APIs exist; honest labels everywhere else.** Any curated/sample layer (construction permits, seeded intervention) shows a subtle "Sample data" badge. Never fake something that could be real.
3. **Works without API keys.** Every pipeline has a bundled cached/sample fallback (`data/samples/`). `DEMO_MODE=true` runs the full app offline. Keys, when present, switch to live data automatically.
4. **Auditability by design.** Every agent action is logged with timestamp, inputs, reasoning, confidence → visible in an "Agent Log" drawer in the UI.
5. **Explainability.** Forecast page shows SHAP-style feature importance. Attribution percentages are clickable → the exact evidence (fire pixels, trajectory, permit) that justifies them.
6. **Production-grade feel:** zero unhandled errors, skeleton loaders, empty states, responsive, keyboard accessible, < 3s initial load.

---

## 3. TECH STACK (exact)

**Frontend:** Next.js 14+ (App Router, TypeScript), Tailwind CSS + shadcn/ui, **MapLibre GL JS** (no token needed; use free `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` for dark and `positron-gl-style` for light), **deck.gl** for heatmap/trajectory/scatter layers, Recharts for charts, Framer Motion for micro-animations, next-intl or simple dictionary for i18n.

**Backend:** Python 3.11 FastAPI, uvicorn. DuckDB (file-based, zero setup) + parquet for data. APScheduler for refresh jobs. WeasyPrint (or reportlab fallback) for dossier PDFs. httpx for API calls with caching.

**ML/Science:** LightGBM (forecasting), scikit-learn (IDW spatial interpolation), shap (explainability), custom modules for wind back-trajectory and Gaussian plume (write these ourselves, ~200 lines each, well-commented — judges read them).

**LLM layer (optional key):** Anthropic Claude API (`ANTHROPIC_API_KEY`) for: GRAP RAG answers, multilingual advisories, orchestrator reasoning summaries. **Fallback without key:** pre-generated template advisories + pre-computed RAG answers stored in `data/samples/llm_cache.json` so the demo never breaks.

**RAG:** ChromaDB (embedded) over GRAP/CAQM/NCAP PDFs in `data/corpus/`. If no PDFs present, ship 8–10 key GRAP clauses as structured JSON (typed out from public documents, with source citations) — this is enough for the demo.

**Run:** `docker-compose up` starts everything; also `make dev` for local (concurrently runs API + web).

---

## 4. REPO STRUCTURE

```
vayu/
├── README.md                  # judged document — see §15
├── docker-compose.yml
├── Makefile                   # make dev, make seed, make backtest, make demo
├── .env.example               # every key documented, all optional
├── config/cities/{delhi,lucknow}.json   # bbox, wards geojson path, stations, timezone
├── apps/web/                  # Next.js
│   └── src/
│       ├── app/(command)/     # commissioner surfaces
│       │   ├── page.tsx               # Command Center (map)
│       │   ├── ward/[id]/page.tsx     # Ward detail
│       │   ├── interventions/page.tsx # ROI leaderboard + orders
│       │   ├── verify/page.tsx        # Outcome verification
│       │   └── methodology/page.tsx   # About/science/limitations
│       ├── app/citizen/page.tsx       # public citizen view
│       ├── app/inspector/page.tsx     # mobile inspector view
│       └── components/ ...
├── services/api/              # FastAPI app, routers per domain
├── services/pipeline/         # ingestion: openaq.py, meteo.py, firms.py, s5p.py, osm.py
├── vayu_core/                 # the science (pip-installable package)
│   ├── forecast/              # features.py, model.py, backtest.py
│   ├── attribution/           # trajectory.py, fusion.py, confidence.py
│   ├── dispersion/            # gaussian_plume.py
│   ├── interventions/         # roi.py, dossier.py
│   └── agents/                # orchestrator.py, forecaster.py, attributor.py, enforcer.py, herald.py, audit.py
├── data/
│   ├── samples/               # bundled offline data (committed, small)
│   ├── cache/                 # runtime cache (gitignored)
│   └── corpus/                # GRAP/CAQM docs or structured clauses JSON
├── models/artifacts/          # trained .lgb models (committed if <50MB)
├── notebooks/backtest_report.ipynb    # visible science
├── docs/
│   ├── architecture.md        # + generate architecture diagram (mermaid)
│   ├── evaluation.md          # AUTO-GENERATED backtest report (§6.5)
│   └── sample_dossiers/       # 3 example PDFs
└── tests/                     # pytest for vayu_core (trajectory, plume, roi, backtest math)
```

---

## 5. ENVIRONMENT VARIABLES (.env.example — all optional, app must run with none)

```bash
DEMO_MODE=true                # true = bundled sample data only, fully offline
OPENAQ_API_KEY=               # free: openaq.org — live + historical AQ
FIRMS_API_KEY=                # free: firms.modaps.eosdis.nasa.gov — fire detections
ANTHROPIC_API_KEY=            # optional: live LLM advisories + RAG; else cached
# Open-Meteo needs NO key. OSM Overpass needs NO key.
GEE_SERVICE_ACCOUNT_JSON=     # optional: Sentinel-5P layer via Google Earth Engine
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Each pipeline: if key missing OR request fails → log a friendly notice → load `data/samples/<source>.parquet`. The UI shows a tiny "live" / "cached" pill per data layer.

---

## 6. FEATURE SPECIFICATIONS

### 6.1 Data pipelines (`services/pipeline/`)

**OpenAQ (openaq.py):** v3 API. Fetch stations within city bbox, then hourly PM2.5/PM10/NO2 measurements. Backfill 24 months on first run (paginated, cached to parquet). Refresh latest hours every 30 min via APScheduler.

**Open-Meteo (meteo.py):** No key. Historical: `archive-api.open-meteo.com/v1/archive` (hourly: temperature_2m, relative_humidity_2m, wind_speed_10m, wind_direction_10m, wind_speed_100m, wind_direction_100m, boundary_layer_height, precipitation, surface_pressure). Forecast: `api.open-meteo.com/v1/forecast` same fields, 72h. Grid: fetch for 5×5 grid of points across city bbox for wind-field work.

**NASA FIRMS (firms.py):** `firms.modaps.eosdis.nasa.gov/api/area/csv/{KEY}/VIIRS_SNPP_NRT/{bbox}/{days}` — returns lat, lon, frp (fire radiative power), acq_date/time, confidence. Keep last 7 days.

**Sentinel-5P (s5p.py, OPTIONAL):** if GEE creds present, pull weekly mean NO2 column density raster over bbox, export as PNG overlay + bounds. Else skip; UI hides layer gracefully.

**OSM (osm.py):** Overpass queries per city (cache results, run once): schools, hospitals, industrial landuse polygons, brick kilns if tagged. Save geojson.

**Wards:** bundle ward-boundary GeoJSON for Delhi (public: Delhi ward shapefiles) and Lucknow (municipal wards; if unavailable use a hex-grid H3 resolution-7 tessellation labeled "analysis zones"). Loader must accept either.

**Sample permits (`data/samples/permits_delhi.csv`):** 30 realistic construction-site rows (name, lat, lon, status, dust-control-compliance flag). Marked sample.

### 6.2 FORECASTER agent (`vayu_core/forecast/`)

- **Target:** station-level PM2.5 at t+24h, t+48h, t+72h (three LightGBM models, quantile objectives for p10/p50/p90 → uncertainty bands).
- **Features:** lagged PM2.5 (1,3,6,12,24,48h), rolling means, hour/day-of-week/month cyclic encodings, wind speed/direction (u,v components), boundary-layer height, humidity, temperature, precipitation, upwind-station PM2.5 (nearest station within ±45° of upwind direction), FIRMS fire count within 50km upwind (24h), festival/holiday flag (bundle India holiday list).
- **Spatial layer:** IDW interpolation from stations → ward centroids → per-ward forecast + city 1km heat grid for the map.
- **Explainability:** persist SHAP values for the latest prediction; API returns top-6 feature contributions per ward ("Why this forecast?" panel).
- **Backtest harness (`backtest.py`) — CRITICAL:** rolling-origin evaluation on final 30 days of history (never trained on). Compute RMSE + MAE for our model vs **persistence** (t+24 = t) vs **climatology** (hour-of-day monthly mean). Also AQI-category accuracy (correct CPCB bucket %) and hazard-crossing detection (precision/recall for crossing AQI 300).
- **Auto-generate `docs/evaluation.md`** with the comparison table + matplotlib charts (predicted-vs-actual, residuals, calibration). `make backtest` reruns everything. These numbers go in the README header.

### 6.3 ATTRIBUTOR agent (`vayu_core/attribution/`)

- **Back-trajectory (trajectory.py):** for a ward centroid at time T, integrate backwards through the hourly wind field (bilinear interpolation of the 5×5 Open-Meteo grid) in 10-min steps for 6/12/24h → polyline + a dispersion cone (±25° widening with distance). Output GeoJSON for the map animation.
- **Evidence fusion (fusion.py):** inside the trajectory cone, gather: FIRMS fires (weight by FRP × recency × distance decay), industrial polygons (OSM), sample permits (dust flag), road-density proxy for traffic, S5P NO2 anomaly if available. Regional-transport share = fraction of cone outside city bbox.
- **Attribution output per ward:** `{source_category: {share_pct, confidence_0_1, evidence: [items with lat/lon, type, timestamp, link]}}`. Shares from a transparent weighted scoring formula (document it in methodology page — judges must see it's principled, not hardcoded). Categories: open_burning, traffic, construction, industry, regional_transport.
- **Confidence:** function of evidence count, sensor agreement, wind-field stability. Show as 0–1 with a colored ring.

### 6.4 ENFORCER agent (`vayu_core/interventions/` + `dispersion/`)

- **Gaussian plume (gaussian_plume.py):** standard Pasquill–Gifford stability classes from wind speed + time of day; given a source (lat, lon, emission estimate from FRP or category default) compute downwind concentration field. Used forward: "what does this source add to ward X?" → counterfactual: "remove it → predicted µg/m³ reduction at t+12/24/48h."
- **Intervention ROI (roi.py):** for each candidate action (halt burning cluster, stop non-compliant construction site, reroute traffic corridor, industrial curb): `ROI = µg/m³ averted × population_exposed ÷ effort_units` (population from ward populations in city config; effort = teams required, from a small lookup). Output ranked leaderboard with plain-language one-liners.
- **Evidence Dossier (dossier.py):** one click → PDF: VAYU header, order ID + timestamp, static map image of source + trajectory (render via staticmaps or matplotlib basemap plot), evidence list (fire pixels table / permit row / satellite note), applicable regulation (from RAG: GRAP clause or Air Act 1981 section, with citation), predicted impact + confidence, dispatch details, sign-off line. Also saved to `docs/sample_dossiers/`.
- **GRAP Autopilot:** when any ward's 48h forecast crosses a GRAP stage threshold (Stage I ≥201, II ≥301, III ≥401, IV ≥450 city AQI), draft the stage's measure list (from corpus, with citations) as a "pending human approval" card. Approving logs it and notifies Herald.

### 6.5 HERALD agent (citizen layer)

- Ward-level advisory generation: severity-templated, LLM-personalized when key present (else templates): general public / children & schools / outdoor workers / elderly & respiratory.
- **Languages:** English, Hindi, + one regional (pre-translate templates; LLM live-translates when key present). Language switcher in citizen UI.
- **Clean-hours:** from the hourly 48h forecast, compute the best outdoor windows per ward ("Best air today: 6–9 AM, AQI ~140").
- **Vulnerability overlay:** schools/hospitals inside a forecast plume or AQI>300 zone get flagged → targeted alert list ("Notify 14 schools in plume path" button → mock WhatsApp panel showing the actual message bubbles in chosen language).

### 6.6 VERIFICATION module

- When an intervention is marked "executed," snapshot: target ward series, 3 weather-matched control wards (similar pre-period AQI + not in plume), predicted counterfactual.
- **Diff-in-diff after 48h:** actual reduction vs predicted, with a simple CI. Panel: "Predicted −61 µg/m³ peak · Observed −54 µg/m³ (89% of predicted) vs controls."
- **Seed one completed historical intervention per city** (clearly badged "Seeded demo record") so the panel is never empty on judging day.

### 6.7 ORCHESTRATOR + audit log

- A lightweight event loop (not over-engineered): pipeline refresh → Forecaster runs → threshold events → Attributor on flagged wards → Enforcer builds candidates → Herald drafts advisories. Each step appends to `audit_log` (DuckDB): agent, trigger, inputs hash, decision, reasoning text (LLM-summarized when key present, else templated), confidence, duration.
- UI: right-side "Agent Activity" drawer streaming the log — this is the *agentic AI made visible* moment. Include a **response-time stopwatch**: elapsed time from signal detection → dossier ready (target < 5 min; display it — Evaluation Focus #5).

---

## 7. API DESIGN (FastAPI, `/api/v1`)

```
GET  /cities                          # configured cities
GET  /cities/{id}/current             # latest AQI per ward + stations (+live/cached flags)
GET  /cities/{id}/forecast?h=24|48|72 # per-ward p10/p50/p90 + grid heat layer
GET  /cities/{id}/forecast/explain/{ward}   # SHAP top features
GET  /cities/{id}/attribution/{ward}  # shares + confidence + evidence items
GET  /cities/{id}/trajectory/{ward}?hours=12  # GeoJSON polyline + cone
GET  /cities/{id}/interventions       # ranked ROI leaderboard
POST /interventions/{id}/dispatch     # generates dossier PDF, returns URL
POST /interventions/{id}/execute      # starts verification tracking
GET  /interventions/{id}/verification # diff-in-diff results
GET  /citizen/{city}/{ward}?lang=en|hi|..   # advisory + clean hours
GET  /grap/status/{city}              # current + forecast stage, drafted measures
POST /grap/{draft_id}/approve
GET  /audit?limit=100                 # agent activity stream (also SSE /audit/stream)
GET  /meta/evaluation                 # backtest metrics JSON (for the Methodology page)
```

All responses typed (pydantic), errors as RFC7807 JSON. CORS for the web app.

---

## 8. UI/UX SPECIFICATION (this is 15% of the score — make it exceptional)

### Design system
- **Command Center (dark):** background `#0A0E1A`, surface `#111827`, borders `#1F2A44`. Accent: electric cyan `#22D3EE` (data), amber `#F59E0B` (warnings), red `#EF4444` (hazard), green `#10B981` (verified). AQI colors follow CPCB buckets exactly (50 green → 500 maroon).
- **Citizen view (light):** white/soft-gray, large type, friendly.
- **Typography:** Inter (UI) + JetBrains Mono (numbers/coordinates). Big KPI numerals.
- **Motion:** Framer Motion; 150–250ms ease-out transitions; animated count-ups on KPIs; **deck.gl TripsLayer for flowing trajectory animation** (the signature visual). No gratuitous animation elsewhere.
- Skeleton loaders on every async block; designed empty states; toasts for actions; cmd-K city/ward search.

### Screen 1 — Command Center (`/`)
- Full-bleed MapLibre dark map. Layers (toggle chips top-left): AQI heat grid, ward choropleth, stations, fires (FIRMS, flame icons sized by FRP), industry, trajectories, plume forecast.
- Left rail: city KPIs (city AQI now, 24/48/72h forecast chips with trend arrows, GRAP stage badge, active alerts count).
- **Alert cards** (top-right stack): "Ward 47 → AQI 312 predicted in 36h (confidence 0.84)" → click = flyTo ward + opens Ward Detail sheet.
- Right drawer: Agent Activity stream (live-updating, monospace, agent-colored tags).
- Bottom-center: time scrubber (past 24h observed → next 72h forecast) that animates the heat grid — the "weather channel" moment.

### Screen 2 — Ward Detail (sheet or `/ward/[id]`)
- Header: ward name, live AQI dial, category chip.
- Forecast chart: observed line + forecast with p10–p90 band; threshold lines at 200/300/400.
- "Why this forecast?" — horizontal SHAP bars, plain-English labels ("Low wind speed +38", "Upwind fires +22").
- **Attribution donut** with confidence rings; clicking a slice highlights its evidence on the map and lists it (each item: type icon, timestamp, distance, source link).
- CTA: "Generate Intervention Options" → Enforcer.

### Screen 3 — Interventions (`/interventions`)
- **ROI leaderboard table:** rank, action, µg/m³ averted (bold), people protected, effort, confidence, ROI score bar. Row expand = counterfactual mini-chart (forecast with/without action).
- "Dispatch" → dossier PDF preview modal (embedded) + "Send to Inspector."
- GRAP Autopilot card when stage crossing predicted: drafted measures w/ citations + Approve button (human-in-the-loop badge).

### Screen 4 — Inspector (`/inspector`, mobile-width)
- Order list → order page: map, evidence checklist, dossier download, "Mark Executed" (photo-note field). Feels like a field app.

### Screen 5 — Citizen (`/citizen`)
- Ward selector + geolocate. Huge AQI number with face icon, 48h forecast sparkline, **Clean Hours strip** (green time blocks), advisory cards per audience, language switcher (EN/HI/+1), mock WhatsApp bubble preview. Shareable card design.

### Screen 6 — Verify (`/verify`)
- Intervention cards: predicted vs observed bars, diff-in-diff chart vs controls, "% of predicted impact realized," response-time stopwatch stat ("Signal → dossier: 3m 42s").

### Screen 7 — Methodology (`/methodology`)
- The judge-trust page: data sources table with live/cached status, backtest table (auto from `/meta/evaluation`), attribution formula, plume math summary, limitations section (honest), regulation corpus list. Link to `docs/evaluation.md`.

---

## 9. DEMO/SEED DATA STRATEGY (`make seed`)

- Bundle in `data/samples/`: 60 days hourly AQ for both cities (real, pre-downloaded), 60 days weather, 7 days FIRMS, OSM extracts, permits CSV, llm_cache.json, one seeded verified intervention per city.
- `make seed` loads all → trains models if artifacts missing → runs backtest → app fully working offline in one command. **The judged demo must never depend on wifi.**

---

## 10. TESTS (pytest — prove the science)

- trajectory: known uniform wind field → straight-line trajectory of correct length/bearing.
- plume: concentration decreases downwind; mass conservation sanity; stability class selection.
- roi: ranking monotonic in averted µg/m³ and population; ties broken by effort.
- backtest: metrics math verified on synthetic series where truth is known.
- API: smoke tests for every endpoint in DEMO_MODE.

---

## 11. WHAT NOT TO BUILD

No auth/login, no user management, no settings pages, no payment, no notification infra (mock the WhatsApp panel), no k8s. Every hour goes to the golden flow and polish.

---

## 12. BUSINESS IMPACT SURFACES (bake into UI, don't just say in deck)

- Command Center footer ticker: "1.67M premature deaths/yr (Lancet) · 900+ CAAQMS stations · 69% of monitored cities lack response protocols (CAG 2024)".
- Every intervention shows **people protected** — impact as a first-class number.
- Methodology page: "Cost to run VAYU for one city: ~$0/mo data + commodity cloud" vs supercomputer DSS.

---

## 13. THE GOLDEN FLOW (rehearse-able 3-minute demo path — must be flawless)

1. Command Center Delhi → time scrubber shows deteriorating 48h grid.
2. Alert card: Ward 47 crossing AQI 300 in 36h → click → Ward Detail.
3. "Why": SHAP shows upwind fires + stagnant wind. Attribution: 42% open burning (conf 0.87) → click slice → **trajectory animation flows to FIRMS cluster 18 km upwind**.
4. "Generate Intervention Options" → leaderboard: #1 halt burning cluster, −61 µg/m³, 38,000 people, 1 team.
5. Dispatch → dossier PDF appears (regulation citation visible) → Inspector view receives it.
6. Herald: notify 14 schools → WhatsApp bubbles in Hindi.
7. Verify page: seeded past intervention — predicted vs observed, "Signal → dossier: 3m 42s".
8. City switcher → Lucknow loads instantly ("new city = one config file").

---

## 14. BUILD ORDER (strict phases; finish + verify each before next)

**Phase 1 — Skeleton & data (foundation):** repo scaffold, docker-compose, city configs, pipelines with sample fallbacks, DuckDB schema, `make seed` working, `/cities/{id}/current` + map showing real ward AQI. ✅ Done when: map renders live/cached AQI for both cities.
**Phase 2 — Forecaster + backtest:** models, interpolation, uncertainty, SHAP, backtest harness, `docs/evaluation.md` auto-generated. ✅ Done when: forecast layer + ward chart + evaluation numbers exist.
**Phase 3 — Attributor:** trajectory module + animated layer, evidence fusion, attribution API + donut UI. ✅ Done when: golden-flow step 3 works.
**Phase 4 — Enforcer:** plume, ROI leaderboard, dossier PDF, GRAP autopilot, inspector view. ✅ Done when: steps 4–5 work.
**Phase 5 — Herald + Verification + audit drawer:** citizen page, languages, clean hours, school alerts, diff-in-diff panel, agent stream, stopwatch. ✅ Done when: steps 6–7 work.
**Phase 6 — Polish:** animations, skeletons, empty states, responsive pass, Methodology page, README, architecture diagram (mermaid in docs/), sample dossiers, lighthouse check, full golden-flow rehearsal on clean clone (`git clone → make seed → make dev` must reach the demo in <10 min).

---

## 15. README.md REQUIREMENTS (judges screen repos before videos)

Order: 1) one-paragraph pitch + golden-flow GIF placeholder, 2) **backtest results table** (from evaluation.md), 3) the loop diagram, 4) "How VAYU differs from SAFAR / Delhi DSS / dashboards" table, 5) architecture diagram, 6) 60-second quickstart (`git clone → cp .env.example .env → make seed → make dev`), 7) data sources + honesty statement, 8) evaluation-focus mapping table, 9) tech stack, 10) team.

---

## 16. FINAL ACCEPTANCE CHECKLIST

- [ ] `make seed && make dev` on a clean machine → full app, no keys, no errors
- [ ] Golden flow 1–8 flawless in DEMO_MODE
- [ ] Backtest table shows VAYU beats persistence + climatology (real numbers)
- [ ] Every attribution % traces to clickable evidence
- [ ] Dossier PDF cites a real regulation clause
- [ ] Advisories render in 3 languages
- [ ] Agent Activity drawer streams during the flow; stopwatch < 5 min
- [ ] Live/cached pills honest; sample badges on curated data
- [ ] Zero console errors; responsive; skeletons everywhere
- [ ] README + docs/evaluation.md + architecture diagram + 3 sample dossiers committed
```
