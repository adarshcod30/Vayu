"""Run the evidence scout and persist candidates to `scouted_evidence`.

Three scouts, one shape each: build a search query for the city → search the web
→ hand the hits to the model with a strict extraction prompt → get JSON items →
write them as `pending`. Idempotent by a content hash id, so re-running a sweep
updates rather than duplicates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from loguru import logger

from vayu_core.config import CityConfig, get_settings, load_city
from vayu_core.db import upsert_df

from .llm import extract_json
from .search import SearchHit, web_search

KINDS = ("grap_stage", "construction", "incident")

# City name used in queries; the config `name` is the display label.
_EXTRACT_SYS = (
    "You extract structured air-quality intelligence for a pollution-control "
    "command centre in India. Return ONLY a JSON array. Each item: "
    '{"title": str, "summary": str (<=240 chars), "lat": number|null, '
    '"lon": number|null, "confidence": number 0-1, "source_index": int}. '
    "source_index is the 0-based index of the search result the item comes from. "
    "Include lat/lon only if the text names a specific place you are confident "
    "about; otherwise null. Omit anything not clearly relevant. No prose."
)


def _query(kind: str, city: CityConfig, at: datetime) -> str:
    name = city.name
    month = at.strftime("%B %Y")
    if kind == "grap_stage":
        return f"CAQM GRAP stage currently in force {name} NCR air quality {month}"
    if kind == "construction":
        return f"large construction demolition project dust {name} RERA {month}"
    return f"{name} air pollution incident industrial fire landfill stubble burning {month}"


def _prompt(kind: str, city: CityConfig, hits: list[SearchHit]) -> str:
    lines = [f"City: {city.name}. Layer: {kind}.", "", "Search results:"]
    for i, h in enumerate(hits):
        lines.append(f"[{i}] {h.title}\n{h.content}\nURL: {h.url}")
    intent = {
        "grap_stage": "Extract the single GRAP stage (I-IV) that is currently in force and when it was ordered.",
        "construction": "Extract active large construction/demolition sites likely to raise dust.",
        "incident": "Extract discrete pollution incidents (fires, landfill/industrial events, stubble reports).",
    }[kind]
    lines += ["", intent, "Return the JSON array now."]
    return "\n".join(lines)


def _id(kind: str, city_id: str, title: str, url: str) -> str:
    h = hashlib.sha1(f"{kind}|{city_id}|{title}|{url}".encode()).hexdigest()[:16]
    return f"scout-{kind}-{h}"


@dataclass
class ScoutResult:
    enabled: bool
    reason: str = ""
    found: int = 0
    written: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)


def _scout_kind(kind: str, city: CityConfig, at: datetime) -> list[dict]:
    hits = web_search(_query(kind, city, at), max_results=6, days=5)
    if not hits:
        return []
    items = extract_json(_EXTRACT_SYS, _prompt(kind, city, hits))
    if not isinstance(items, list):
        return []
    s = get_settings()
    rows = []
    for it in items:
        if not isinstance(it, dict) or not it.get("title"):
            continue
        idx = it.get("source_index")
        hit = hits[idx] if isinstance(idx, int) and 0 <= idx < len(hits) else None
        rows.append(
            {
                "id": _id(kind, city.id, str(it["title"]), hit.url if hit else ""),
                "city": city.id,
                "kind": kind,
                "title": str(it["title"])[:300],
                "summary": str(it.get("summary", ""))[:240],
                "lat": _num(it.get("lat")),
                "lon": _num(it.get("lon")),
                "source_url": hit.url if hit else "",
                "source_name": hit.title if hit else "",
                "published": (hit.published if hit else None) or "",
                "scouted_ts": at,
                "model": s.bedrock_model_id,
                "confidence": _num(it.get("confidence")) or 0.5,
                "status": "pending",
                "raw_json": json.dumps(it),
            }
        )
    return rows


def _num(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def run_scout(city_id: str, kinds: tuple[str, ...] = KINDS) -> ScoutResult:
    """Scout `city_id` across `kinds`, persisting pending candidates.

    Never raises for missing config/keys: returns `enabled=False` with a reason
    so the API and scheduled job can report it plainly.
    """
    s = get_settings()
    if not s.scout_enabled:
        return ScoutResult(
            enabled=False,
            reason="Scout needs BEDROCK_MODEL_ID and a search provider (SEARCH_PROVIDER + key) in .env.",
        )

    city = load_city(city_id)
    at = s.now()
    all_rows: list[dict] = []
    by_kind: dict[str, int] = {}
    for kind in kinds:
        try:
            rows = _scout_kind(kind, city, at)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[{city_id}] scout {kind} failed: {exc}")
            rows = []
        by_kind[kind] = len(rows)
        all_rows.extend(rows)

    written = 0
    if all_rows:
        from vayu_core.db import write_conn

        df = pd.DataFrame(all_rows)
        with write_conn() as con:
            written = upsert_df(con, "scouted_evidence", df, ["id"])
    logger.info(f"[{city_id}] scout: found {len(all_rows)}, wrote {written} — {by_kind}")
    return ScoutResult(enabled=True, found=len(all_rows), written=written, by_kind=by_kind)
