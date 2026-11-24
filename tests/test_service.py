import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch


azure = types.ModuleType("azure")
azure_core = types.ModuleType("azure.core")
azure_core_exceptions = types.ModuleType("azure.core.exceptions")
azure_storage = types.ModuleType("azure.storage")
azure_blob = types.ModuleType("azure.storage.blob")

class ResourceExistsErrorStub(Exception):
    pass

azure_core_exceptions.ResourceExistsError = ResourceExistsErrorStub

class ContainerClient:
    @staticmethod
    def from_connection_string(connection, container):
        return None

sys.modules["azure.core"] = azure_core
sys.modules["azure.core.exceptions"] = azure_core_exceptions
azure_blob.ContainerClient = ContainerClient
sys.modules["azure"] = azure
sys.modules["azure.storage"] = azure_storage
sys.modules["azure.storage.blob"] = azure_blob

google = types.ModuleType("google")
google_oauth = types.ModuleType("google.oauth2")
google_auth = types.ModuleType("google.oauth2.service_account")
google_credentials = types.ModuleType("google.oauth2.credentials")

class Credentials:
    @staticmethod
    def from_service_account_file(*args, **kwargs):
        return object()

google_auth.Credentials = Credentials
class UserCredentials:
    def __init__(self, token, scopes):
        self.token = token
        self.scopes = scopes

google_credentials.Credentials = UserCredentials
google_oauth.service_account = google_auth
google_oauth.credentials = google_credentials
googleapiclient = types.ModuleType("googleapiclient")
googleapiclient.discovery = types.ModuleType("googleapiclient.discovery")
googleapiclient.discovery.build = lambda *args, **kwargs: None
sys.modules["google"] = google
sys.modules["google.oauth2"] = google_oauth
sys.modules["google.oauth2.service_account"] = google_auth
sys.modules["google.oauth2.credentials"] = google_credentials
sys.modules["googleapiclient"] = googleapiclient
sys.modules["googleapiclient.discovery"] = googleapiclient.discovery

from drive_blob_cli.service import (
    AzureClient,
    DriveClient,
    DriveFile,
    ResourceExistsError,
)


class ServiceTests(unittest.TestCase):
    def test_drive_user_oauth_uses_selected_folder(self):
        service = SimpleNamespace(files=lambda: None)
        settings = SimpleNamespace(
            google_service_account_file=None,
            google_drive_folder_id=None,
        )

        with patch("drive_blob_cli.service.build", return_value=service) as build:
            client = DriveClient(
                settings,
                access_token="user-access-token",
                folder_id="selected-folder",
            )

        credentials = build.call_args.kwargs["credentials"]
        self.assertEqual(credentials.token, "user-access-token")
        self.assertEqual(client._folder_id, "selected-folder")

    def test_drive_file_must_belong_to_selected_folder(self):
        class Request:
            def execute(self):
                return {
                    "id": "file-id",
                    "name": "file.txt",
                    "parents": ["another-folder"],
                    "trashed": False,
                }

        class Files:
            def get(self, **kwargs):
                return Request()

        service = SimpleNamespace(files=lambda: Files())
        settings = SimpleNamespace(
            google_service_account_file=None,
            google_drive_folder_id=None,
        )
        with patch("drive_blob_cli.service.build", return_value=service):
            client = DriveClient(settings, access_token="user-token", folder_id="folder")

        with self.assertRaisesRegex(ValueError, "not in the configured"):
            client.get_file("file-id")

    def test_drive_page_listing(self):
        call_count = 0

        class Request:
            def execute(self):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {
                        "files": [{"id": "1", "name": "a.txt"}],
                        "nextPageToken": "next",
                    }
                return {"files": [{"id": "2", "name": "b.txt"}]}

        class Files:
            def list(self, **kwargs):
                return Request()

        service = SimpleNamespace(files=lambda: Files())
        settings = SimpleNamespace(
            google_service_account_file="credentials.json",
            google_drive_folder_id="folder",
        )

        with patch(
            "drive_blob_cli.service.service_account.Credentials.from_service_account_file",
            return_value=object(),
        ), patch("drive_blob_cli.service.build", return_value=service):
            client = DriveClient(settings)
            self.assertEqual(
                list(client.list_files()),
                [DriveFile(id="1", name="a.txt"), DriveFile(id="2", name="b.txt")],
            )

    def test_azure_listing(self):
        class Container:
            def create_container(self):
                pass

            def list_blobs(self):
                return [
                    SimpleNamespace(name="a.txt"),
                    SimpleNamespace(name="b.txt"),
                ]

        class ContainerClientStub:
            @staticmethod
            def from_connection_string(connection, container):
                return Container()

        with patch("drive_blob_cli.service.ContainerClient", ContainerClientStub):
            settings = SimpleNamespace(
                azure_connection_string="connection",
                azure_container="container",
            )
            names = [item.name for item in AzureClient(settings).list_blobs()]

        self.assertEqual(names, ["a.txt", "b.txt"])

    def test_azure_client_creates_missing_container(self):
        calls = []
        container = SimpleNamespace(create_container=lambda: calls.append("created"))
        client = type(
            "ContainerClientStub",
            (),
            {"from_connection_string": staticmethod(lambda *args: container)},
        )

        with patch("drive_blob_cli.service.ContainerClient", client):
            AzureClient(
                SimpleNamespace(
                    azure_connection_string="connection",
                    azure_container="container",
                )
            )

        self.assertEqual(calls, ["created"])

    def test_azure_client_ignores_existing_container(self):
        def create_container():
            raise ResourceExistsError()

        container = SimpleNamespace(create_container=create_container)
        client = type(
            "ContainerClientStub",
            (),
            {"from_connection_string": staticmethod(lambda *args: container)},
        )

        with patch("drive_blob_cli.service.ContainerClient", client):
            AzureClient(
                SimpleNamespace(
                    azure_connection_string="connection",
                    azure_container="container",
                )
            )
