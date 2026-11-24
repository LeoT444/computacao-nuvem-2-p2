# Project Plan: Google Drive to Azure Blob CLI

## Goal

Build a minimal Python command-line application that lists files in a configured
Google Drive folder, lists blobs in a configured Azure container, and copies
the Drive files to that container while reporting each transfer's result.

## Scope

- Python CLI and Vercel-hosted web interface; no database, scheduler, or
  background worker.
- Commands to list Drive files, list destination blobs, and synchronize files.
- Web authentication with Google OAuth 2.0 user consent and read-only Drive
  access. Keep the access token in browser memory only for the current session.
- Preserve optional service-account authentication for the CLI.
- Azure Blob Storage authentication with a connection string.
- Configuration loaded from `.env`; provide `.env.example` with placeholders
  only. Exclude `.env` and service-account credentials from version control.
- Copy each source file using its Drive filename as the blob name; replace a
  blob with the same name.
- Report success or a useful error for each transfer.
- A simple web interface is also included for Vercel, with server-side API
  actions publicly callable without an app-level access token; Google OAuth is
  still required for Drive actions.
- The interface is served by FastAPI and lets users list both sides, select
  files, and copy them sequentially.
- Each web copy is a separate serverless invocation and must fit the configured
  function duration and memory limits.

## Configuration

- `GOOGLE_OAUTH_CLIENT_ID`: public OAuth client ID for the web app.
- `GOOGLE_DRIVE_FOLDER_ID`: optional default folder ID; web users may enter
  their own folder ID.
- `GOOGLE_SERVICE_ACCOUNT_FILE` or `GOOGLE_SERVICE_ACCOUNT_JSON`: optional
  service-account credentials for CLI use.
- `AZURE_STORAGE_CONNECTION_STRING`: Azure Storage connection string.
- `AZURE_STORAGE_CONTAINER`: destination container name.

## Implementation

- Python 3.11+ with `google-api-python-client`, `google-auth`,
  `azure-storage-blob`, and `python-dotenv`.
- Use Google Drive read-only access and the Azure Blob SDK.
- Page through Drive and blob listing results.
- Download and upload file content without persisting copies in the project.
- Validate required settings and surface API/authentication errors clearly.

## Verification

- Add focused tests for configuration validation and the transfer/listing flow
  using mocked Google and Azure clients.
- Run the project tests and Python compilation checks.

## Approval

This plan must be approved before scaffolding begins.
