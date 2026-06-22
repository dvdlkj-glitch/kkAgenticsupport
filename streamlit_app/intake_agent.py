"""LLM-driven support intake agent (used by the introduction page chat).

Drives the conversation defined in ``customer_support_script.txt``:
  * greet and collect Full Name, Company, Project Name, Project Code
  * guide the user through their issue, invite a screenshot/log upload,
    gate uploads behind a corporate email, give the resolution-timeline notice
  * detect SLT Academy Trainers/members and switch to the SLT Academy branch
    (Full Name + the project to build, plus a 'client request.txt' upload)

It talks to OpenRouter through ``core.openrouter.chat`` (the shared LLM client),
using ANSWER_MODEL. A second, deterministic extraction call keeps a structured
view of what's been collected so the page knows when a record can be saved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.config import settings
from core.openrouter import chat

# The human-authored script is the single source of truth for the wording/flow.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "customer_support_script.txt"


def load_script() -> str:
    try:
        return _SCRIPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


# The exact Segment A welcome, shown immediately (no API call needed on load).
WELCOME = (
    "👋 Welcome to **kkAgentic Support Services**. To route your inquiry to the "
    "correct project team and database, please start by telling me:\n\n"
    "1. Your **Full Name**\n"
    "2. Your **Company Name**\n"
    "3. The **Project Name**\n"
    "4. Your **Designated Project Code**\n\n"
    "If you're an **SLT Academy Trainer or member**, just say so — I'll switch to the "
    "SLT Academy request flow instead.\n\n"
    "Type your reply below to begin."
)


def _system_prompt() -> str:
    return (
        "You are the kkAgentic Support intake assistant, embedded in a chat window on "
        "the support website. Greet users warmly and guide them step by step, asking "
        "for ONE or two things at a time — never dump the whole questionnaire at once "
        "after the first welcome.\n\n"
        "Follow this company script faithfully (wording and stage order):\n"
        "----- SUPPORT SCRIPT -----\n"
        f"{load_script()}\n"
        "----- END SCRIPT -----\n\n"
        "Operating rules:\n"
        "1. Standard users: collect Full Name, Company Name, Project Name, and Project "
        "Code before deep diagnostics. Then ask them to describe the issue (error codes, "
        "behaviors, steps). Invite them to attach a screenshot or .txt/.log file using "
        "the attachment panel shown below the chat, and ask for their corporate email "
        "before they upload. After an upload, give the resolution-timeline notice.\n"
        "2. SLT Academy Trainers/members: if the user says they are from SLT Academy / an "
        "SLT Academy Trainer or member, switch to the SLT Academy branch — collect their "
        "Full Name and the Name of the project they want to build for their client, and "
        "ask them to upload the client's "
        "requirement specification file named exactly 'client request.txt' via the "
        "attachment panel.\n"
        "3. When you have the required details, tell the user their details are ready to "
        "be saved and ask them to click the 'Save my details to support' button shown "
        "below the chat.\n"
        "4. Be concise, friendly and professional. Do not invent ticket numbers, "
        "timelines beyond the script, or facts. Never ask for passwords or payment card "
        "numbers."
    )


def reply(history: list[dict]) -> str:
    """Generate the assistant's next message given prior chat turns."""
    messages = [{"role": "system", "content": _system_prompt()}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    return chat(messages, model=settings.answer_model, temperature=0.4, max_tokens=450)


_EXTRACT_SYSTEM = (
    "You extract structured intake fields from a support conversation. "
    "Return ONLY a compact JSON object, no prose, in exactly this shape:\n"
    '{"full_name": "", "company": "", "project_name": "", "project_code": "", '
    '"email": "", "issue": "", "is_stl": false, "stl_project": ""}\n'
    "Rules: use an empty string for anything not yet provided. Set is_stl to true ONLY "
    "if the user states they are from SLT Academy / an SLT Academy Trainer or member. "
    "For SLT Academy users, stl_project is the project they want to build for their "
    "client. Do not guess."
)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def extract_fields(history: list[dict]) -> dict:
    """Best-effort structured snapshot of what the user has provided so far."""
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    raw = chat(
        [
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {"role": "user", "content": convo + "\n\nReturn the JSON now."},
        ],
        model=settings.answer_model,
        temperature=0.0,
        max_tokens=300,
    )
    data = _extract_json(raw)
    # normalize
    out = {
        "full_name": str(data.get("full_name", "") or "").strip(),
        "company": str(data.get("company", "") or "").strip(),
        "project_name": str(data.get("project_name", "") or "").strip(),
        "project_code": str(data.get("project_code", "") or "").strip(),
        "email": str(data.get("email", "") or "").strip(),
        "issue": str(data.get("issue", "") or "").strip(),
        "is_stl": bool(data.get("is_stl", False)),
        "stl_project": str(data.get("stl_project", "") or "").strip(),
    }
    return out


def is_complete(fields: dict) -> bool:
    """Are the minimum fields present to save a record?"""
    if fields.get("is_stl"):
        return bool(fields.get("full_name") and fields.get("stl_project"))
    return bool(
        fields.get("full_name")
        and fields.get("company")
        and fields.get("project_name")
        and fields.get("project_code")
    )


def _safe_component(value: str, fallback: str) -> str:
    value = (value or "").strip() or fallback
    # keep it filename-friendly (drive._safe_name also sanitizes)
    return re.sub(r'[\\/:*?"<>|]+', "-", value).strip() or fallback


def record_filename(fields: dict) -> str:
    """SLT Academy -> 'SLT Academy member request.txt'; otherwise '<name> and <project>.txt'."""
    if fields.get("is_stl"):
        return "SLT Academy member request.txt"
    name = _safe_component(fields.get("full_name"), "user")
    project = _safe_component(fields.get("project_name"), "project")
    return f"{name} and {project}.txt"


def build_record(fields: dict, when: str) -> str:
    """Human-readable intake record saved to Google Drive."""
    lines = [
        "kkAgentic Support — Intake Record",
        "=" * 40,
        f"Captured: {when}",
        f"Channel: web (introduction page)",
        "",
    ]
    if fields.get("is_stl"):
        lines += [
            "Request type: SLT ACADEMY TRAINER / MEMBER",
            f"Full Name: {fields.get('full_name', '')}",
            f"Project to build for client: {fields.get('stl_project', '')}",
            "Client requirement file expected: client request.txt (uploaded separately)",
        ]
    else:
        lines += [
            "Request type: Standard support",
            f"Full Name: {fields.get('full_name', '')}",
            f"Company Name: {fields.get('company', '')}",
            f"Project Name: {fields.get('project_name', '')}",
            f"Project Code: {fields.get('project_code', '')}",
            f"Corporate Email: {fields.get('email', '')}",
            "",
            "Reported issue:",
            fields.get("issue", "") or "(not provided)",
        ]
    lines += ["", "=" * 40]
    return "\n".join(lines)
