"""Bedrock text/JSON extraction via the model-agnostic `converse` API.

`converse` works across Bedrock model families (Nova, Claude, Llama), so swapping
`BEDROCK_MODEL_ID` needs no code change. Nova on us-east-1 requires the regional
inference profile id (`us.amazon.nova-pro-v1:0`), which is what belongs in .env.
"""

from __future__ import annotations

import json

from loguru import logger

from vayu_core.config import get_settings


def _client():
    import boto3  # imported lazily: boto3 is only needed in live mode

    s = get_settings()
    kwargs = {"region_name": s.aws_region}
    if s.aws_access_key_id and s.aws_secret_access_key:
        kwargs["aws_access_key_id"] = s.aws_access_key_id
        kwargs["aws_secret_access_key"] = s.aws_secret_access_key
    return boto3.client("bedrock-runtime", **kwargs)


def converse(system: str, user: str, max_tokens: int = 1500, temperature: float = 0.0) -> str:
    """Single-turn completion. Returns the model's text, or "" on failure."""
    s = get_settings()
    if not s.bedrock_model_id:
        logger.warning("converse called with no BEDROCK_MODEL_ID")
        return ""
    try:
        resp = _client().converse(
            modelId=s.bedrock_model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"bedrock converse failed: {exc}")
        return ""


def extract_json(system: str, user: str, max_tokens: int = 1500) -> list | dict | None:
    """Converse and parse the reply as JSON, tolerating ```json fences and prose
    around the object. Returns None if nothing parseable comes back."""
    text = converse(system, user, max_tokens=max_tokens)
    if not text:
        return None
    t = text.strip()
    if "```" in t:
        # Pull the fenced block.
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    # Fall back to the outermost bracket pair if there's leading/trailing prose.
    for open_c, close_c in (("[", "]"), ("{", "}")):
        if open_c in t and close_c in t:
            frag = t[t.index(open_c) : t.rindex(close_c) + 1]
            try:
                return json.loads(frag)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        logger.warning(f"could not parse model JSON: {text[:200]!r}")
        return None
