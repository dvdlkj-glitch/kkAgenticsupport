"""Agent 1 — the ROUTER.

Reads the user's question and decides which project it belongs to.
Returns the project key, a confidence score (0..1) and a short reason.
Uses ROUTER_MODEL on OpenRouter.
"""
from __future__ import annotations

import json
import re

from .config import settings
from .openrouter import chat

SYSTEM = (
    "You are a support routing assistant. You are given a user's question and a list of "
    "projects, each with a key, name, description and keywords. Decide which single project "
    "the question is about. If a previous project was already in context and the new question "
    "is a follow-up, prefer that project. If nothing fits, use the key \"unknown\".\n\n"
    "Respond with ONLY a compact JSON object, no prose, in this exact shape:\n"
    '{"project_key": "<key-or-unknown>", "confidence": <0..1>, "reason": "<short>"}'
)


def _format_projects(projects: list[dict]) -> str:
    lines = []
    for p in projects:
        kw = ", ".join(p.get("keywords") or [])
        lines.append(
            f"- key: {p['key']}\n  name: {p['name']}\n  description: {p['description']}"
            + (f"\n  keywords: {kw}" if kw else "")
        )
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    # Grab the first {...} block and parse it leniently.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def route(question: str, projects: list[dict], context_project_key: str | None = None) -> dict:
    """Return {'project_key', 'confidence', 'reason'}.

    Includes a fast keyword pre-check so obvious matches don't even need the model.
    """
    if not projects:
        return {"project_key": "unknown", "confidence": 0.0, "reason": "no projects configured"}

    # --- cheap keyword shortcut ---
    q = question.lower()
    for p in projects:
        for kw in (p.get("keywords") or []):
            if kw and kw.lower() in q:
                return {
                    "project_key": p["key"],
                    "confidence": 0.9,
                    "reason": f"keyword match: {kw}",
                }

    ctx = ""
    if context_project_key:
        ctx = f"\nProject currently in context (prefer for follow-ups): {context_project_key}\n"

    user = (
        f"Projects:\n{_format_projects(projects)}\n{ctx}\n"
        f"User question: {question}\n\nReturn the JSON now."
    )

    raw = chat(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        model=settings.router_model,
        temperature=0.0,
        max_tokens=150,
    )

    data = _extract_json(raw)
    key = str(data.get("project_key", "unknown")).strip() or "unknown"
    valid_keys = {p["key"] for p in projects}
    if key not in valid_keys:
        key = "unknown"
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "project_key": key,
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(data.get("reason", ""))[:200],
    }
