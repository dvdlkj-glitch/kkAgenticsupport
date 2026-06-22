"""Supabase access: projects, vector search, conversation logging."""
from __future__ import annotations

from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def client():
    from supabase import create_client

    if not (settings.supabase_url and settings.supabase_key):
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY are not set. Add them to your .env.")
    return create_client(settings.supabase_url, settings.supabase_key)


def get_active_projects() -> list[dict]:
    """All active projects (used by the router and the web/console UIs)."""
    res = (
        client()
        .table("projects")
        .select("id,key,name,description,keywords,persona")
        .eq("is_active", True)
        .execute()
    )
    return res.data or []


def get_project_by_key(key: str) -> dict | None:
    res = client().table("projects").select("*").eq("key", key).limit(1).execute()
    return (res.data or [None])[0]


def upsert_project(
    key: str, name: str, description: str, keywords: list[str], persona: str = ""
) -> dict:
    payload = {
        "key": key,
        "name": name,
        "description": description,
        "keywords": keywords,
        "persona": persona,
        "is_active": True,
    }
    res = client().table("projects").upsert(payload, on_conflict="key").execute()
    return res.data[0]


def delete_project_documents(project_id: str) -> None:
    client().table("documents").delete().eq("project_id", project_id).execute()


def insert_document_chunks(rows: list[dict]) -> None:
    if rows:
        client().table("documents").insert(rows).execute()


def match_documents(project_id: str, query_embedding: list[float], top_k: int) -> list[dict]:
    """Vector similarity search via the match_documents RPC."""
    res = client().rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "p_project_id": project_id,
            "match_count": top_k,
        },
    ).execute()
    return res.data or []


def log_conversation(
    channel: str,
    user_ref: str,
    question: str,
    routed_project_id: str | None,
    routed_project_key: str | None,
    confidence: float | None,
    answer: str,
) -> None:
    try:
        client().table("conversations").insert(
            {
                "channel": channel,
                "user_ref": user_ref,
                "question": question,
                "routed_project_id": routed_project_id,
                "routed_project_key": routed_project_key,
                "confidence": confidence,
                "answer": answer,
            }
        ).execute()
    except Exception:
        # Logging must never break the user-facing answer.
        pass
