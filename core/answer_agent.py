"""Agent 2 — the per-project ANSWER agent (RAG).

Retrieves the most relevant doc/FAQ chunks for the chosen project from Supabase,
then asks ANSWER_MODEL on OpenRouter to answer using ONLY that context.
"""
from __future__ import annotations

from . import db
from .config import settings
from .embeddings import embed_one
from .openrouter import chat

SYSTEM_TEMPLATE = (
    "You are the dedicated support agent for the project \"{project_name}\".\n"
    "{persona}\n"
    "Answer the user's question using ONLY the context provided below. "
    "Be concise, friendly and specific. Use steps when helpful.\n"
    "If the answer is not in the context, say you don't have that information yet and "
    "offer to escalate to a human, rather than inventing an answer.\n\n"
    "----- CONTEXT -----\n{context}\n----- END CONTEXT -----"
)


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        title = c.get("title") or c.get("source") or f"snippet {i}"
        parts.append(f"[{i}] ({title})\n{c.get('content', '').strip()}")
    return "\n\n".join(parts) if parts else "(no documents found for this project)"


def answer(question: str, project: dict, top_k: int | None = None) -> dict:
    """Return {'answer', 'sources', 'used_chunks'} for one project."""
    top_k = top_k or settings.top_k
    query_vec = embed_one(question)
    chunks = db.match_documents(project["id"], query_vec, top_k)

    system = SYSTEM_TEMPLATE.format(
        project_name=project["name"],
        persona=project.get("persona") or "",
        context=_build_context(chunks),
    )

    reply = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        model=settings.answer_model,
        temperature=0.2,
        max_tokens=800,
    )

    sources = []
    seen = set()
    for c in chunks:
        s = c.get("source") or c.get("title")
        if s and s not in seen:
            seen.add(s)
            sources.append(s)

    return {"answer": reply, "sources": sources, "used_chunks": len(chunks)}
