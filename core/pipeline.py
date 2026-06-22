"""Orchestration: question -> ROUTER (agent 1) -> ANSWER (agent 2) -> reply.

This is the single entry point used by every channel (web API, Telegram, Streamlit).
"""
from __future__ import annotations

from . import answer_agent, db, router_agent
from .config import settings


def handle_question(
    question: str,
    channel: str = "web",
    user_ref: str = "anon",
    context_project_key: str | None = None,
) -> dict:
    """Full pipeline.

    Returns a dict:
      {
        "project_key": str | None,
        "project_name": str | None,
        "confidence": float,
        "answer": str,
        "sources": [str],
        "needs_clarification": bool,
      }
    """
    question = (question or "").strip()
    if not question:
        return {
            "project_key": None,
            "project_name": None,
            "confidence": 0.0,
            "answer": "Please type a question and I'll route it to the right project agent.",
            "sources": [],
            "needs_clarification": True,
        }

    projects = db.get_active_projects()
    if not projects:
        return {
            "project_key": None,
            "project_name": None,
            "confidence": 0.0,
            "answer": "No projects are configured yet. Run the ingestion script to add one.",
            "sources": [],
            "needs_clarification": True,
        }

    # --- Agent 1: route ---
    decision = router_agent.route(question, projects, context_project_key)
    key = decision["project_key"]
    confidence = decision["confidence"]

    # Low confidence / unknown -> ask the user to pick instead of guessing.
    if key == "unknown" or confidence < settings.router_min_confidence:
        names = ", ".join(p["name"] for p in projects)
        msg = (
            "I'm not sure which project this is about. "
            f"Could you tell me which one you mean? Available: {names}."
        )
        db.log_conversation(channel, user_ref, question, None, None, confidence, msg)
        return {
            "project_key": None,
            "project_name": None,
            "confidence": confidence,
            "answer": msg,
            "sources": [],
            "needs_clarification": True,
        }

    project = next((p for p in projects if p["key"] == key), None)

    # --- Agent 2: answer (RAG) ---
    result = answer_agent.answer(question, project)

    db.log_conversation(
        channel, user_ref, question, project["id"], project["key"], confidence, result["answer"]
    )

    return {
        "project_key": project["key"],
        "project_name": project["name"],
        "confidence": confidence,
        "answer": result["answer"],
        "sources": result["sources"],
        "needs_clarification": False,
    }
