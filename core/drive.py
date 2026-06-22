"""Store user-submitted files (screenshots, issue logs) in a dedicated Google Drive folder.

Server-side only. The web page never sees Google credentials — it POSTs the file to the
FastAPI ``/upload`` endpoint, which calls :func:`upload_file` here.

Auth: a Google **service account** JSON key (``GOOGLE_SERVICE_ACCOUNT_FILE``) that has access
to the target folder (``GDRIVE_UPLOAD_FOLDER_ID``). Share the folder with the service
account's ``client_email`` (Editor), or put the folder on a Shared Drive.

If Drive isn't configured, files fall back to a local ``./uploads`` directory so the feature
still works in development.
"""
from __future__ import annotations

import io
import os
import time
from dataclasses import dataclass

from .config import settings


@dataclass
class UploadResult:
    name: str
    where: str          # "drive" | "local"
    id: str | None = None
    link: str | None = None      # internal Drive link (not exposed to end users)
    path: str | None = None


_service = None


def drive_enabled() -> bool:
    has_creds = bool(settings.google_service_account_file or settings.google_service_account_json)
    return bool(has_creds and settings.gdrive_upload_folder_id)


def _drive_service():
    global _service
    if _service is not None:
        return _service
    import json as _json

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.file"]
    if settings.google_service_account_json:
        # Credentials supplied as raw JSON (e.g. from Streamlit secrets).
        info = _json.loads(settings.google_service_account_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    else:
        # Credentials supplied as a path to a downloaded key file.
        creds = service_account.Credentials.from_service_account_file(
            settings.google_service_account_file, scopes=scopes
        )
    _service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _service


def _safe_name(name: str) -> str:
    name = os.path.basename(name or "upload")
    cleaned = "".join(c for c in name if c.isalnum() or c in "-_. ()").strip()
    return cleaned or "upload"


def upload_file(
    filename: str, data: bytes, mimetype: str, prefix_timestamp: bool = True
) -> UploadResult:
    """Persist *data* in Drive (if configured) else locally.

    By default the stored name is timestamp-prefixed to avoid collisions
    (good for screenshots/logs). Pass ``prefix_timestamp=False`` to keep the
    exact filename — used for intake records like ``STL member request.txt``.
    Google Drive allows multiple files with the same name (keyed by id), so
    exact-name records won't overwrite each other.
    """
    safe = _safe_name(filename)
    stamped = f"{time.strftime('%Y%m%d-%H%M%S')}_{safe}" if prefix_timestamp else safe

    if drive_enabled():
        from googleapiclient.http import MediaIoBaseUpload

        service = _drive_service()
        meta = {"name": stamped, "parents": [settings.gdrive_upload_folder_id]}
        media = MediaIoBaseUpload(
            io.BytesIO(data), mimetype=mimetype or "application/octet-stream", resumable=False
        )
        created = (
            service.files()
            .create(body=meta, media_body=media, fields="id, name, webViewLink", supportsAllDrives=True)
            .execute()
        )
        return UploadResult(
            name=created.get("name", stamped), where="drive",
            id=created.get("id"), link=created.get("webViewLink"),
        )

    # ---- local fallback (development) ----
    folder = settings.upload_local_dir or "uploads"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, stamped)
    with open(path, "wb") as fh:
        fh.write(data)
    return UploadResult(name=stamped, where="local", path=os.path.abspath(path))


def upload_text_record(filename: str, text: str) -> UploadResult:
    """Upload a UTF-8 text record (intake details) under its EXACT filename.

    e.g. ``"Jane Doe and Billing Portal.txt"`` or ``"STL member request.txt"``.
    """
    return upload_file(
        filename, text.encode("utf-8"), "text/plain", prefix_timestamp=False
    )
