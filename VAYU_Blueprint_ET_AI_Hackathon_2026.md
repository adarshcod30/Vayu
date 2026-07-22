# Project VAYU — Winning Blueprint for ET AI Hackathon 2026
### Problem Statement 5: AI-Powered Urban Air Quality Intelligence for Smart City Intervention

**Working name:** VAYU — *Verifiable Airshed Intelligence & Enforcement* (Sanskrit: "wind/air")
Alternate names if VAYU is taken by another team: **AirWarrant**, **NirmalNet**, **VayuNetra** ("eye on the air"). Verify name availability on Unstop/GitHub before finalizing.

---

## 1. The One-Line Pitch

> **Every other team will build a dashboard that *measures* pollution. We are building the system that *prosecutes* it.**
>
> VAYU closes the loop that no existing system in India closes: **Reading → Responsible Source → Ranked Intervention → Enforcement Order → Verified Outcome.**

The unit of output of our product is not a chart. It is an **evidence-backed Intervention Order** — a dispatch-ready dossier that tells a municipal officer *exactly* where to go, *what* to stop, *how many µg/m³ it will save*, and — 48 hours later — *whether it actually worked*.

---

## 2. Why This Problem Statement Wins (Strategic Reasoning)

### 2.1 The judging math
Innovation (25%) + Business Impact (25%) = **50% of the score is about the idea and its consequence**, not code. Technical Excellence is only 20%. Winning means picking a problem where impact is *provable*, not simulated.

### 2.2 PS 5 is the only problem statement with real, free, live data
| PS | Data reality |
|---|---|
| PS 1 Industrial Safety | SCADA/gas sensor data must be **faked** — judges know instantly |
| PS 2 Energy Supply Chain | AIS vessel data is paid; scenarios unverifiable |
| PS 3 EV Supply Chain | BMS/telematics data must be simulated |
| PS 4 Data Centre EPC | Proprietary project documents don't exist publicly |
| **PS 5 Air Quality** | **CPCB live feeds, OpenAQ history, NASA satellites, weather — all free, all real** |
| PS 6 Digital Fraud | Scam call data must be synthesized; "very low false positive" bar brutal to prove |
| PS 7 Cyber Resilience | Benchmark datasets exist but demos look like log files |
| PS 8 Knowledge RAG | Will be the most crowded pick — everyone builds a RAG chatbot |

**Consequence:** We are the team whose accuracy claims can be *backtested against reality*. When the PDF's Evaluation Focus asks for "AQI forecast accuracy at hyperlocal resolution (RMSE versus persistence baseline)" — we will show a real number computed on real held-out CPCB history. Teams on other PS structurally cannot do this.

### 2.3 The problem passes the "can be seen" test
Air pollution is the only problem in the list that judges physically experience. A Delhi/NCR evaluator opened their window this morning to this problem. Emotional resonance is free.

### 2.4 The PDF hands us the gap
The problem context itself says: *"The data exists. The intelligence layer to act on it does not"* and *"only 31% of cities with monitoring data had any actionable multi-agency response protocols."* Our product is literally that missing 69%.

---

## 3. Know Your Enemy: What Exists Today (and Why We're Different)

This section is our credibility armor. Most teams won't know these systems exist; judges (or their advisors) will. We name them proactively and position against them.

| Existing system | What it does | Its gap (our opening) |
|---|---|---|
| **IITM Decision Support System (DSS), Delhi** | Numerical-model source attribution from 29 sectors, 3-day lead time | **Delhi-only. Winter-only — it is switched off from March to August.** No ward-level granularity, no enforcement workflow, no outcome verification. Requires supercomputer (Pratyush). |
| **SAFAR** (MoES) | AQI forecasts for 4 metros | Forecast only. No attribution, no action layer. 4 cities out of 130+ NCAP cities. |
| **CPCB SAMEER app / CAAQMS dashboards** | Real-time AQI display | Pure monitoring. The exact "dashboard" trap the PS warns against. |
| **GRAP / CAQM (Delhi-NCR)** | Graded response action plan, manually invoked | Reactive, committee-driven, invoked *after* AQI crosses thresholds. No forecast-triggered automation, no evidence packaging. |
| **Private (Ambee, Blue Sky Analytics, AQI.in)** | Data/API vendors | Sell data, not decisions. No enforcement or accountability loop. |

**Our positioning sentence for the deck:**
> "The Government of India already spends crores running a supercomputer-based DSS for one city, six months a year. VAYU delivers ward-level attribution, intervention ranking, and enforcement orchestration for **any of the 900+ CAAQMS-monitored locations, 365 days a year, on commodity cloud** — because we replace heavy chemistry-transport models with a fusion of satellite evidence, wind-field back-trajectories, and machine learning."

This is the out-of-the-box move: not inventing a new dashboard, but **democratizing and closing the loop on a capability the government has proven it wants but cannot scale.**

---

## 4. What Everyone Else Will Build vs. What We Build

| The typical PS 5 submission (predictable) | VAYU (differentiated) |
|---|---|
| AQI map with colored dots | **Animated pollution *provenance* map** — wind back-trajectories showing where each ward's air came from in the last 12h |
| LSTM forecast of city AQI | **Ward-level (1 km grid) 24–72h forecast, backtested**, with RMSE vs persistence baseline and calibration plots in the deck |
| A pie chart of "sources" (hardcoded) | **Evidence-fused attribution**: NASA FIRMS fire pixels + Sentinel-5P NO₂/SO₂ columns + construction permits + traffic proxies + land use, each with a confidence score |
| "Alert the authorities" button | **Intervention ROI engine**: counterfactual dispersion modeling ranks candidate actions by *µg/m³ averted per enforcement-hour* — enforcement as an optimization problem |
| Generic chatbot advisory | **GRAP Autopilot**: RAG over the actual CAQM/GRAP legal documents; forecasts stage crossings 48h ahead and auto-drafts the legally-specific measure list with citations |
| Nothing after the alert | **Outcome Verification**: after an intervention, difference-in-differences vs weather-matched control wards answers "did it actually work?" — *no one builds this* |

**The three features nobody else will have (our innovation core):**
1. **Intervention ROI Leaderboard** — ranks enforcement actions by predicted µg/m³ averted per unit effort. Turns "Business Impact 25%" into a literal number on screen.
2. **Evidence Dossier Generator** — one click produces a court/CAQM-grade PDF: geotagged source, satellite snapshot, wind trajectory proof, regulation violated, predicted impact. This is the "enforcement recommendation quality" the Evaluation Focus demands.
3. **Outcome Verification Panel** — closes the accountability loop. Also directly serves the Evaluation Focus item "demonstrated reduction in response time from signal to intervention."

---

## 5. Product Architecture: The Four-Agent Airshed Command

An agentic system (matches "Multi-Agent AI Systems" in suggested technologies), with every agent action logged with reasoning — auditability by design.

```
                    ┌─────────────────────────────┐
                    │   ORCHESTRATOR (LLM agent)   │
                    │  routes events, logs reasons │
                    └──────┬──────┬──────┬────────┘
                           │      │      │
        ┌──────────┐ ┌─────┴────┐ ┌┴─────────┐ ┌──────────┐
        │ FORECASTER│ │ ATTRIBUTOR│ │ ENFORCER │ │  HERALD  │
        │  (when)   │ │   (who)   │ │  (what)  │ │ (citizen)│
        └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Agent 1 — FORECASTER ("when will it get bad, where")
- **Input:** OpenAQ/CPCB historical + live station data, Open-Meteo weather forecasts (wind, boundary-layer height, humidity, temperature inversion signals), seasonal/festival calendar, day-of-week traffic patterns.
- **Model:** Gradient boosting (LightGBM) per-pollutant, per-grid-cell. Spatial interpolation (IDW/kriging) from stations to 1 km grid. *Deliberately not an LSTM* — LightGBM trains in seconds, is explainable (SHAP feature importance shown in UI), and beats deep models on tabular weather-AQI data at this scale.
- **Output:** 24/48/72h AQI forecast per ward with uncertainty bands.
- **The evidence move:** hold out the most recent 30 days of real data → publish RMSE vs (a) persistence baseline ("tomorrow = today"), (b) climatology. Show the table in the deck and README.

### Agent 2 — ATTRIBUTOR ("whose smoke is this")
- **Wind back-trajectory:** integrate reverse wind vectors (Open-Meteo hourly wind field) from each hotspot ward, 6–24h backwards → upwind source polygon. Simple, physically real, and *demos beautifully* as animated trails on the map.
- **Evidence layers fused inside the polygon:**
  - NASA FIRMS VIIRS/MODIS fire detections (waste/stubble burning) — free API, near-real-time
  - Sentinel-5P NO₂/SO₂ column density (industrial/traffic signature) — free via Copernicus/GEE
  - OSM land use + industrial site locations; construction permit records (municipal open data or curated sample)
  - Traffic proxy (tomtom index / time-of-day patterns)
- **Output:** per-ward source attribution (e.g., "42% open burning, 31% traffic, 18% construction, 9% regional transport") **with a confidence score per claim and a clickable evidence trail** — every percentage links to the satellite pixel/permit/trajectory that justifies it.

### Agent 3 — ENFORCER ("what action, in what order")
- **Counterfactual engine:** Gaussian plume dispersion (standard atmospheric science, implementable in ~200 lines) simulates "if this source stops now, what does ward AQI look like in 12/24/48h?"
- **Intervention ROI:** ranks candidate actions by `µg/m³ averted × population exposed ÷ enforcement effort`. Renders as a leaderboard: *"Action 1: Halt burning cluster at [location] — saves 61 µg/m³ peak, 38,000 people in plume path, 1 inspection team."*
- **Evidence Dossier Generator:** one click → PDF with map, satellite snapshot, trajectory proof, applicable regulation (GRAP clause / Air Act section via RAG with citation), predicted impact. Dispatch-ready.
- **GRAP Autopilot:** RAG over actual GRAP/CAQM notification documents; when the Forecaster predicts a stage-threshold crossing 48h out, drafts the stage-specific measure list with document citations for human sign-off. (Human-in-the-loop = responsible AI talking point.)

### Agent 4 — HERALD ("protect people meanwhile")
- Ward-level advisories in regional languages (Hindi + 2–3 others via LLM) pushed through a WhatsApp-style interface in the demo.
- **Vulnerability mapping:** schools, hospitals, elder-care from OSM overlaid with the forecast plume → *targeted* alerts ("School X: shift outdoor sports to 7–9 AM clean window"), not blanket city warnings.
- **Clean-hours exposure windows:** hyperlocal "safe outdoor time" recommendation — a citizen-facing feature with daily utility.

### Closing the loop — OUTCOME VERIFICATION
- After an intervention is marked "executed," track the target ward vs weather-matched control wards (difference-in-differences).
- Panel shows: predicted saving vs actual saving, with honesty about confidence intervals.
- This transforms VAYU from a "recommendation tool" into an **accountability system** — the strongest Business Impact story in the room.

---

## 6. Explicit Mapping to the Problem Statement PDF

### 6.1 Coverage of "What You May Build" (all five bullets)
| PDF bullet | VAYU component |
|---|---|
| Geospatial Pollution Source Attribution Engine | Agent 2 ATTRIBUTOR (trajectory + satellite + permit fusion, confidence-scored) |
| Hyperlocal Predictive AQI Forecasting Agent | Agent 1 FORECASTER (1 km grid, 24–72h, backtested) |
| Enforcement Intelligence & Prioritisation Agent | Agent 3 ENFORCER (ROI leaderboard + evidence dossiers) |
| Multi-City Comparative Intelligence Dashboard | Multi-city switcher (Delhi + 1–2 non-obvious cities, e.g., Lucknow/Patna) + intervention-effectiveness comparison via the Verification panel |
| Citizen Health Risk Advisory System | Agent 4 HERALD (multilingual, vulnerability-mapped, clean-hours) |

### 6.2 Coverage of Evaluation Focus (every clause answered)
| Evaluation Focus clause | Our proof artifact |
|---|---|
| Source attribution accuracy vs ground-truth emission inventories | Compare our Delhi attribution against published IITM DSS sector splits + TERI/SAFAR emission inventory studies — a real cross-validation no one else will attempt |
| AQI forecast accuracy at hyperlocal resolution (RMSE vs persistence) | Backtest table: our RMSE vs persistence vs climatology, on 30 held-out days of real CPCB data |
| Enforcement recommendation quality rated by domain experts | Evidence dossiers are self-documenting; include 3 sample dossiers in the submission PDF; if possible get 1 comment from a municipal officer/professor (huge if achievable) |
| Citizen advisory relevance and language coverage | Live demo of Hindi + English + 1 regional language advisories, vulnerability-targeted |
| Demonstrated reduction in response time signal → intervention | Timeline graphic: today's process (CAG: no protocols in 69% of cities, days-to-weeks) vs VAYU (signal → dispatched dossier in < 5 minutes) |

### 6.3 Suggested technologies — all six used
Geospatial + remote sensing (Sentinel-5P, FIRMS, MODIS) ✓ · Multi-agent AI ✓ · Real-time CAAQMS/IoT integration ✓ · Atmospheric dispersion modelling (Gaussian plume + back-trajectory) ✓ · Predictive analytics (LightGBM + uncertainty) ✓ · LLMs for multi-language citizen communication ✓

### 6.4 Judging criteria mapping
| Criterion | Weight | How VAYU scores it |
|---|---|---|
| Innovation | 25% | Intervention ROI ranking, outcome verification loop, evidence dossiers — three features absent from both existing govt systems and predictable hackathon builds |
| Business Impact | 25% | 1.67M premature deaths/yr context; quantified µg/m³ averted per action; direct fit to NCAP's 130-city mandate and CAQM's legal machinery; SaaS-to-municipalities model (NCAP funds already allocated to cities) |
| Technical Excellence | 20% | Real multi-source data fusion, backtested models, SHAP explainability, agent audit logs, reproducible pipeline |
| Scalability | 15% | Works from free public data — onboarding a new city = config file, not a supercomputer. Demo the same stack on 2–3 cities live |
| User Experience | 15% | Three personas, three surfaces: Commissioner (command map), Inspector (mobile dossier view), Citizen (WhatsApp advisory). Judged in 3 minutes — designed for it |

---

## 7. Data Sources (all free, all real)

| Source | What we take | Access |
|---|---|---|
| **OpenAQ** | Historical + live PM2.5/PM10/NO₂ for Indian CAAQMS stations | Free API |
| **CPCB / data.gov.in** | Official AQI, station metadata | Free (scrape/API) |
| **Open-Meteo** | Hourly weather forecast + historical reanalysis (wind u/v, PBL height, temp, humidity) | Free API, no key |
| **NASA FIRMS** | VIIRS/MODIS active fire detections (burning events), <3h latency | Free API key |
| **Sentinel-5P (Copernicus)** | NO₂ / SO₂ / CO column maps | Free (GEE or openEO) |
| **OpenStreetMap** | Land use, industry, schools, hospitals, roads | Free (Overpass) |
| **GRAP/CAQM + NCAP documents** | Legal corpus for RAG | Public PDFs |
| Municipal construction permits | Sample/curated set for demo city | Open data where available; clearly-labeled curated sample otherwise |

**Honesty rule for the demo:** everything real-time is real; anything curated (permits) is labeled "sample dataset" on-screen. Judges reward transparency and punish discovered fakery.

---

## 8. Tech Stack (chosen for your team: React/Next.js)

**Frontend:** Next.js 14 + **MapLibre GL** (free, no token) + **deck.gl** for animated trajectory/heatmap layers · Tailwind + shadcn/ui · Recharts for metrics · dark "command center" theme (judges = instant credibility).

**Backend:** FastAPI (Python) — data pipelines, LightGBM models, plume simulation, PDF dossier generation (WeasyPrint) · Postgres + PostGIS (or DuckDB + GeoJSON to keep it light) · APScheduler for periodic data pulls.

**AI layer:** LightGBM (forecast) · scikit-learn (interpolation) · custom back-trajectory + Gaussian plume modules (~400 lines, we own the science) · Claude/GPT API for: orchestrator reasoning logs, GRAP RAG (with a small vector store, e.g., ChromaDB), multilingual advisories.

**Deploy for demo:** Vercel (frontend) + Railway/Render (backend) — a live URL in the submission beats "runs on my laptop."

**Repo structure (GitHub URL is a scored deliverable — treat README as a judged document):**
```
vayu/
├── README.md            ← pitch, architecture diagram, backtest metrics table, live demo link, 60-sec setup
├── apps/web             ← Next.js command center + citizen view
├── services/api         ← FastAPI
├── services/pipeline    ← data ingestion (openaq, firms, meteo, s5p)
├── models/              ← forecasting + backtest notebooks (keep the notebooks — judges love visible science)
├── agents/              ← orchestrator, forecaster, attributor, enforcer, herald
├── docs/                ← architecture diagram, evaluation report, sample dossiers
└── docker-compose.yml   ← one-command run
```

---

## 9. Two-Week Build Plan

**Days 1–2 — Data foundation.** Ingestion pipelines for OpenAQ/CPCB, Open-Meteo, FIRMS. Pick demo cities: **Delhi (must) + Lucknow or Patna** (shows scalability beyond the obvious). Backfill 2 years of history.

**Days 3–5 — Forecaster.** LightGBM per-pollutant models, grid interpolation, uncertainty bands. **Run the backtest immediately** — this number anchors the whole submission. SHAP explainability.

**Days 6–8 — Attributor + Enforcer.** Back-trajectory module → animated map layer. FIRMS + S5P + land-use fusion → attribution with confidence. Gaussian plume counterfactual → Intervention ROI leaderboard. Evidence dossier PDF generator.

**Days 9–10 — Herald + GRAP Autopilot.** RAG over GRAP docs with citations. Multilingual advisories. Vulnerability overlay (OSM schools/hospitals). WhatsApp-style citizen view.

**Days 11–12 — Command center polish.** The 3-minute demo path must be flawless: city map → forecast alert → attribution trails → ROI leaderboard → dossier → citizen alert → verification panel. Seed a "verified past intervention" so the verification panel has content. Multi-city switcher.

**Day 13 — Submission artifacts.** Detailed PDF document (problem → gap vs existing systems → architecture → backtest evidence → impact model → scalability), architecture diagram, pitch deck, README final pass.

**Day 14 — Demo video (3–4 min) + buffer.** Record twice; script below. Submit a day early — Unstop uploads fail at deadlines.

---

## 10. The 3–4 Minute Demo Video Script (storyboard)

Hackathon judging research is unanimous: *a story about one place beats a tour of features.* We tell the story of one ward, one day.

| Time | Scene | On screen |
|---|---|---|
| 0:00–0:25 | **Hook.** "On 23 January 2025, eight monitoring stations in Delhi recorded hazardous air for 14 straight hours. Every reading was public. No enforcement action was traceable to any of them. India has 900+ monitoring stations — and a 69% action gap (CAG, 2024)." | News-style AQI imagery → the CAG statistic |
| 0:25–0:50 | **Reframe.** "Dashboards measure pollution. VAYU prosecutes it." Introduce the loop: Reading → Source → Action → Verification | Loop animation, 4 agents |
| 0:50–1:30 | **Forecast.** Command center: Forecaster flags Ward 47 crossing AQI 300 in 36 hours, with confidence band. "This forecast is backtested: X% better than persistence on 30 days of real CPCB data." | Live UI + metrics overlay |
| 1:30–2:10 | **Attribution.** Wind back-trajectory animates; FIRMS fire cluster lights up 18 km upwind; attribution card: "42% open burning — confidence 0.87 — evidence: 6 VIIRS detections + trajectory intersect." | The wow moment — animated trails |
| 2:10–2:50 | **Action.** ROI leaderboard ranks 5 interventions; click #1 → Evidence Dossier PDF generates on screen; inspector's mobile view receives dispatch. Meanwhile Herald pushes Hindi advisory to schools in plume path. | Split screen: commissioner / inspector / citizen |
| 2:50–3:20 | **Verification.** "48 hours later": actual vs predicted µg/m³ saved, diff-in-diff vs control ward. "The loop is closed. Every rupee of enforcement is now auditable." | Verification panel |
| 3:20–3:45 | **Scale + close.** Switch city to Lucknow live ("new city = one config file, zero supercomputers"). "The government's own DSS covers 1 city, 6 months a year. VAYU: every NCAP city, 365 days. That's 1.67 million lives a year worth fighting for." Team + GitHub + live URL | Multi-city map zoom-out |

---

## 11. Winning Tactics Checklist (from hackathon-winner research)

- **Demo > everything.** One end-to-end user flow, rehearsed until boring. No settings pages, no auth screens.
- **A mediocre project with a great pitch beats the reverse.** Budget days 13–14 entirely for narrative.
- **Numbers beat adjectives.** Every claim gets a number: RMSE, µg/m³ averted, minutes-to-dossier, population covered.
- **Show why judges should trust the AI:** citations in RAG answers, confidence scores on attribution, SHAP plots, agent audit logs. "Auditable" appears in the Evaluation Focus of *every* PS — ET's evaluators care.
- **Pre-empt the killer question.** Judges will ask "how is this different from SAFAR/the Delhi DSS?" — we answer it *in* the deck before they ask (Section 3 table).
- **Submit early, test the video file** (<50MB mp4, or Drive link), and make the GitHub README a standalone pitch — evaluators often screen repos before ever watching videos.
- **Label sample data honestly.** Real-time layers real; curated layers labeled. Integrity reads as maturity.

---

## 12. Anticipated Judge Q&A (prepare answers now)

1. **"Attribution without a chemistry-transport model — is it valid?"** → We fuse *direct observation* (satellite fire pixels, NO₂ columns) with physical wind trajectories; we cross-validate our Delhi splits against published IITM DSS/emission-inventory figures and report agreement. We trade model sophistication for scalability + evidence traceability — the right trade for enforcement, where you need proof, not simulation.
2. **"Will municipalities actually use this?"** → NCAP already funds 130 cities for air-quality action; CAQM already issues GRAP directions manually. VAYU doesn't create a new workflow — it accelerates a legally mandated one from days to minutes.
3. **"What about data gaps in smaller cities?"** → Satellite layers (FIRMS, S5P) are nationwide regardless of ground stations; forecaster degrades gracefully to satellite + weather features. This is exactly why the architecture beats station-dependent designs.
4. **"Privacy/misuse of enforcement AI?"** → Human-in-the-loop sign-off on every order; full audit log of agent reasoning; dossiers cite evidence, humans decide.
5. **"Business model?"** → SaaS to municipal corporations under NCAP budgets; CSR/ESG dashboards for industry; API for insurers/health systems. TAM anchor: NCAP outlay > ₹10,000 crore.

---

## 13. What I Build For You Next (in order)

1. **Working prototype** — the full stack above, demo-path first (forecast → attribution → dossier), then breadth.
2. **Detailed submission PDF** — the judged document, built from this blueprint + real backtest numbers once the models run.
3. **Architecture diagram** — clean, judge-readable.
4. **Pitch deck** — 10–12 slides following the video narrative.
5. **README + repo hygiene** — pitch-grade.

Say the word and I start with the data pipelines + Forecaster backtest, because every downstream claim depends on that number.
