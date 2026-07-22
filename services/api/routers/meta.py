"""Health and evaluation metadata (the Methodology page reads these)."""

from __future__ import annotations

import json

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vayu_core.config import (
    REPO_ROOT,
    clock_override,
    get_settings,
    list_cities,
    set_clock,
    set_demo_mode,
)
from vayu_core.db import read_conn

from ..schemas import HealthOut

router = APIRouter(tags=["meta"])

# Curated demo episodes (Phase L, memory hardening): the date picker in Demo
# mode no longer lets the operator pick an arbitrary hour. Render's free tier
# is 512MB, and on-demand scoring an arbitrary never-before-seen hour — while
# individually cheap (~1.5s, windowed) — was enough added pressure on top of
# DuckDB's own footprint to occasionally tip the instance into an OOM kill.
# These 5 hours are already scored (sitting in the `forecasts` table from
# earlier runs), so selecting one is a plain read — no scoring computation at
# all. They're real measured episodes across the season, not synthetic: a
# clean day, the season's first uptick, the crisis building, the flagship
# severe episode (3 Nov), and the season's worst hour — an honest arc rather
# than a false "spread across the whole year" (Delhi's pollution is seasonal;
# nothing severe happens in July, which is the point of the Live toggle).
# Live mode is unaffected — its free date/time picker still works for any
# hour, because on-demand scoring for arbitrary Live dates already has its own
# windowed cap and doesn't run the far heavier live gap-fill.
DEMO_DATES: dict[str, list[dict]] = {
    "delhi": [
        {"at": "2025-09-03T17:00:00Z", "label": "Clean day", "aqi": 55, "category": "Good"},
        {"at": "2025-09-17T17:00:00Z", "label": "Early-season uptick", "aqi": 107, "category": "Moderate"},
        {"at": "2025-10-24T17:00:00Z", "label": "Crisis building", "aqi": 337, "category": "Very Poor"},
        {"at": "2025-11-03T06:00:00Z", "label": "Flagship severe episode", "aqi": 373, "category": "Very Poor"},
        {"at": "2025-11-24T00:00:00Z", "label": "Peak of the season", "aqi": 405, "category": "Severe"},
    ],
}


class ClockIn(BaseModel):
    as_of: datetime | None = None  # None clears the pin (back to demo/live)


class ModeIn(BaseModel):
    demo_mode: bool
    city_id: str = "delhi"  # which city to gap-fill when switching to live


def _clock_state() -> dict:
    settings = get_settings()
    pinned = clock_override()
    with read_conn() as con:
        row = con.execute("SELECT min(ts), max(ts) FROM measurements").fetchone()
    lo, hi = (row or (None, None))
    now = settings.now()
    # In live mode the operator may pick any hour up to *today* (data fills in as
    # the refresh job ingests). In demo mode selection is bounded to the bundled
    # coverage — there is nothing beyond it to show.
    max_selectable = now if not settings.demo_mode else hi
    from ..livefill import active

    return {
        "now": now,
        "demo_mode": settings.demo_mode,
        "source": "override" if pinned is not None else ("demo" if settings.demo_mode else "live"),
        "live": pinned is None and not settings.demo_mode,
        "pinned": pinned is not None,
        # The window the operator can time-travel within.
        "data_min": lo,
        "data_max": hi,
        "max_selectable": max_selectable,
        # Cities with a live gap-fill in flight — the UI polls /clock and
        # refetches everything when this empties.
        "filling": active(),
    }


@router.get("/clock")
def get_clock() -> dict:
    """The app's effective clock + the date range the picker can select within."""
    return _clock_state()


@router.get("/demo-dates")
def get_demo_dates(city_id: str = "delhi") -> dict:
    """The curated Demo-mode episodes — see DEMO_DATES for why these exist."""
    return {"city": city_id, "dates": DEMO_DATES.get(city_id, [])}


@router.post("/clock")
def post_clock(body: ClockIn) -> dict:
    """Pin the whole app to `as_of` (any hour with data), or clear to demo/live.

    Every read surface keys off `settings.now()`, so this moves the nowcast,
    forecast horizons, alerts, GRAP stage and ROI together to the chosen instant.
    Forecasts for that hour are scored on demand on first request.
    """
    set_clock(body.as_of)
    return _clock_state()


@router.get("/mode")
def get_mode() -> dict:
    return _clock_state()


@router.post("/mode")
def post_mode(body: ModeIn) -> dict:
    """Toggle demo/live at runtime. Demo OFF → live wall clock + live feeds for
    today; demo ON → bundled past data pinned to DEMO_NOW.

    Switching to live kicks a background gap-fill (CPCB + OpenAQ + weather ±6d
    + FIRMS) so today's map, forecast and trajectory populate within ~a minute —
    the product rule: dates past the archive are fetched, never refused.
    """
    set_demo_mode(body.demo_mode)
    if not body.demo_mode:
        from ..livefill import fill_city_async

        # Always refresh on switch: whether it's today or 25 days from now, the
        # click assembles the present-day picture (CPCB/OpenAQ + weather ±6d +
        # FIRMS + scout) and scores the current hour.
        fill_city_async(body.city_id)
    return _clock_state()


@router.post("/livefill")
def post_livefill(city_id: str = "delhi", wait: bool = False) -> dict:
    """Explicitly gap-fill today's live data for a city. `wait=true` runs it
    synchronously and returns the row counts (used for verification/demos)."""
    if wait:
        from ..livefill import fill_city

        return fill_city(city_id)
    from ..livefill import fill_city_async, filling

    started = fill_city_async(city_id)
    return {"city": city_id, "started": started, "already_running": not started and filling(city_id)}


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    try:
        with read_conn() as con:
            wards = con.execute("SELECT count(*) FROM wards").fetchone()[0]
            meas = con.execute("SELECT count(*) FROM measurements").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        return HealthOut(
            status="degraded",
            demo_mode=settings.demo_mode,
            now=settings.now(),
            cities=[c.id for c in list_cities()],
            seeded=False,
            detail=f"database unavailable: {exc}",
        )

    seeded = wards > 0 and meas > 0
    return HealthOut(
        status="ok" if seeded else "degraded",
        demo_mode=settings.demo_mode,
        now=settings.now(),
        cities=[c.id for c in list_cities()],
        seeded=seeded,
        detail="" if seeded else "no data yet — run `make seed`",
    )


@router.get("/meta/evaluation")
def evaluation() -> dict:
    """Backtest metrics for the Methodology page.

    Generated by `make backtest` in Phase 2; until then this reports honestly
    that it has not been run rather than shipping placeholder numbers.
    """
    path = REPO_ROOT / "docs" / "evaluation.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Backtest has not been run yet — `make backtest` generates docs/evaluation.md (Phase 2).",
        )
    return json.loads(path.read_text())
