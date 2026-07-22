"""S3 as the source of truth (Phase L deployment).

Core principle: nothing heavy lives in git or the container image. The API pulls
a "hot" DuckDB from S3 on boot; the scheduled jobs push it back after each
ingest/score/retrain. Full history stays as partitioned Parquet on S3 and is
queried directly via DuckDB httpfs for backtests (out of scope here).

Every function is a no-op (returns False) when `VAYU_S3_BUCKET` is unset, so the
exact same code runs offline in the demo and online in AWS with only env
differences — the twelve-factor split the rest of VAYU already follows.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from vayu_core.config import get_settings
from vayu_core.db import db_file


def _client():
    import boto3

    s = get_settings()
    kwargs = {"region_name": s.aws_region}
    if s.aws_access_key_id and s.aws_secret_access_key:
        kwargs["aws_access_key_id"] = s.aws_access_key_id
        kwargs["aws_secret_access_key"] = s.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def _key(name: str) -> str:
    return f"{get_settings().vayu_s3_prefix}/{name}".lstrip("/")


def hot_db_key() -> str:
    return _key("hot/vayu.duckdb")


def enabled() -> bool:
    return bool(get_settings().vayu_s3_bucket)


def push_hot_db() -> bool:
    """Upload the local DuckDB to S3. Returns True on success."""
    if not enabled():
        return False
    s = get_settings()
    path = db_file()
    if not path.exists():
        logger.warning("push_hot_db: local DB does not exist yet")
        return False
    try:
        _client().upload_file(str(path), s.vayu_s3_bucket, hot_db_key())
        logger.info(f"pushed hot DB → s3://{s.vayu_s3_bucket}/{hot_db_key()}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"push_hot_db failed: {exc}")
        return False


def pull_hot_db(overwrite: bool = True) -> bool:
    """Download the hot DuckDB from S3 to the local path. Returns True on success."""
    if not enabled():
        return False
    s = get_settings()
    path = db_file()
    if path.exists() and not overwrite:
        return False
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _client().download_file(s.vayu_s3_bucket, hot_db_key(), str(path))
        logger.info(f"pulled hot DB ← s3://{s.vayu_s3_bucket}/{hot_db_key()}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"pull_hot_db failed (first boot before any push?): {exc}")
        return False


def maybe_pull_on_boot() -> bool:
    """Pull the hot DB if a bucket is configured and there's no local DB yet.

    Called by the API entrypoint. In the demo (no bucket) this is a no-op and the
    bundled DB is used unchanged.
    """
    if not enabled():
        return False
    if db_file().exists():
        logger.info("local DB present; skipping S3 pull (set VAYU_FORCE_PULL to override)")
        return False
    return pull_hot_db()
