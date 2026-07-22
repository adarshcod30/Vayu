# 01 — Product Requirements Document (PRD)
## VAYU — Verifiable Airshed Intelligence & Enforcement

| | |
|---|---|
| Version | 1.0 |
| Status | Approved for build |
| Companion docs | `VAYU_MASTER_BUILD_PROMPT.md` (build order/scope), `02_TRD.md` (how), `03_App_Flow.md` (UX behavior) |
| Context | ET AI Hackathon 2026 — Problem Statement 5 |

---

## 1. Vision & Problem

**Vision:** Make every polluting source in an Indian city *findable, actionable, and accountable* within minutes — not committee-weeks.

**Problem:** India operates 900+ air quality monitoring stations, yet a 2024 CAG audit found 69% of monitored cities have no actionable response protocol connected to those readings. Existing systems stop at *measurement* (CPCB SAMEER), *forecast* (SAFAR, 4 cities), or *attribution without action* (IITM DSS — Delhi-only, winter-only, supercomputer-bound). The gap is the loop between a bad reading and a specific, evidence-backed enforcement act — and a check on whether it worked.

**Product thesis:** VAYU is not a dashboard. It is an intervention engine. Its atomic unit of value is the **Intervention Order** — a dispatch-ready evidence dossier — and its differentiating promise is the **closed loop**:

```
READING → RESPONSIBLE SOURCE → RANKED INTERVENTION → ENFORCEMENT ORDER → VERIFIED OUTCOME
```

## 2. Goals & Success Metrics

### 2.1 Hackathon success metrics (what judges must see)
| Metric | Target | Where proven |
|---|---|---|
| Forecast RMSE vs persistence baseline | Beat persistence by a measurable margin on 30 held-out days of real CPCB data | `docs/evaluation.md`, Methodology page, README |
| Hazard-crossing detection (AQI>300) | Precision & recall reported honestly | evaluation.md |
| Signal → dispatched dossier time | < 5 minutes, displayed as live stopwatch | Verify page, Agent drawer |
| Attribution traceability | 100% of attribution percentages click through to concrete evidence | Ward Detail |
| Language coverage | ≥ 3 languages on citizen advisories | Citizen page |
| City onboarding cost | New city = 1 config file, demonstrated live (Delhi → Lucknow switch) | Command Center |
| Cold-start reproducibility | `git clone → make seed → make dev` to full app < 10 min, zero API keys | README quickstart |

### 2.2 Product metrics (post-hackathon narrative)
µg/m³ averted per intervention; population-hours of exposure avoided; % of interventions with verified outcomes; municipal response time reduction (days → minutes).

## 3. Personas

### P1 — The Commissioner (primary)
Municipal/Smart City official responsible for NCAP targets and GRAP compliance.
- **Jobs:** know where air will be worst before it happens; justify enforcement decisions to CAQM/courts/press; deploy limited inspection teams for maximum effect.
- **Pains:** data scattered across CPCB portals; attribution is guesswork; enforcement is reactive and legally fragile; no way to prove an action worked.
- **Success moment:** clicks one alert → sees who is responsible with evidence → dispatches the top-ROI action → shows the verified µg/m³ saved in the next review meeting.

### P2 — The Field Inspector
Pollution control board / municipal enforcement staff.
- **Jobs:** receive clear orders; reach the right site; carry defensible evidence; report back fast.
- **Pains:** vague instructions ("check burning near X"); paperwork; challenges to authority on site.
- **Success moment:** opens order on phone → map pin, evidence photos/satellite proof, regulation citation → marks executed in two taps.

### P3 — The Citizen / Institution (school admin, parent, outdoor worker)
- **Jobs:** decide when to be outdoors; protect children/elderly; get told *what to do*, not just a number.
- **Pains:** AQI apps give a city-wide number and generic advice, in English.
- **Success moment:** sees ward-level "Best air today 6–9 AM" in Hindi; school gets a targeted plume alert before sports day.

## 4. Epics & User Stories (P0 = demo-critical, P1 = strongly expected, P2 = if time allows)

### Epic A — See & Foresee (Forecasting)
- **A1 (P0)** As a Commissioner, I see current AQI per ward on a city map with live/cached status, so I trust what I'm seeing. *AC: choropleth + station markers; CPCB color buckets; data-freshness pill.*
- **A2 (P0)** I see 24/48/72h ward-level forecasts with uncertainty bands. *AC: p10/p50/p90; threshold lines at 200/300/400; time scrubber animates the city grid.*
- **A3 (P0)** I receive an alert when any ward is predicted to cross AQI 300 within 48h. *AC: alert card with ward, ETA, confidence; click → Ward Detail.*
- **A4 (P1)** I can ask "why this forecast?" *AC: top-6 SHAP feature contributions in plain English.*
- **A5 (P1)** As a judge, I can inspect the backtest. *AC: Methodology page shows RMSE/MAE vs persistence & climatology + calibration chart, auto-generated from real held-out data.*

### Epic B — Name the Source (Attribution)
- **B1 (P0)** For a flagged ward I see source attribution (burning/traffic/construction/industry/regional) with confidence per category. *AC: donut with confidence rings; formula documented on Methodology page.*
- **B2 (P0)** Every attribution claim traces to evidence. *AC: clicking a slice highlights fire pixels / permit rows / trajectory on map and lists items with timestamps and distances.*
- **B3 (P0)** I can watch where the ward's air came from. *AC: animated 6–24h wind back-trajectory with dispersion cone (deck.gl TripsLayer).*
- **B4 (P2)** Satellite NO₂ overlay strengthens industry/traffic evidence when GEE key present. *AC: layer hidden gracefully when absent.*

### Epic C — Act (Intervention & Enforcement)
- **C1 (P0)** I see intervention options ranked by ROI. *AC: leaderboard with µg/m³ averted, people protected, effort, confidence; row expands to counterfactual with/without chart.*
- **C2 (P0)** One click generates an evidence dossier PDF. *AC: contains map snapshot, evidence table, regulation citation with source, predicted impact, order ID, sign-off block; saved and downloadable.*
- **C3 (P0)** Dispatch sends the order to the Inspector view. *AC: appears in inspector list; status → Dispatched.*
- **C4 (P1)** GRAP Autopilot drafts stage measures when a stage crossing is forecast. *AC: drafted list with clause citations; requires explicit human Approve; badge "human-in-the-loop".*
- **C5 (P1)** As an Inspector, I mark an order executed with a note. *AC: status → Executed; verification tracking starts.*

### Epic D — Protect People Meanwhile (Citizen)
- **D1 (P0)** As a citizen, I see my ward's AQI, 48h forecast, and Clean Hours windows. *AC: light theme; huge AQI numeral; green time blocks.*
- **D2 (P0)** I read audience-specific advisories in my language. *AC: EN/HI/+1; audiences: general, children/schools, outdoor workers, elderly/respiratory; templated fallback when no LLM key.*
- **D3 (P1)** As a Commissioner, I alert institutions in a forecast plume. *AC: schools/hospitals in plume flagged; "Notify N schools" → mock WhatsApp panel showing actual message bubbles in selected language.*

### Epic E — Prove It Worked (Verification)
- **E1 (P0)** For an executed intervention I see predicted vs observed impact. *AC: diff-in-diff vs 3 weather-matched control wards; "% of predicted realized"; honest CI; one seeded demo record per city badged "Seeded demo record".*
- **E2 (P1)** I see the response-time stopwatch per intervention. *AC: elapsed signal→dossier; target <5 min displayed.*

### Epic F — Trust & Auditability (cross-cutting)
- **F1 (P0)** Agent Activity drawer streams every automated step with reasoning and confidence. *AC: agent-tagged entries; SSE live updates during demo.*
- **F2 (P0)** Honesty labels. *AC: live/cached pill per data layer; "Sample data" badge on curated layers; limitations section on Methodology page.*

### Epic G — Scale (Multi-city)
- **G1 (P0)** Switch Delhi ↔ Lucknow instantly. *AC: all surfaces re-render from `config/cities/*.json`; no hardcoded city logic anywhere.*

## 5. Functional Requirements → PS 5 mapping

| PS "What You May Build" bullet | VAYU epic |
|---|---|
| Geospatial Pollution Source Attribution Engine | Epic B |
| Hyperlocal Predictive AQI Forecasting Agent | Epic A |
| Enforcement Intelligence & Prioritisation Agent | Epic C |
| Multi-City Comparative Intelligence Dashboard | Epic G + E (verified interventions comparable across cities) |
| Citizen Health Risk Advisory System | Epic D |

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | Initial load < 3s on broadband; map interactions 60fps; API p95 < 500ms in DEMO_MODE |
| Reliability | Zero unhandled exceptions in golden flow; every async block has loading/empty/error states |
| Offline | Full app runs with no keys/no network via bundled samples (`DEMO_MODE=true`) |
| Accessibility | Keyboard navigable; WCAG AA contrast; AQI never conveyed by color alone (always number + label) |
| Responsiveness | Command Center ≥1280px optimized; Citizen & Inspector mobile-first |
| Integrity | No fabricated data presented as real; formulas documented; limitations stated |
| Auditability | Every automated decision logged with inputs, reasoning, confidence, duration |
| I18n | Advisory content externalized; ≥3 languages |

## 7. Out of Scope (explicitly)

Authentication/user accounts, real WhatsApp/SMS delivery, payments, admin CMS, chemistry-transport modeling (WRF/CMAQ), real-time CCTV/traffic-camera ingestion, native mobile apps, Kubernetes. Rationale: every hour goes to the golden flow.

## 8. Release Plan

Maps 1:1 to Phases 1–6 in `VAYU_MASTER_BUILD_PROMPT.md` §14. P0 stories land in Phases 1–5; P1 in Phases 4–6; P2 only after the Final Acceptance Checklist passes.

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OpenAQ/CPCB API instability during judging | Demo breaks | DEMO_MODE offline bundle is the default demo path; live is a bonus |
| Forecast barely beats persistence | Weak evidence story | Report honestly + emphasize hazard-crossing recall (the decision-relevant metric); tune features (upwind station, fires) which drive the edge |
| Ward boundary data unavailable (Lucknow) | Blocks hyperlocal claim | H3 hex "analysis zones" fallback, labeled as such |
| Judges challenge attribution rigor | Credibility | Confidence scores, documented formula, cross-check vs published IITM DSS Delhi splits, limitations section |
| LLM key absent/rate-limited on stage | Advisory/RAG breaks | llm_cache.json pre-generated fallback for every demo-path call |
| Scope creep | Nothing polished | Phase gates + §11 "What NOT to build" are binding |

## 10. Open Questions (resolve during build, don't block)

1. Lucknow ward GeoJSON sourcing — municipal portal vs H3 fallback (decide in Phase 1).
2. Third language for advisories — Urdu vs Tamil vs Bengali (pick based on demo city; Hindi + English fixed).
3. Population per ward for Delhi — Census 2011 ward table vs uniform estimate (prefer real, labeled with source).
