import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda *args, **kwargs: False
sys.modules.setdefault("dotenv", dotenv)

from drive_blob_cli.config import load_settings


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.original = os.environ.copy()
        for key in (
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "GOOGLE_SERVICE_ACCOUNT_JSON",
            "GOOGLE_DRIVE_FOLDER_ID",
            "AZURE_STORAGE_CONNECTION_STRING",
            "AZURE_STORAGE_CONTAINER",
        ):
            os.environ.pop(key, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original)

    def test_load_settings_accepts_complete_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "credentials.json"
            credential.write_text("{}")
            os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = str(credential)
            os.environ["GOOGLE_DRIVE_FOLDER_ID"] = "folder-id"
            os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "UseDevelopmentStorage=true"
            os.environ["AZURE_STORAGE_CONTAINER"] = "files"

            settings = load_settings(Path(directory) / "missing.env")

            self.assertEqual(settings.google_drive_folder_id, "folder-id")
            self.assertEqual(settings.azure_container, "files")

    def test_load_settings_rejects_missing_environment(self):
        with self.assertRaisesRegex(ValueError, "Missing required configuration"):
            load_settings("/path/that/does/not/exist.env")

    def test_load_settings_accepts_service_account_json_without_local_file(self):
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = '{"type":"service_account"}'
        os.environ["GOOGLE_DRIVE_FOLDER_ID"] = "folder-id"
        os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "UseDevelopmentStorage=true"
        os.environ["AZURE_STORAGE_CONTAINER"] = "files"

        settings = load_settings("/path/that/does/not/exist.env")

        self.assertIsNone(settings.google_service_account_file)
        self.assertEqual(
            settings.google_service_account_json,
            '{"type":"service_account"}',
        )

    def test_load_settings_rejects_invalid_service_account_json(self):
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = "not-json"
        os.environ["GOOGLE_DRIVE_FOLDER_ID"] = "folder-id"
        os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "UseDevelopmentStorage=true"
        os.environ["AZURE_STORAGE_CONTAINER"] = "files"

        with self.assertRaisesRegex(ValueError, "must contain valid JSON"):
            load_settings("/path/that/does/not/exist.env")

    def test_load_settings_allows_web_oauth_without_service_account_or_default_folder(self):
        os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "UseDevelopmentStorage=true"
        os.environ["AZURE_STORAGE_CONTAINER"] = "files"

        settings = load_settings(
            "/path/that/does/not/exist.env",
            require_google_service_account=False,
            require_drive_folder=False,
        )

        self.assertIsNone(settings.google_service_account_file)
        self.assertIsNone(settings.google_service_account_json)
        self.assertIsNone(settings.google_drive_folder_id)
