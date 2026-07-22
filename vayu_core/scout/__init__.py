"""Live evidence scout (Phase L3).

For the pollution layers that have **no machine-readable feed** — the GRAP stage
actually in force, construction activity, and one-off incidents (industrial
fires, demolitions, stubble reports) — VAYU pairs a Bedrock LLM with a web-search
API. The scout searches, the model extracts structured candidates, and every
candidate lands in `scouted_evidence` as `pending`: badged
"web-scouted · unverified", it is never turned into an order until a human
promotes it. This is the guardrail — an LLM finding informs a commissioner; it
does not act on the city by itself.
"""

from .run import ScoutResult, run_scout

__all__ = ["ScoutResult", "run_scout"]
