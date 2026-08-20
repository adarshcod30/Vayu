"""Thin Gemini client — REST, no SDK.

Deliberately `urllib` against the public generateContent endpoint rather than
`google-generativeai`. VAYU already talks to CPCB, FIRMS, Open-Meteo and DLR the
same way, the request shape is three fields, and it keeps the container free of
a dependency tree whose only job is to build that JSON. It also means the Vertex
path is a different URL rather than a different library.

Everything raises `GeminiUnavailable` rather than returning a plausible-looking
default: callers must decide what to show a user when the model cannot be
reached, and silently substituting a guess for a pollution measurement is not an
option this project accepts.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request

import certifi
from loguru import logger

from vayu_core.config import get_settings

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_TIMEOUT = 60

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiUnavailable(RuntimeError):
    """Gemini could not be reached, or no credentials are configured."""


def available() -> bool:
    return get_settings().google_ai_available


def _endpoint(model: str, key: str) -> str:
    return f"{API_ROOT}/{model}:generateContent?key={key}"


def generate(
    parts: list[dict],
    *,
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    model: str | None = None,
) -> str:
    """Single-turn call. `parts` is Gemini's content-parts list, so the same
    function serves text-only and image+text (multimodal) requests.

    Temperature defaults to 0: every use here is an extraction or a grounded
    summary, where run-to-run variation is a bug, not creativity.
    """
    s = get_settings()
    if not s.google_api_key:
        raise GeminiUnavailable(
            "GOOGLE_API_KEY is not set — get a free key at aistudio.google.com/apikey"
        )

    body: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    req = urllib.request.Request(
        _endpoint(model or s.gemini_model, s.google_api_key),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_SSL_CTX) as r:  # noqa: S310
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:300] if hasattr(exc, "read") else ""
        raise GeminiUnavailable(f"Gemini HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise GeminiUnavailable(f"Gemini call failed: {type(exc).__name__}: {exc}") from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        # A blocked prompt returns no candidates but does carry the reason.
        reason = (payload.get("promptFeedback") or {}).get("blockReason", "no candidates")
        raise GeminiUnavailable(f"Gemini returned nothing ({reason})")

    out = "".join(
        p.get("text", "") for p in (candidates[0].get("content") or {}).get("parts", [])
    )
    if not out.strip():
        raise GeminiUnavailable("Gemini returned an empty response")
    return out


def generate_json(parts: list[dict], **kw) -> dict | list:
    """`generate` + strict JSON parse, tolerating ```json fences and prose.

    Gemini supports a responseMimeType of application/json, but it is not
    honoured by every model revision, so the fence-stripping fallback stays.
    """
    raw = generate(parts, **kw)
    text = raw.strip()

    if "```" in text:
        block = text.split("```", 2)
        text = block[1] if len(block) > 1 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: the outermost bracket pair, for replies wrapped in prose.
        for opener, closer in (("{", "}"), ("[", "]")):
            if opener in text and closer in text:
                frag = text[text.index(opener) : text.rindex(closer) + 1]
                try:
                    return json.loads(frag)
                except json.JSONDecodeError:
                    continue
    logger.warning(f"Gemini reply was not JSON: {raw[:200]!r}")
    raise GeminiUnavailable("Gemini did not return parseable JSON")
