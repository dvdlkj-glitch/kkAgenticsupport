"""FastAPI backend that the Apple-style web page calls.

Endpoints:
    GET  /health           -> simple liveness
    GET  /projects         -> list of active projects (for the web page intro)
    POST /chat             -> {question, session_id, project_key?} -> answer

Run:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core import db, drive, pipeline
from core.config import settings

app = FastAPI(title="kkAgentic Support API")

origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    question: str
    session_id: str = "web-anon"
    project_key: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/projects")
def projects() -> dict:
    try:
        rows = db.get_active_projects()
    except Exception as e:
        return {"projects": [], "error": str(e)}
    return {
        "projects": [
            {"key": p["key"], "name": p["name"], "description": p["description"]} for p in rows
        ]
    }


@app.post("/chat")
def chat(body: ChatIn) -> dict:
    result = pipeline.handle_question(
        body.question,
        channel="web",
        user_ref=body.session_id,
        context_project_key=body.project_key,
    )
    return result


@app.get("/upload-info")
def upload_info() -> dict:
    """Lets the web page show accurate limits/hints for the attach button."""
    return {
        "enabled": True,
        "drive": drive.drive_enabled(),
        "max_mb": settings.upload_max_mb,
        "allowed_ext": [e.strip() for e in settings.upload_allowed_ext.split(",") if e.strip()],
    }


@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    session_id: str = Form("web-anon"),
    note: str = Form(""),
) -> dict:
    """Receive a screenshot or issue log from the web chat and store it in Google Drive.

    The browser sends multipart form-data; credentials live only here on the server.
    """
    data = await file.read()

    max_bytes = settings.upload_max_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (max {settings.upload_max_mb} MB).")

    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed = [e.strip().lower() for e in settings.upload_allowed_ext.split(",") if e.strip()]
    if allowed and ext not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext or '?'}'. Allowed: {', '.join(allowed)}.",
        )

    try:
        res = drive.upload_file(
            file.filename or "upload", data, file.content_type or "application/octet-stream"
        )
    except Exception as e:  # surface a clean message instead of a 500 stack
        raise HTTPException(status_code=502, detail=f"Could not store the file: {e}")

    # Note: the internal Drive link/id is intentionally NOT returned to the public web page.
    return {"ok": True, "name": res.name, "where": res.where}
