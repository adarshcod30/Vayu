"""Web search for the scout — Tavily (default) or Brave, via plain REST.

Deliberately the REST APIs, not an MCP client: the scout runs headless on a
schedule (EventBridge → Fargate) where an interactively-authenticated MCP server
isn't present. A REST call with a key from the environment always works there.
"""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass

import certifi
from loguru import logger

from vayu_core.config import get_settings

_TIMEOUT = 20

# Use the certifi CA bundle explicitly. Python on macOS often can't find the
# system root certs, so a bare urlopen fails HTTPS with CERTIFICATE_VERIFY_FAILED
# — the same issue the data.gov.in ingestor hit. certifi ships the roots.
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


@dataclass
class SearchHit:
    title: str
    url: str
    content: str
    published: str | None = None


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_SSL_CTX) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _tavily(query: str, key: str, max_results: int, days: int) -> list[SearchHit]:
    data = _post_json(
        "https://api.tavily.com/search",
        {
            "api_key": key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "days": days,
            "include_answer": False,
        },
        headers={},
    )
    return [
        SearchHit(
            title=r.get("title", ""),
            url=r.get("url", ""),
            content=r.get("content", ""),
            published=r.get("published_date"),
        )
        for r in data.get("results", [])
    ]


def _brave(query: str, key: str, max_results: int) -> list[SearchHit]:
    q = urllib.parse.quote(query)
    req = urllib.request.Request(
        f"https://api.search.brave.com/res/v1/web/search?q={q}&count={max_results}",
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_SSL_CTX) as resp:  # noqa: S310
        data = json.loads(resp.read().decode())
    return [
        SearchHit(title=r.get("title", ""), url=r.get("url", ""), content=r.get("description", ""))
        for r in data.get("web", {}).get("results", [])
    ]


def web_search(query: str, max_results: int = 6, days: int = 3) -> list[SearchHit]:
    """Search the web with the configured provider. Returns [] on any failure or
    when no provider is configured — the scout degrades to "found nothing" rather
    than raising, so a missing key never breaks a run."""
    s = get_settings()
    try:
        if s.search_provider == "tavily" and s.tavily_api_key:
            return _tavily(query, s.tavily_api_key, max_results, days)
        if s.search_provider == "brave" and s.brave_api_key:
            return _brave(query, s.brave_api_key, max_results)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"web_search failed for {query!r}: {exc}")
        return []
    logger.warning(f"no search provider configured (search_provider={s.search_provider!r})")
    return []
