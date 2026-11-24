from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    google_service_account_file: str | None
    google_drive_folder_id: str | None
    azure_connection_string: str
    azure_container: str
    google_service_account_json: str | None = None


def load_settings(
    env_file: str | os.PathLike[str] | None = None,
    *,
    require_google_service_account: bool = True,
    require_drive_folder: bool = True,
) -> Settings:
    if env_file is None:
        load_dotenv()
    else:
        load_dotenv(str(env_file))

    values = {
        "GOOGLE_SERVICE_ACCOUNT_FILE": os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip(),
        "GOOGLE_SERVICE_ACCOUNT_JSON": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip(),
        "GOOGLE_DRIVE_FOLDER_ID": os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip(),
        "AZURE_STORAGE_CONNECTION_STRING": os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING", ""
        ).strip(),
        "AZURE_STORAGE_CONTAINER": os.getenv("AZURE_STORAGE_CONTAINER", "").strip(),
    }

    missing = [
        name
        for name in ("AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_CONTAINER")
        if not values[name]
    ]
    if require_drive_folder and not values["GOOGLE_DRIVE_FOLDER_ID"]:
        missing.append("GOOGLE_DRIVE_FOLDER_ID")
    has_service_account = bool(
        values["GOOGLE_SERVICE_ACCOUNT_FILE"] or values["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )
    if require_google_service_account and not has_service_account:
        missing.append("GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON")
    if missing:
        raise ValueError(
            "Missing required configuration: " + ", ".join(missing)
        )

    credential_path: Path | None = None
    service_account_json: str | None = None
    if require_google_service_account and values["GOOGLE_SERVICE_ACCOUNT_JSON"]:
        try:
            credential_info = json.loads(values["GOOGLE_SERVICE_ACCOUNT_JSON"])
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON must contain valid JSON"
            ) from exc
        if not isinstance(credential_info, dict):
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON must be a JSON object")
        service_account_json = values["GOOGLE_SERVICE_ACCOUNT_JSON"]
    elif require_google_service_account and values["GOOGLE_SERVICE_ACCOUNT_FILE"]:
        credential_path = Path(values["GOOGLE_SERVICE_ACCOUNT_FILE"]).expanduser()
        if not credential_path.is_file():
            raise FileNotFoundError(
                f"Google service-account file not found: {credential_path}"
            )

    return Settings(
        google_service_account_file=str(credential_path) if credential_path else None,
        google_drive_folder_id=values["GOOGLE_DRIVE_FOLDER_ID"] or None,
        azure_connection_string=values["AZURE_STORAGE_CONNECTION_STRING"],
        azure_container=values["AZURE_STORAGE_CONTAINER"],
        google_service_account_json=service_account_json,
    )
