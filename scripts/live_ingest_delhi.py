"""One-off: ingest TODAY's live Delhi data and score it, to demonstrate live mode.
Run with DEMO_MODE=false so the pipeline takes its live-fetch paths.
"""
from loguru import logger

from vayu_core.config import get_settings, load_city
from vayu_core.db import init_db

s = get_settings()
logger.info(f"demo_mode={s.demo_mode} now={s.now():%Y-%m-%d %H:%M %Z}")
init_db()

from services.api.scoring import ensure_forecasts, reset_forecaster
from services.pipeline.seed import seed_city

city = load_city("delhi")
seed_city(city, force=True)
reset_forecaster()
run_ts = ensure_forecasts("delhi", s.now())
logger.success(f"live ingest done — forecast run_ts={run_ts}")
