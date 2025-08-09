from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
from ..config import SECRETS_DIR

# Lazy import Google libs to keep startup light

def _build_service():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except Exception as exc:
        raise RuntimeError("Google Drive libraries not available: " + str(exc))

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    token_path = SECRETS_DIR / "token.json"
    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    else:
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            cred_path = SECRETS_DIR / "credentials.json"
            if not cred_path.exists():
                raise RuntimeError("Missing Google OAuth credentials at secrets/credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
            creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

    service = build("drive", "v3", credentials=creds)
    return service


def upload_file(pdf_path: Path, filename: Optional[str] = None) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload  # type: ignore

    service = _build_service()
    metadata = {"name": filename or pdf_path.name}
    media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
    file = service.files().create(body=metadata, media_body=media, fields="id, webViewLink").execute()
    file_id = file.get("id")
    # Set anyone with the link can view
    service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()
    # Re-fetch to get shareable link
    file = service.files().get(fileId=file_id, fields="id, webViewLink").execute()
    return file["id"], file["webViewLink"]