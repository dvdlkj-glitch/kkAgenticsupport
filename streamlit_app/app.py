"""Streamlit support console for kkAgentic Support.

Run:
    streamlit run streamlit_app/app.py

Deploy free on Streamlit Community Cloud; set the same env vars as .env in
the app's Secrets.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when run via `streamlit run`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from core import db, pipeline  # noqa: E402

st.set_page_config(page_title="kkAgentic Support", page_icon="💬", layout="centered")

# --- light Apple-ish styling ---
st.markdown(
    """
    <style>
      .stApp { background: #f5f5f7; }
      h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
                   letter-spacing: -0.02em; }
      .pill { display:inline-block; padding:2px 10px; border-radius:999px;
              background:#e8e8ed; color:#1d1d1f; font-size:12px; margin-right:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("kkAgentic Support")
st.caption("Two AI agents — one routes your question, one answers it from that project's docs.")

# Sidebar: project list + context
with st.sidebar:
    st.subheader("Projects")
    try:
        projects = db.get_active_projects()
        for p in projects:
            st.markdown(f"**{p['name']}**  \n{p['description']}")
    except Exception as e:
        st.error(f"Can't load projects: {e}")
    if st.button("Reset conversation"):
        st.session_state.clear()
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "project_key" not in st.session_state:
    st.session_state.project_key = None

# Replay history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask a support question…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Routing and answering…"):
            try:
                result = pipeline.handle_question(
                    prompt,
                    channel="streamlit",
                    user_ref="streamlit-session",
                    context_project_key=st.session_state.project_key,
                )
            except Exception as e:
                result = {
                    "answer": f"⚠️ Error: {e}",
                    "project_key": None,
                    "project_name": None,
                    "confidence": 0.0,
                    "sources": [],
                    "needs_clarification": True,
                }

        if result["project_key"]:
            st.session_state.project_key = result["project_key"]

        header = ""
        if result["project_name"] and not result["needs_clarification"]:
            header = (
                f"<span class='pill'>{result['project_name']}</span>"
                f"<span class='pill'>confidence {result['confidence']:.0%}</span>\n\n"
            )
        st.markdown(header + result["answer"], unsafe_allow_html=True)
        if result["sources"]:
            st.caption("Sources: " + ", ".join(result["sources"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": header + result["answer"]}
    )
