from __future__ import annotations

from collections.abc import Iterable

from .service import AzureClient, CopyResult, DriveClient


def copy_file(
    drive: DriveClient,
    azure: AzureClient,
    source: DriveFile,
) -> CopyResult:
    try:
        content = drive.download(source.id)
        azure.upload(source.name, content)
        return CopyResult(name=source.name, success=True)
    except Exception as exc:
        return CopyResult(name=source.name, success=False, error=str(exc))


def copy_files(
    drive: DriveClient,
    azure: AzureClient,
) -> Iterable[CopyResult]:
    for source in drive.list_files():
        yield copy_file(drive, azure, source)
