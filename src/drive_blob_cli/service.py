from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import ContainerClient
from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import Settings


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str


@dataclass(frozen=True)
class BlobItem:
    name: str


@dataclass(frozen=True)
class CopyResult:
    name: str
    success: bool
    error: str | None = None


class DriveClient:
    def __init__(
        self,
        settings: Settings,
        access_token: str | None = None,
        folder_id: str | None = None,
    ) -> None:
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        self._folder_id = folder_id or settings.google_drive_folder_id
        if not self._folder_id:
            raise ValueError("Google Drive folder ID is not configured")

        service_account_json = getattr(settings, "google_service_account_json", None)
        if access_token:
            from google.oauth2.credentials import Credentials

            credentials = Credentials(token=access_token, scopes=scopes)
        elif service_account_json:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json),
                scopes=scopes,
            )
        else:
            if not settings.google_service_account_file:
                raise ValueError("Google service-account credentials are not configured")
            credentials = service_account.Credentials.from_service_account_file(
                settings.google_service_account_file,
                scopes=scopes,
            )
        self._service = build("drive", "v3", credentials=credentials)

    def get_file(self, file_id: str) -> DriveFile:
        item = (
            self._service.files()
            .get(fileId=file_id, fields="id,name,parents,trashed")
            .execute()
        )
        if item.get("trashed") or self._folder_id not in item.get("parents", []):
            raise ValueError("File is not in the configured Google Drive folder")
        return DriveFile(id=item["id"], name=item["name"])

    def list_files(self) -> Iterable[DriveFile]:
        page_token = None
        while True:
            response = (
                self._service.files()
                .list(
                    q=f"'{self._folder_id}' in parents and trashed=false",
                    spaces="drive",
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                    pageSize=100,
                )
                .execute()
            )
            for item in response.get("files", []):
                yield DriveFile(id=item["id"], name=item["name"])
            page_token = response.get("nextPageToken")
            if not page_token:
                return

    def download(self, file_id: str) -> bytes:
        return self._service.files().get_media(fileId=file_id).execute()


class AzureClient:
    def __init__(self, settings: Settings) -> None:
        self._container = ContainerClient.from_connection_string(
            settings.azure_connection_string,
            settings.azure_container,
        )
        try:
            self._container.create_container()
        except ResourceExistsError:
            pass

    def list_blobs(self) -> Iterable[BlobItem]:
        for blob in self._container.list_blobs():
            yield BlobItem(name=blob.name)

    def upload(self, name: str, content: bytes) -> None:
        self._container.upload_blob(name=name, data=content, overwrite=True)
