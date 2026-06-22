"""Streamlit host for the introduction page + live support intake agent.

Layout:
  1. Renders web/introduction.html (hero, flow, features) for visual context.
     Its old canned "demo" chat is hidden — this page's REAL chat is below.
  2. A native, LLM-driven support intake assistant (see intake_agent.py) that:
       - greets and collects Full Name, Company, Project Name, Project Code
       - guides the user through their issue / STL-member flow
       - lets the user attach a screenshot or .txt/.log (uploaded to Google Drive)
       - saves the collected details as a text record to the SAME Drive folder,
         named "<name> and <project>.txt" (or "STL member request.txt" for STL).

Run locally:
    streamlit run streamlit_app/intro.py
Deploy:
    Point Streamlit Community Cloud at this file and add OpenRouter + Google Drive
    credentials under App -> Settings -> Secrets (see notes at the bottom).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# --- Make the repo root importable when run via `streamlit run` ---
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_secrets_into_env() -> None:
    """Copy credentials from st.secrets into the environment BEFORE core is
    imported, so core.config.settings picks them up on Streamlit Cloud.

    Supported keys (all optional):
      OPENROUTER_API_KEY, ROUTER_MODEL, ANSWER_MODEL,
      GDRIVE_UPLOAD_FOLDER_ID, GOOGLE_SERVICE_ACCOUNT_JSON,
      or a [gcp_service_account] TOML table (the key file's fields).
    """
    try:
        secrets = st.secrets
    except Exception:
        return

    for k in ("OPENROUTER_API_KEY", "ROUTER_MODEL", "ANSWER_MODEL", "GDRIVE_UPLOAD_FOLDER_ID"):
        if k in secrets and not os.environ.get(k):
            os.environ[k] = str(secrets[k])

    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        if "gcp_service_account" in secrets:
            os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = json.dumps(dict(secrets["gcp_service_account"]))
        elif "GOOGLE_SERVICE_ACCOUNT_JSON" in secrets:
            os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = str(secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])


_load_secrets_into_env()

from core import drive  # noqa: E402  (import after env is populated)
from core.config import settings  # noqa: E402

try:  # works whether the repo root or streamlit_app/ is on sys.path
    from streamlit_app import intake_agent  # noqa: E402
except ImportError:  # pragma: no cover
    import intake_agent  # type: ignore  # noqa: E402

st.set_page_config(page_title="kkAgentic Support — Introduction", layout="wide")

st.markdown(
    """
    <style>
      header[data-testid="stHeader"]{display:none}
      [data-testid="stAppViewContainer"]{background:#ffffff}
      footer{display:none}
      .block-container{padding:0 !important; max-width:1040px !important; margin:0 auto !important}
      [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] *{
        font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif}

      /* brand lockup — matches the marketing header */
      .kk-panel{max-width:680px;margin:0 auto;padding:0 16px;color:#1d1d1f}
      .kk-brand{display:flex;align-items:center;gap:12px;margin:30px 0 8px}
      .kk-logo{width:40px;height:40px;border-radius:11px;display:flex;align-items:center;
        justify-content:center;background:linear-gradient(135deg,#0071e3,#5e5ce6);color:#fff;
        font-weight:800;letter-spacing:.4px;font-size:15px;box-shadow:0 4px 14px rgba(0,113,227,.30)}
      .kk-title{font-size:22px;font-weight:700;letter-spacing:-0.02em;color:#1d1d1f}
      .kk-title .dim{color:#6e6e73;font-weight:500}
      .kk-sub{color:#6e6e73;font-size:14.5px;margin:0 0 6px}

      /* chat bubbles — clean Apple cards, centered column */
      [data-testid="stChatMessage"]{background:#ffffff;border:0.5px solid rgba(0,0,0,.10);
        border-radius:16px;padding:12px 16px;margin:8px auto;max-width:680px;
        box-shadow:0 1px 2px rgba(0,0,0,.05)}
      [data-testid="stChatMessage"] *{color:#1d1d1f}
      [data-testid="stChatInput"]{max-width:680px;margin:0 auto;background:#ffffff;
        border:0.5px solid rgba(0,0,0,.14);border-radius:14px}

      /* expander + form as light cards */
      [data-testid="stExpander"]{max-width:680px;margin:10px auto;border:0.5px solid rgba(0,0,0,.10);
        border-radius:14px;background:#ffffff;overflow:hidden}
      [data-testid="stExpander"] summary{font-weight:600;color:#1d1d1f}
      [data-testid="stForm"]{max-width:680px;margin:0 auto;border:0.5px solid rgba(0,0,0,.10);
        border-radius:14px;background:#ffffff}

      /* Apple-blue pill buttons */
      .stButton button, [data-testid="stFormSubmitButton"] button{border-radius:980px;font-weight:600}

      /* Apple-light file-uploader dropzone */
      [data-testid="stFileUploaderDropzone"]{background:#f5f5f7 !important;
        border:1px dashed #c7c7cc !important;border-radius:14px}
      [data-testid="stFileUploaderDropzone"] *{color:#1d1d1f !important}

      /* center captions/markdown text in the panel column */
      [data-testid="stCaptionContainer"]{max-width:680px;margin:0 auto}
    </style>
    """,
    unsafe_allow_html=True,
)

# 1) Marketing page (canned demo chat inside is hidden)
html = (Path(__file__).resolve().parent.parent / "web" / "introduction.html").read_text(encoding="utf-8")
components.html(html, height=2600, scrolling=True)

# ============================================================
# 2) Live support intake assistant (native, LLM-driven)
# ============================================================
ALLOWED = [e.strip().lstrip(".").lower() for e in settings.upload_allowed_ext.split(",") if e.strip()]
LLM_READY = bool(settings.openrouter_api_key)

# --- session state ---
if "intake_msgs" not in st.session_state:
    st.session_state.intake_msgs = [{"role": "assistant", "content": intake_agent.WELCOME}]
if "intake_fields" not in st.session_state:
    st.session_state.intake_fields = {}
if "record_saved_as" not in st.session_state:
    st.session_state.record_saved_as = None

st.markdown('<div class="kk-panel">', unsafe_allow_html=True)
st.markdown(
    '<div class="kk-brand"><span class="kk-logo">DL</span>'
    '<span class="kk-title">David Lau <span class="dim">· KK Agentic Support</span></span></div>'
    '<p class="kk-sub">Live support assistant — tell me about your request and I’ll guide you '
    "step by step, then save the details to our support drive.</p>",
    unsafe_allow_html=True,
)

if not LLM_READY:
    st.warning(
        "The assistant isn’t connected yet — add **OPENROUTER_API_KEY** in "
        "**App → Settings → Secrets** to enable live replies. You can still see the "
        "welcome flow below."
    )

# --- render chat history ---
for m in st.session_state.intake_msgs:
    with st.chat_message("user" if m["role"] == "user" else "assistant"):
        st.markdown(m["content"])

# --- chat input ---
prompt = st.chat_input("Type your reply…")
if prompt:
    st.session_state.intake_msgs.append({"role": "user", "content": prompt})
    if LLM_READY:
        try:
            answer = intake_agent.reply(st.session_state.intake_msgs)
        except Exception as e:
            answer = f"⚠️ I couldn’t reach the assistant just now: {e}"
        st.session_state.intake_msgs.append({"role": "assistant", "content": answer})
        # refresh the structured snapshot of collected fields
        try:
            st.session_state.intake_fields = intake_agent.extract_fields(st.session_state.intake_msgs)
        except Exception:
            pass
    else:
        st.session_state.intake_msgs.append(
            {"role": "assistant", "content": "_(Assistant offline — add OPENROUTER_API_KEY to go live.)_"}
        )
    st.rerun()

fields = st.session_state.intake_fields or {}
complete = intake_agent.is_complete(fields)

# --- collected details + save / upload controls ---
with st.expander("📋 Details collected so far", expanded=complete):
    if fields:
        if fields.get("is_stl"):
            st.markdown(
                f"- **SLT Academy member** ✓\n- **Full Name:** {fields.get('full_name') or '—'}\n"
                f"- **Project to build:** {fields.get('stl_project') or '—'}"
            )
        else:
            st.markdown(
                f"- **Full Name:** {fields.get('full_name') or '—'}\n"
                f"- **Company:** {fields.get('company') or '—'}\n"
                f"- **Project Name:** {fields.get('project_name') or '—'}\n"
                f"- **Project Code:** {fields.get('project_code') or '—'}\n"
                f"- **Email:** {fields.get('email') or '—'}\n"
                f"- **Issue:** {fields.get('issue') or '—'}"
            )
        st.caption(f"Record will be saved as: **{intake_agent.record_filename(fields)}**")
    else:
        st.caption("Nothing collected yet — start chatting above.")

    if st.session_state.record_saved_as:
        st.success(f"Saved to Google Drive as **{st.session_state.record_saved_as}** ✓")
    else:
        save_disabled = not (complete and drive.drive_enabled())
        if st.button("💾 Save my details to support", type="primary", disabled=save_disabled):
            when = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = intake_agent.record_filename(fields)
            text = intake_agent.build_record(fields, when)
            try:
                res = drive.upload_text_record(filename, text)
                st.session_state.record_saved_as = res.name
                st.rerun()
            except Exception as e:
                st.error(f"Couldn’t save the record: {e}")
        if not complete:
            st.caption("Provide the required details in the chat to enable saving.")
        elif not drive.drive_enabled():
            st.caption("⚠️ Google Drive not configured yet — add the service-account secrets to enable saving.")

# --- diagnostic / client-spec attachment ---
st.markdown("#### 📎 Attach a screenshot or log file")
if fields.get("is_stl"):
    st.caption("SLT Academy members: upload your client's spec file named exactly **client request.txt**.")
with st.form("attach_form", clear_on_submit=True):
    uploaded = st.file_uploader(
        "Screenshot or .txt/.log file",
        type=ALLOWED,
        accept_multiple_files=False,
        help=f"Allowed: {', '.join('.' + e for e in ALLOWED)} · max {settings.upload_max_mb} MB",
    )
    sent = st.form_submit_button("Upload attachment")
if sent:
    if uploaded is None:
        st.warning("Choose a file to attach.")
    elif len(uploaded.getvalue()) > settings.upload_max_mb * 1024 * 1024:
        st.error(f"File too large — the limit is {settings.upload_max_mb} MB.")
    elif not drive.drive_enabled():
        st.error("Google Drive isn’t configured yet, so the file wasn’t uploaded.")
    else:
        with st.spinner("Uploading to Google Drive…"):
            try:
                res = drive.upload_file(
                    uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream"
                )
                st.success(f"Uploaded ✓ — **{res.name}** saved to the support Google Drive.")
            except Exception as e:
                st.error(f"Upload failed: {e}")

st.caption(
    ("✅ Google Drive configured." if drive.drive_enabled() else "⚠️ Google Drive not configured yet.")
    + ("  ·  ✅ Assistant online." if LLM_READY else "  ·  ⚠️ Assistant offline (no OpenRouter key).")
)
st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------
#  STREAMLIT SECRETS  (App -> Settings -> Secrets)
#
#    OPENROUTER_API_KEY = "sk-or-..."
#    ANSWER_MODEL = "google/gemma-3-27b-it"
#    GDRIVE_UPLOAD_FOLDER_ID = "1n85znNakl_5A_kkuC52faUbPQIUmL0Xj"
#
#    [gcp_service_account]
#    type = "service_account"
#    project_id = "your-project"
#    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
#    client_email = "uploader@your-project.iam.gserviceaccount.com"
#    ...
#
#  Then share the Drive folder with that client_email (Editor).
# ------------------------------------------------------------------
