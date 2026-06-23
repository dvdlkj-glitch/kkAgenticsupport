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
    # Accessing st.secrets (membership tests included) raises
    # StreamlitSecretNotFoundError when no secrets.toml exists — e.g. running
    # locally. Every key here is optional, so wrap the whole body and bail out
    # quietly if secrets aren't configured.
    try:
        secrets = st.secrets

        for k in ("OPENROUTER_API_KEY", "ROUTER_MODEL", "ANSWER_MODEL", "GDRIVE_UPLOAD_FOLDER_ID"):
            if k in secrets and not os.environ.get(k):
                os.environ[k] = str(secrets[k])

        if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
            if "gcp_service_account" in secrets:
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = json.dumps(dict(secrets["gcp_service_account"]))
            elif "GOOGLE_SERVICE_ACCOUNT_JSON" in secrets:
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = str(secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    except Exception:
        return


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
      /* ===== kkAgentic — monochrome brushed-metal theme (matches the marketing hero) ===== */
      :root{
        --kk-ink:#16181c; --kk-ink-2:#2a2d33; --kk-muted:#5b616a; --kk-faint:#9298a0;
        --kk-hair:rgba(20,22,26,.12); --kk-hair-soft:rgba(20,22,26,.07);
        --kk-glass:rgba(255,255,255,.58); --kk-glass-2:rgba(255,255,255,.4);
        --kk-glass-brd:rgba(255,255,255,.78); --kk-steel:#3a3f47;
        --kk-shadow:0 22px 54px -32px rgba(18,20,24,.5);
      }
      header[data-testid="stHeader"]{display:none}
      footer{display:none}
      [data-testid="stAppViewContainer"]{
        background:
          radial-gradient(130% 90% at 12% -6%, #f4f5f6 0%, rgba(244,245,246,0) 55%),
          radial-gradient(120% 80% at 108% 14%, #cfd3d7 0%, rgba(207,211,215,0) 52%),
          radial-gradient(90% 70% at 50% 116%, #c9ced3 0%, rgba(201,206,211,0) 60%),
          linear-gradient(146deg, #e9ebed 0%, #d4d8db 38%, #e6e8ea 64%, #d0d4d8 100%);
        background-attachment:fixed;
        color:var(--kk-ink);
        font-family:"Inter",-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,sans-serif}
      .block-container{padding:0 !important; max-width:1120px !important; margin:0 auto !important}
      /* clean, app-like look: hide page + iframe scrollbars (wheel still scrolls) */
      ::-webkit-scrollbar{width:0 !important; height:0 !important; background:transparent}
      html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"]{
        scrollbar-width:none; -ms-overflow-style:none;}
      iframe{border:0 !important}
      /* never override icon webfonts (was breaking the chat avatar -> "smart_toy") */
      [data-testid="stIconMaterial"], span[class*="material-symbols"], .material-icons{
        font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important}

      /* base text + links */
      [data-testid="stMarkdownContainer"]{color:var(--kk-ink)}
      [data-testid="stAppViewContainer"] a{color:var(--kk-ink); text-decoration:underline;
        text-decoration-color:var(--kk-steel); text-underline-offset:2px}

      /* brand lockup — matches the marketing header */
      .kk-panel{max-width:720px;margin:0 auto;padding:0 16px;color:var(--kk-ink)}
      .kk-brand{display:flex;align-items:center;gap:12px;margin:34px 0 10px}
      .kk-logo{width:40px;height:40px;border-radius:11px;display:flex;align-items:center;
        justify-content:center;background:linear-gradient(150deg,#2c2f34,#0f1013);color:#eef0f2;
        font-weight:700;letter-spacing:-.02em;font-size:15px;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 8px 20px -10px rgba(0,0,0,.6)}
      .kk-title{font-size:21px;font-weight:600;letter-spacing:-0.02em;color:var(--kk-ink)}
      .kk-title .reg{font-size:.55em;vertical-align:super;color:var(--kk-faint)}
      .kk-title .dim{color:var(--kk-muted);font-weight:500}
      .kk-eyebrow{font-size:11px;font-weight:600;letter-spacing:.26em;text-transform:uppercase;
        color:var(--kk-faint);display:block;margin:0 0 6px}
      .kk-sub{color:var(--kk-muted);font-size:14.5px;line-height:1.6;margin:0 0 6px}

      /* chat bubbles — frosted glass cards, centered column */
      [data-testid="stChatMessage"]{background:var(--kk-glass);backdrop-filter:blur(16px) saturate(140%);
        -webkit-backdrop-filter:blur(16px) saturate(140%);border:1px solid var(--kk-glass-brd);
        border-radius:16px;padding:12px 16px;margin:8px auto;max-width:720px;box-shadow:var(--kk-shadow)}
      [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
      [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li{color:var(--kk-ink)}
      [data-testid="stChatMessage"] strong{color:#0e1013}
      [data-testid="stChatMessage"] code{background:rgba(20,22,26,.07);color:var(--kk-ink-2);
        border-radius:6px;padding:1px 5px}

      /* chat input — frosted field with steel focus ring */
      [data-testid="stChatInput"]{max-width:720px;margin:0 auto;background:var(--kk-glass);
        border:1px solid var(--kk-glass-brd);border-radius:14px;backdrop-filter:blur(10px)}
      [data-testid="stChatInput"]:focus-within{border-color:var(--kk-steel);
        box-shadow:0 0 0 3px rgba(58,63,71,.14)}
      [data-testid="stChatInput"] textarea{color:var(--kk-ink) !important}
      [data-testid="stChatInput"] textarea::placeholder{color:var(--kk-faint)}

      /* expander + form as frosted glass cards */
      [data-testid="stExpander"]{max-width:720px;margin:10px auto;border:1px solid var(--kk-glass-brd);
        border-radius:14px;background:var(--kk-glass);backdrop-filter:blur(16px) saturate(140%);
        -webkit-backdrop-filter:blur(16px) saturate(140%);overflow:hidden;box-shadow:var(--kk-shadow)}
      [data-testid="stExpander"] summary{font-weight:600;color:var(--kk-ink)}
      [data-testid="stExpander"] summary:hover{color:var(--kk-steel)}
      [data-testid="stExpander"] [data-testid="stMarkdownContainer"]{color:var(--kk-ink)}
      [data-testid="stForm"]{max-width:720px;margin:0 auto;border:1px solid var(--kk-glass-brd);
        border-radius:14px;background:var(--kk-glass);backdrop-filter:blur(16px) saturate(140%);
        -webkit-backdrop-filter:blur(16px) saturate(140%);box-shadow:var(--kk-shadow)}

      /* monochrome pill buttons */
      .stButton button, [data-testid="stFormSubmitButton"] button{border-radius:980px;font-weight:600;
        border:1px solid var(--kk-glass-brd);background:var(--kk-glass);color:var(--kk-ink);transition:.16s ease}
      .stButton button:hover, [data-testid="stFormSubmitButton"] button:hover{
        border-color:var(--kk-steel);background:rgba(255,255,255,.72);transform:translateY(-1px)}
      /* primary button (e.g. "💾 Save my details to support") — readable light
         frosted pill matching the file-upload button. Streamlit colours the inner
         label dark, so on the old black pill it was invisible; force it readable. */
      .stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"]{
        background:var(--kk-glass) !important;color:var(--kk-ink) !important;
        border:1px solid var(--kk-glass-brd) !important;box-shadow:var(--kk-shadow) !important}
      .stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
        background:rgba(255,255,255,.8) !important;border-color:var(--kk-steel) !important;transform:translateY(-1px)}
      .stButton button[kind="primary"] *, [data-testid="stFormSubmitButton"] button[kind="primary"] *{
        color:var(--kk-ink) !important}

      /* frosted file-uploader dropzone */
      [data-testid="stFileUploaderDropzone"]{background:var(--kk-glass-2) !important;
        border:1px dashed var(--kk-hair) !important;border-radius:14px}
      [data-testid="stFileUploaderDropzone"]:hover{border-color:var(--kk-steel) !important}
      [data-testid="stFileUploaderDropzone"] *{color:var(--kk-ink) !important}
      [data-testid="stFileUploaderDropzone"] small{color:var(--kk-muted) !important}
      /* the "Browse files / Upload" button inside the dropzone — readable frosted pill
         (was a black button with dark, invisible label until hover) */
      [data-testid="stFileUploaderDropzone"] button,
      [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]{
        background:var(--kk-glass) !important;border:1px solid var(--kk-glass-brd) !important;
        border-radius:980px !important;font-weight:600 !important;
        box-shadow:var(--kk-shadow) !important;transition:.16s ease}
      [data-testid="stFileUploaderDropzone"] button:hover,
      [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]:hover{
        background:rgba(255,255,255,.8) !important;border-color:var(--kk-steel) !important;
        transform:translateY(-1px)}
      [data-testid="stFileUploaderDropzone"] button,
      [data-testid="stFileUploaderDropzone"] button *{color:var(--kk-ink) !important}

      /* center captions/markdown text in the panel column */
      [data-testid="stCaptionContainer"]{max-width:720px;margin:0 auto;color:var(--kk-muted)}

      /* ---- guiding animations (subtle) ---- */
      @keyframes kkFade{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
      @keyframes kkGlow{0%,100%{box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 8px 20px -10px rgba(0,0,0,.6)}
                        50%{box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 12px 26px -10px rgba(0,0,0,.66)}}
      @keyframes kkBounce{0%,100%{transform:translateY(0)}50%{transform:translateY(4px)}}
      @keyframes kkPulse{0%,100%{opacity:.4;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)}}
      .kk-brand,.kk-sub{animation:kkFade .5s ease both}
      .kk-logo{animation:kkGlow 2.8s ease-in-out infinite}
      [data-testid="stChatMessage"]{animation:kkFade .45s ease both}
      .kk-hint{display:inline-flex;align-items:center;gap:9px;margin:10px 0 2px;padding:8px 15px;
        border-radius:980px;background:var(--kk-glass);color:var(--kk-ink-2);font-size:13px;font-weight:600;
        border:1px solid var(--kk-glass-brd);box-shadow:var(--kk-shadow);animation:kkFade .6s ease both}
      .kk-hint .dot{width:8px;height:8px;border-radius:50%;background:var(--kk-steel);
        box-shadow:0 0 9px 0 rgba(58,63,71,.5);animation:kkPulse 1.4s ease-in-out infinite}
      .kk-hint .arrow{display:inline-block;animation:kkBounce 1.4s ease-in-out infinite}

      /* ---- mobile phones (≤640px) ---- */
      @media (max-width:640px){
        .block-container{padding:0 14px !important}
        .kk-panel{padding:0; max-width:100%}
        .kk-brand{margin:18px 0 6px; gap:10px}
        .kk-logo{width:34px; height:34px; font-size:13px}
        .kk-title{font-size:18px}
        .kk-sub{font-size:13px}
        .kk-hint{font-size:12px; flex-wrap:wrap; gap:7px; padding:7px 13px}
        [data-testid="stChatMessage"], [data-testid="stChatInput"],
        [data-testid="stExpander"], [data-testid="stForm"],
        [data-testid="stCaptionContainer"]{max-width:100%}
        [data-testid="stChatMessage"]{padding:11px 13px}
        /* easy-to-tap full-width buttons */
        .stButton button, [data-testid="stFormSubmitButton"] button{width:100%}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# 1) Marketing page (canned demo chat inside is hidden)
html = (Path(__file__).resolve().parent.parent / "web" / "introduction.html").read_text(encoding="utf-8")
# Height tuned to the rebuilt marketing page so it renders inline (no inner scroll);
# the live intake assistant follows directly below.
components.html(html, height=4360, scrolling=True)

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
    '<span class="kk-eyebrow">Live support assistant</span>'
    '<div class="kk-brand"><span class="kk-logo">kk</span>'
    '<span class="kk-title">kkAgentic<span class="reg">®</span> Support '
    '<span class="dim">· David Lau</span></span></div>'
    '<p class="kk-sub">Tell me about your request and I’ll guide you step by step — '
    "one question at a time — then save the details to our support drive.</p>"
    '<div class="kk-hint"><span class="dot"></span>Start by typing your reply below'
    '<span class="arrow">↓</span></div>',
    unsafe_allow_html=True,
)

if not LLM_READY:
    st.warning(
        "The assistant isn’t connected yet — add **OPENROUTER_API_KEY** in "
        "**App → Settings → Secrets** to enable live replies. You can still see the "
        "welcome flow below."
    )

# --- render chat history ---
# Explicit emoji avatars so the bubble never falls back to Streamlit's
# Material-icon avatar (which can render the raw "smart_toy" ligature).
AVATARS = {"user": "🧑", "assistant": "💬"}
for m in st.session_state.intake_msgs:
    role = "user" if m["role"] == "user" else "assistant"
    with st.chat_message(role, avatar=AVATARS[role]):
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
