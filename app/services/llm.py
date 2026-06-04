"""Thin OpenAI wrapper.

Generates a natural-language narrative for a recommendation. The whole engine
is designed to work *without* an API key: if OpenAI is unavailable or disabled,
callers fall back to the deterministic explanation. This keeps the service
demoable, testable, and resilient.
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def is_available() -> bool:
    s = get_settings()
    return bool(s.llm_enabled and s.openai_api_key)


def generate_narrative(prompt: str) -> str | None:
    """Return an LLM narrative, or None if unavailable / on error."""
    settings = get_settings()
    if not is_available():
        return None
    try:
        from openai import OpenAI  # imported lazily so the dep is optional

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an SRE assistant. Explain an upgrade recommendation "
                        "clearly and concisely for an on-call engineer. Be specific, "
                        "do not invent facts beyond the provided context."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return resp.choices[0].message.content
    except Exception as exc:  # network, auth, quota, etc.
        logger.warning("LLM narrative generation failed, falling back: %s", exc)
        return None
