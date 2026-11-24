import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response


dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda *args, **kwargs: False
sys.modules["dotenv"] = dotenv

azure = types.ModuleType("azure")
azure_core = types.ModuleType("azure.core")
azure_core_exceptions = types.ModuleType("azure.core.exceptions")
azure_storage = types.ModuleType("azure.storage")
azure_blob = types.ModuleType("azure.storage.blob")

class ResourceExistsError(Exception):
    pass

azure_core_exceptions.ResourceExistsError = ResourceExistsError

class ContainerClient:
    pass

sys.modules["azure.core"] = azure_core
sys.modules["azure.core.exceptions"] = azure_core_exceptions
azure_blob.ContainerClient = ContainerClient
sys.modules["azure"] = azure
sys.modules["azure.storage"] = azure_storage
sys.modules["azure.storage.blob"] = azure_blob

google = types.ModuleType("google")
google_oauth = types.ModuleType("google.oauth2")
google_auth = types.ModuleType("google.oauth2.service_account")

class Credentials:
    @staticmethod
    def from_service_account_file(*args, **kwargs):
        return object()

google_auth.Credentials = Credentials
google_oauth.service_account = google_auth
googleapiclient = types.ModuleType("googleapiclient")
googleapiclient.discovery = types.ModuleType("googleapiclient.discovery")
googleapiclient.discovery.build = lambda *args, **kwargs: None
googleapiclient.errors = types.ModuleType("googleapiclient.errors")

class HttpError(Exception):
    pass

googleapiclient.errors.HttpError = HttpError
sys.modules["google"] = google
sys.modules["google.oauth2"] = google_oauth
sys.modules["google.oauth2.service_account"] = google_auth
sys.modules["googleapiclient"] = googleapiclient
sys.modules["googleapiclient.discovery"] = googleapiclient.discovery
sys.modules["googleapiclient.errors"] = googleapiclient.errors

from drive_blob_cli.app import copy_files
from drive_blob_cli.service import CopyResult, DriveFile
import app as web_app


class FakeDrive:
    def __init__(self):
        self.files = [
            DriveFile(id="1", name="report.txt"),
            DriveFile(id="2", name="broken.txt"),
        ]

    def list_files(self):
        return iter(self.files)

    def download(self, file_id):
        if file_id == "2":
            raise RuntimeError("download failed")
        return b"report contents"


class FakeAzure:
    def __init__(self):
        self.uploads = []

    def upload(self, name, content):
        self.uploads.append((name, content))


class CopyTests(unittest.TestCase):
    def test_copy_reports_success_and_error_per_file(self):
        drive = FakeDrive()
        azure = FakeAzure()

        results = list(copy_files(drive, azure))

        self.assertEqual(
            results,
            [
                CopyResult(name="report.txt", success=True),
                CopyResult(
                    name="broken.txt",
                    success=False,
                    error="download failed",
                ),
            ],
        )
        self.assertEqual(azure.uploads, [("report.txt", b"report contents")])

    def test_api_lists_azure_without_app_token(self):
        body = json.dumps({"action": "list-azure"}).encode()
        request_sent = False

        async def receive():
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api",
                "raw_path": b"/api",
                "query_string": b"",
                "headers": [
                    (b"content-length", str(len(body)).encode()),
                    (b"content-type", b"application/json"),
                ],
                "client": ("test", 123),
                "server": ("test", 80),
            },
            receive,
        )
        response = Response()

        class Azure:
            def list_blobs(self):
                return []

        with patch.object(web_app, "load_dotenv"), patch.object(
            web_app, "load_settings", return_value=object()
        ), patch.object(web_app, "AzureClient", return_value=Azure()):
            result = asyncio.run(web_app.api(request, response))

        self.assertEqual(result, {"blobs": []})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
