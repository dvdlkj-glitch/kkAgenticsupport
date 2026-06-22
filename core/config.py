"""Central configuration. Reads from environment (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv optional at runtime
    pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # OpenRouter
    openrouter_api_key: str = _get("OPENROUTER_API_KEY")
    openrouter_base_url: str = _get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    router_model: str = _get("ROUTER_MODEL", "google/gemma-3-12b-it")
    answer_model: str = _get("ANSWER_MODEL", "google/gemma-3-27b-it")
    site_url: str = _get("OPENROUTER_SITE_URL")
    app_name: str = _get("OPENROUTER_APP_NAME", "kkAgentic Support")

    # Supabase
    supabase_url: str = _get("SUPABASE_URL")
    supabase_key: str = _get("SUPABASE_KEY")

    # Embeddings
    embedding_backend: str = _get("EMBEDDING_BACKEND", "local")
    embedding_model_local: str = _get(
        "EMBEDDING_MODEL_LOCAL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    embedding_model_openai: str = _get("EMBEDDING_MODEL_OPENAI", "text-embedding-3-small")
    embedding_dim: int = int(_get("EMBEDDING_DIM", "384") or "384")
    openai_api_key: str = _get("OPENAI_API_KEY")

    # Retrieval / routing
    top_k: int = int(_get("TOP_K", "5") or "5")
    router_min_confidence: float = float(_get("ROUTER_MIN_CONFIDENCE", "0.45") or "0.45")

    # Telegram
    telegram_bot_token: str = _get("TELEGRAM_BOT_TOKEN")

    # Web / API
    cors_allow_origins: str = _get("CORS_ALLOW_ORIGINS", "*")

    # Uploads -> Google Drive (screenshots / issue logs from the web chat)
    google_service_account_file: str = _get("GOOGLE_SERVICE_ACCOUNT_FILE")
    # Raw service-account JSON content (used on Streamlit Cloud where you can't
    # ship a key file — paste the JSON into st.secrets instead of a file path).
    google_service_account_json: str = _get("GOOGLE_SERVICE_ACCOUNT_JSON")
    gdrive_upload_folder_id: str = _get("GDRIVE_UPLOAD_FOLDER_ID")
    upload_local_dir: str = _get("UPLOAD_LOCAL_DIR", "uploads")
    upload_max_mb: int = int(_get("UPLOAD_MAX_MB", "10") or "10")
    upload_allowed_ext: str = _get(
        "UPLOAD_ALLOWED_EXT", ".png,.jpg,.jpeg,.gif,.webp,.txt,.log"
    )


settings = Settings()
