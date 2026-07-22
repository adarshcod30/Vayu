"""Hourly refresh (L1c): ingest the latest live data, then score the current hour.

Reuses the same ingest as `make seed` — it already degrades gracefully per source
and does INSERT OR REPLACE — but instead of rebuilding the full training frame
(the slow part of seeding), it scores just the current hour with the fast
windowed path (L1a). That keeps a scheduled run to a few seconds per city.

Run: `python -m services.jobs.refresh`  (add `--scout` to also sweep evidence.)
"""

from __future__ import annotations

import sys

from loguru import logger

from vayu_core.config import get_settings, list_cities
from vayu_core.db import init_db


def refresh(do_scout: bool = False) -> int:
    settings = get_settings()
    if settings.demo_mode:
        logger.warning("DEMO_MODE is on — refresh will re-fetch nothing new. Set DEMO_MODE=false for live.")

    init_db()

    # Pull the latest hot DB from S3 first so we append to shared state, not a
    # stale local copy (no-op offline).
    from vayu_core.storage import pull_hot_db

    pull_hot_db(overwrite=True)

    from services.api.scoring import ensure_forecasts, reset_forecaster
    from services.pipeline.seed import seed_city

    at = settings.now()
    for city in list_cities():
        try:
            seed_city(city, force=True)  # live fetch of measurements/weather/fires
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{city.id}] ingest error (continuing): {exc}")

    reset_forecaster()  # artifacts may have been swapped by a retrain
    scored = 0
    for city in list_cities():
        run_ts = ensure_forecasts(city.id, at)
        if run_ts is not None:
            scored += 1

    if do_scout and settings.scout_enabled:
        from vayu_core.scout import run_scout

        for city in list_cities():
            run_scout(city.id)

    from vayu_core.storage import push_hot_db

    push_hot_db()
    logger.success(f"refresh complete — scored {scored} cities at {at:%Y-%m-%d %H:%M UTC}")
    return 0


def main() -> int:
    logger.remove()
    logger.add(sys.stderr, format="<level>{level: <8}</level> {message}", level="INFO")
    return refresh(do_scout="--scout" in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
