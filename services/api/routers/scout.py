"""Evidence scout surface (L3): the human review queue.

Scouted items are advisory — badged "web-scouted · unverified" — and only a
person may promote them. Nothing here dispatches an order.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from vayu_core.config import get_settings
from vayu_core.db import read_conn, write_conn
from vayu_core.scout import run_scout

from ..deps import get_city

router = APIRouter(prefix="/scout", tags=["scout"])


@router.get("")
def list_scouted(
    city_id: str | None = None,
    status: str = Query("pending", description="pending | promoted | dismissed | all"),
    limit: int = 100,
) -> dict:
    s = get_settings()
    where = []
    params: list = []
    if city_id:
        where.append("city = ?")
        params.append(city_id)
    if status != "all":
        where.append("status = ?")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with read_conn() as con:
        df = con.execute(
            f"""SELECT id, city, kind, title, summary, lat, lon, source_url, source_name,
                       published, scouted_ts, model, confidence, status
                FROM scouted_evidence {clause}
                ORDER BY scouted_ts DESC, confidence DESC LIMIT ?""",
            [*params, limit],
        ).df()
    items = [
        {
            "id": r.id,
            "city": r.city,
            "kind": r.kind,
            "title": r.title,
            "summary": r.summary,
            "lat": None if r.lat != r.lat else float(r.lat),  # NaN guard
            "lon": None if r.lon != r.lon else float(r.lon),
            "source_url": r.source_url,
            "source_name": r.source_name,
            "published": r.published,
            "scouted_ts": None if r.scouted_ts is None else r.scouted_ts.isoformat(),
            "model": r.model,
            "confidence": float(r.confidence),
            "status": r.status,
            "badge": "web-scouted · unverified",
        }
        for r in df.itertuples()
    ]
    return {"enabled": s.scout_enabled, "items": items, "count": len(items)}


@router.post("/run")
def run(city_id: str = Query(...), kinds: str | None = None) -> dict:
    """Trigger a scout sweep for a city. `kinds` is an optional comma list."""
    get_city(city_id)  # 404 for unknown city
    ks = tuple(k.strip() for k in kinds.split(",")) if kinds else None
    result = run_scout(city_id, ks) if ks else run_scout(city_id)
    return {
        "enabled": result.enabled,
        "reason": result.reason,
        "found": result.found,
        "written": result.written,
        "by_kind": result.by_kind,
    }


def _set_status(scout_id: str, status: str) -> dict:
    with write_conn() as con:
        row = con.execute("SELECT id FROM scouted_evidence WHERE id = ?", [scout_id]).fetchone()
        if not row:
            raise HTTPException(404, f"unknown scouted item '{scout_id}'")
        con.execute("UPDATE scouted_evidence SET status = ? WHERE id = ?", [status, scout_id])
    return {"id": scout_id, "status": status}


@router.post("/{scout_id}/promote")
def promote(scout_id: str) -> dict:
    """Mark reviewed & accepted. Surfaces as corroborating evidence; a human still
    raises any resulting order through the normal interventions flow."""
    return _set_status(scout_id, "promoted")


@router.post("/{scout_id}/dismiss")
def dismiss(scout_id: str) -> dict:
    return _set_status(scout_id, "dismissed")
