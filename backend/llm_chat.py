# -*- coding: utf-8 -*-
"""Apeluri LLM unificate: OpenAI-compat (base URL opțional) sau Anthropic Claude."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from backend.config import settings

_log = logging.getLogger(__name__)


def llm_provider_normalized() -> str:
    raw = (
        getattr(settings, "llm_provider", None)
        or os.getenv("LLM_PROVIDER")
        or "openai"
    )
    p = (raw or "").strip().lower()
    return p if p in {"openai", "anthropic"} else "openai"


def resolve_model_name() -> str:
    """Numele modelului; dacă lipsește, implicit Haiku (Anthropic) sau gpt-4o-mini (OpenAI)."""
    m = (
        getattr(settings, "llm_model", None)
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or ""
    )
    m = (m or "").strip()
    if m:
        return m
    if llm_provider_normalized() == "anthropic":
        return "claude-haiku-4-5"
    return "gpt-4o-mini"


def audit_llm_has_credentials() -> bool:
    """Chei suficiente pentru audit Copilot / apeluri din llm_chat."""
    if llm_provider_normalized() == "anthropic":
        return bool(_anthropic_api_key())
    return bool(_openai_compatible_api_key())


def suggest_alias_llm_configured() -> bool:
    """Alias necunoscute: aceleași chei ca auditul (poți folosi același provider)."""
    return audit_llm_has_credentials()


def _anthropic_api_key() -> str:
    sk = (getattr(settings, "anthropic_api_key", None) or "").strip()
    if sk:
        return sk
    return (os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()


def _openai_compatible_api_key() -> str:
    return (
        os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY_3")
        or ""
    ).strip()


def chat_completion_system_user(
    system: str,
    user: str,
    *,
    max_tokens: int,
    temperature: float = 0.0,
) -> str:
    """
    Apel chat cu un singur mesaj user după system (cazul tipic buletin / alias).
    """
    prov = llm_provider_normalized()
    model = resolve_model_name()
    if prov == "anthropic":
        return _anthropic_system_user(
            system, user, model=model, max_tokens=max_tokens, temperature=temperature
        )
    return _openai_system_user(
        system, user, model=model, max_tokens=max_tokens, temperature=temperature
    )


def _anthropic_system_user(
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    try:
        import anthropic
    except ImportError as e:
        raise ImportError(
            "Pentru LLM_PROVIDER=anthropic instalează: pip install anthropic"
        ) from e
    key = _anthropic_api_key()
    if not key:
        raise EnvironmentError(
            "Lipsește ANTHROPIC_API_KEY (sau LLM_API_KEY cu cheie Anthropic) pentru Claude."
        )
    timeout = float(getattr(settings, "llm_buletin_audit_timeout_seconds", 90.0))
    client = anthropic.Anthropic(api_key=key, timeout=timeout)
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=temperature,
    )
    parts: list[str] = []
    for block in msg.content:
        if getattr(block, "text", None):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "".join(parts).strip()


def _openai_system_user(
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    from openai import OpenAI

    api_key = _openai_compatible_api_key()
    if not api_key:
        raise EnvironmentError("Lipsește cheie API (LLM_API_KEY sau OPENAI_API_KEY).")
    timeout = float(getattr(settings, "llm_buletin_audit_timeout_seconds", 90.0))
    base = (getattr(settings, "llm_base_url", None) or os.getenv("LLM_BASE_URL") or "").strip()
    kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base:
        kwargs["base_url"] = base.rstrip("/")
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
