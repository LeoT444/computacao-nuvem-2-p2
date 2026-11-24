from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from drive_blob_cli.app import copy_file
from drive_blob_cli.config import load_settings
from drive_blob_cli.service import AzureClient, DriveClient

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/config")
def public_config(response: Response) -> dict[str, str]:
    load_dotenv()
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_OAUTH_CLIENT_ID is not configured",
        )
    response.headers["Cache-Control"] = "no-store"
    return {
        "googleClientId": client_id,
        "defaultFolderId": os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip(),
    }


@app.post("/api")
async def api(request: Request, response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    load_dotenv()

    content_length = request.headers.get("content-length")
    if content_length is None:
        raise HTTPException(status_code=411, detail="Content-Length is required")
    try:
        size = int(content_length)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
    if size <= 0 or size > 16384:
        raise HTTPException(status_code=400, detail="Invalid request body size")

    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    action = body.get("action")
    if action not in ("list-drive", "list-azure", "copy-file"):
        raise HTTPException(status_code=400, detail="Unknown action")
    if action == "copy-file":
        file_id = body.get("fileId")
        if not isinstance(file_id, str) or not file_id.strip():
            raise HTTPException(status_code=400, detail="fileId is required")
    if action in ("list-drive", "copy-file"):
        access_token = body.get("googleAccessToken")
        if not isinstance(access_token, str) or not access_token.strip():
            raise HTTPException(
                status_code=401,
                detail="Connect a Google Drive account before listing or copying files",
            )
        folder_id = body.get("folderId")
        if folder_id is not None and not isinstance(folder_id, str):
            raise HTTPException(status_code=400, detail="folderId must be a string")
    else:
        access_token = None
        folder_id = None

    try:
        settings = load_settings(
            require_google_service_account=False,
            require_drive_folder=False,
        )
        if action == "list-drive":
            files = [
                {"id": item.id, "name": item.name}
                for item in DriveClient(
                    settings,
                    access_token=access_token,
                    folder_id=folder_id or settings.google_drive_folder_id,
                ).list_files()
            ]
            return {"files": files}
        if action == "list-azure":
            blobs = [{"name": item.name} for item in AzureClient(settings).list_blobs()]
            return {"blobs": blobs}

        drive = DriveClient(
            settings,
            access_token=access_token,
            folder_id=folder_id or settings.google_drive_folder_id,
        )
        source = drive.get_file(file_id)
        result = copy_file(drive, AzureClient(settings), source)
        return {
            "result": {
                "name": result.name,
                "success": result.success,
                "error": result.error,
            }
        }
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpError as exc:
        if exc.resp.status == 401:
            raise HTTPException(
                status_code=401,
                detail="Google access expired; reconnect your Google account",
            ) from exc
        if exc.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail="Google Drive denied access; check the folder and granted scope",
            ) from exc
        raise HTTPException(status_code=502, detail="Google Drive request failed") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
