from __future__ import annotations

import argparse
import sys

from googleapiclient.errors import HttpError

from .app import copy_files
from .config import load_settings
from .service import AzureClient, DriveClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drive-blob",
        description="List and copy Google Drive files to Azure Blob Storage.",
    )
    parser.add_argument(
        "command",
        choices=("list-drive", "list-azure", "copy"),
        help="operation to perform",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        settings = load_settings()
        drive = DriveClient(settings)
        azure = AzureClient(settings)

        if args.command == "list-drive":
            for item in drive.list_files():
                print(item.name)
            return 0

        if args.command == "list-azure":
            for item in azure.list_blobs():
                print(item.name)
            return 0

        failures = 0
        for result in copy_files(drive, azure):
            if result.success:
                print(f"SUCCESS: {result.name}")
            else:
                failures += 1
                print(f"ERROR: {result.name}: {result.error}", file=sys.stderr)
        return 1 if failures else 0
    except (ValueError, FileNotFoundError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Operation error: {exc}", file=sys.stderr)
        return 1
