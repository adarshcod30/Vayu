# Data Provenance

> VAYU's second non-negotiable principle: *real data wherever free APIs exist; honest
> labels everywhere else. Never fake something that could be real.*
>
> This page records exactly where every number on screen comes from, including the
> parts that are unflattering. If a layer is modelled rather than measured, it says
> so here, in the API (`source` / `data_status`), and on the UI pill.

## Summary

| Layer | Source | Key needed? | Measured or modelled | Status label |
|---|---|---|---|---|
| Ward boundaries | [DataMeet Municipal Spatial Data](https://github.com/datameet/Municipal_Spatial_Data) | no | real municipal polygons | `live` / `sample` |
| Station identity (name, lat/lon) | CPCB CAAQMS via [data.gov.in](https://data.gov.in) | no (public demo key) | **measured** network metadata | `live` |
| Current AQI (live mode) | CPCB CAAQMS via data.gov.in | no (public demo key) | **measured** | `live` |
| Historical hourly AQ (**in use**) | [OpenAQ v3](https://openaq.org) — CPCB/DPCC/IMD monitors | `OPENAQ_API_KEY` | **measured** | `live` |
| Historical hourly AQ (fallback) | [Open-Meteo Air Quality](https://open-meteo.com) (ECMWF CAMS reanalysis) | no | **modelled** | `cams` → pill reads *reanalysis* |
| Weather (history + forecast) | Open-Meteo | no | modelled (NWP/reanalysis — as all weather is) | `live` / `sample` |
| Fires | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) VIIRS | `FIRMS_API_KEY` | measured satellite detections | `sample` / `unavailable` |
| Schools, hospitals, industrial landuse | OpenStreetMap via Overpass | no | community-mapped | `live` / `sample` |
| Road density (traffic proxy) | OpenStreetMap major roads | no | community-mapped | `live` / `sample` |
| Construction permits | **curated on real OSM construction landuse** | no | **SAMPLE — see §6** | `sample` |
| Sentinel-5P NO₂ | Google Earth Engine | `GEE_SERVICE_ACCOUNT_JSON` | measured satellite column | `unavailable` when absent |
| Ward population | Census of India 2011 city totals, apportioned by ward area | no | **estimated** — see below | carried in `pop_source` |

---

## 1. The CPCB feed publishes sub-indices, not concentrations

India's official real-time feed (`data.gov.in` resource `3b01bcb8-…`) exposes fields
named `min_value` / `max_value` / `avg_value`. These are **CPCB sub-indices** (a
per-pollutant AQI), *not* concentrations — the field names actively mislead.

How we established this:

* CO reads ~52 nationally. As mg/m³ that is severe-poisoning territory; as µg/m³ it is
  below any physically possible ambient level. Read as a **sub-index**, 52 back-converts
  to **1.05 mg/m³** — a textbook urban value.
* Independent check: CAMS reports **1.36 mg/m³** at Anand Vihar for the same
  station-hour that the feed reported CO = 68 (sub-index 68 → **1.4 mg/m³**).
* Reading the values as concentrations puts every Delhi station at "AQI 500 Severe"
  in the middle of monsoon, which is plainly wrong.

VAYU therefore:

1. Takes station AQI **directly** as `max(sub-index)` — exact, no round-trip error.
2. Recovers concentrations by inverting the published CPCB breakpoint table
   (`vayu_core.aqi.concentration_from_sub_index`), which is piecewise-linear and
   strictly monotonic, so the inverse is exact up to the integer rounding of the
   published index (≈ ±1–3 µg/m³ across the PM2.5 range).

**Semantics that matter:** CPCB sub-indices are defined on 24-hour averages
(8-hour for CO/O₃). The recovered concentrations are therefore *24h averages*, not
instantaneous hourly values, and must not be mixed with hourly series uncritically.

## 2. The historical series: measured (OpenAQ) with a CAMS fallback

**With `OPENAQ_API_KEY` set (the current configuration)** the hourly history is
**measured** — the CPCB/DPCC/IMD CAAQMS network mirrored by OpenAQ, stored as
`source='openaq'`. Station identity and values are both real instrument readings.

**Without a key**, VAYU falls back to sampling the **ECMWF CAMS global reanalysis**
(Open-Meteo, no key) **at the real CPCB station coordinates** — real, physically
modelled data anchored to the actual network, labelled `cams-reanalysis` and shown as
*reanalysis* on the pill. The app still runs fully offline; the science is just weaker.

### Why the key matters: CAMS is spatially smooth, and biased low

CAMS runs on a ~40 km global grid, so Delhi spans about three cells. Measured on the
bundled window:

| Series | Stations | Distinct PM2.5 values |
|---|---|---|
| CAMS reanalysis at station coords | 44 | **3** |
| CPCB measured | 31 | **27** |

With three distinct values across 44 stations, a "hyperlocal, station-level forecast"
would be three series wearing 44 hats, and the upwind-station feature would be
meaningless (neighbouring stations are identical). CAMS also under-estimates: at Anand
Vihar on 2025-12-13 it reported a 217 µg/m³ daily mean against a **measured 498 µg/m³** —
roughly 2.3× low. Both facts are why measured data is the default and CAMS is the
fallback.

### Selecting the right sensor is not cosmetic

Many CPCB stations expose several OpenAQ sensors for one parameter. R K Puram has two
pm25 sensors: **id 35** (covering 2016→2018, now retired) and **id 12234787**
(2025→present). The `/v3/locations` payload carries no coverage dates, so any id-based
tie-break is a coin flip — and "lowest id" deterministically picks the *dead* one,
which returns zero rows.

VAYU therefore queries `/v3/locations/{id}/sensors` for each station and selects, per
parameter, the sensor whose `datetimeFirst`/`datetimeLast` actually overlap the
requested window. Of 98 Delhi locations in the bbox, **52 have live coverage** for the
demo window and 46 are correctly skipped as retired.

This mattered: the first backfill silently returned data for only **9 of 98** stations
and looked like a success. A partial backfill is the most dangerous failure mode for a
forecaster, so the ingestor now logs a warning whenever it gets fewer stations back than
it asked for.

## 3. Ward population is an estimate

Per-ward Census counts are not published machine-readably for either demo city. VAYU
apportions the **Census 2011** city total across wards **by polygon area** and records
that method in the `pop_source` column of every ward row, so any population figure on
screen carries how it was derived.

Sanity check: the 290 Delhi ward polygons sum to **1,490 km²** against the true NCT area
of ~1,483 km², confirming the equal-area projection used for the apportionment.

This is an estimate, and uniform density is wrong in detail — dense old-city wards are
under-counted and peri-urban wards over-counted. Any "people protected" figure inherits
that error. Replacing it with a real ward-level table is tracked as PRD Open Question 3.

## 4. The demo clock is pinned to a real, measured pollution episode

`DEMO_MODE=true` pins "now" to `DEMO_NOW=2025-11-03T06:00:00Z`. The timestamp was chosen
from **measured** CPCB data, not model output, and not for convenience.

The requirement is subtle: the golden flow forecasts a *crossing* of AQI 300, so the air
must be below 300 at the pinned clock and above it ~36–48 h later. Delhi's December sits
above 300 almost continuously — on 12 Dec, Anand Vihar already measured a 344 µg/m³ daily
mean (AQI 438). You cannot forecast a crossing that has already happened.

Scanning the measured city-mean series across the winter surfaced this window:

| Date | Measured city AQI |
|---|---|
| 2025-11-03 | **254** (Poor) |
| 2025-11-04 | 268 |
| 2025-11-05 | **351** (Very Poor) |

A genuine +97 AQI crossing over 48 h, at the peak of Punjab/Haryana stubble burning —
which is exactly the causal story the Attributor tells. (2025-11-05 is also Guru Nanak
Jayanti, a real confounder the `is_holiday` feature carries rather than hides.)

Today's date (July, monsoon) shows clean air and no crossing, which is why the demo
window is autumn.

## 5. What is *not* fabricated

* No fire pixels are invented. With no `FIRMS_API_KEY` and no bundled extract, the fires
  layer reports `unavailable` and hides — fabricating a fire would fabricate an
  enforcement target.
* No S5P layer is faked; it hides without credentials.
* `/meta/evaluation` returns **404 with an explanation** until `make backtest` has
  actually run, rather than shipping placeholder accuracy numbers.
* Wards with no nearby station are rendered grey and flagged `low_confidence`, never
  coloured green (which would imply clean air).

## 6. Construction permits are the one curated layer — and the accusation is ours

There is no public machine-readable feed of Delhi/Lucknow construction permits with
dust-control compliance status. Master prompt §2 permits a curated sample exactly here.
Two rules are enforced in code rather than by convention:

1. **Real geography.** The 30 Delhi sites are placed on *actual OSM construction /
   brownfield landuse polygons*, so a dispatched inspector would arrive somewhere that
   genuinely is a building site. (Lucknow has no such OSM landuse mapped, so its sites
   fall back to ward centroids — still real wards, and the log says so.)
2. **The badge travels with the data.** `source="Sample data — curated on real OSM
   construction landuse"` is attached to the *evidence item itself* in the API response,
   so the UI cannot forget to render the badge. `tests/test_fusion.py` asserts it.

**The dust-compliance flag is the fabricated part, and it is an accusation.** It is
derived deterministically from the site id (so the demo is reproducible), roughly 1 in 3
non-compliant. A non-compliant site is weighted ×2 in the attribution, which means this
flag can move an enforcement recommendation. Any dossier naming a construction action
must state on the document that the permit layer is sample data. Replacing this layer
with a real municipal feed is the single highest-value integration for a real deployment.

## 7. Traffic is a proxy, and says so

There is no free real-time vehicle-count feed for Indian cities, and the master prompt
rules out CCTV ingestion. VAYU therefore measures **weighted major-road km per km²** per
ward from OSM (motorway ×4, trunk ×3, primary ×2, secondary ×1 — a documented judgement),
modulated by hour-of-day and by **measured NO₂**, the tailpipe tracer VAYU does observe.

This is why `traffic` carries a negative confidence prior: a fire pixel is a direct
satellite observation of an event; a traffic share is inferred from road length and a
clock. The confidence ring shows that difference rather than hiding it.

## 8. Two documented departures from TRD 5.3

**Fire distance decay: 120 km, not the specified 20 km.** The TRD's `exp(−d/20km)` is
calibrated for local burning (its golden flow says "fire cluster 18 km upwind"). Punjab
stubble sits 150–250 km up the trajectory, where `exp(−200/20) ≈ 2e-5` — arithmetically
zero. Measured on real 3 Nov 2025 data, a fire sitting on the trajectory path scored
0.14 against a regional term of 45, and open burning came out at **0.3%**. PM2.5 has an
atmospheric lifetime of days; a ~120 km e-folding reflects plume dilution over that
transport, and matches the Forecaster's regional fire feature.

**Double-count guard.** A Punjab fire is simultaneously "open burning" and "regional
transport". Scoring both independently let regional swallow **99.7%** of a ward. VAYU now
subtracts identified out-of-city fires from the regional term, so `regional_transport`
means *imported pollution not traced to an identified source* — which is the honest and
operationally useful definition.

## 9. The attribution scales are calibrated, and the calibration is auditable

The five `SCALE` constants convert incompatible units (FRP in MW, landuse in km², roads
in km/km², trajectory geometry as a fraction) into summable scores. They are **not fitted
to ground truth** — no per-ward "true share of PM2.5 from burning" exists for any city.

They are calibrated so the city-wide balance lands inside Delhi's **published winter
source-apportionment ranges (IITM DSS / SAFAR)**, which TRD 5.3 explicitly asks us to
cross-check against. `make calibrate` re-derives them and writes
`docs/attribution_crosscheck.json`:

| Category | VAYU mean | Published | Agrees |
|---|---|---|---|
| Open burning | 26.3% | 10–40% | ✓ |
| Traffic | 21.1% | 15–25% | ✓ |
| Industry | 15.8% | 10–20% | ✓ |
| Construction | 10.5% | 5–15% | ✓ |
| Regional transport | 26.3% | 20–30% | ✓ |

Only the **balance** is anchored. All per-ward variation still comes from the evidence —
open burning ranges from **8% to 88%** across Delhi wards depending on which fires sit in
that ward's cone. Before calibration, industry alone read **65%** against a published
10–20%, because industry was scored by counting OSM features rather than by area (TRD 5.3
specifies area; a 9.62 km² estate and a 0.064 km² workshop had counted equally).
