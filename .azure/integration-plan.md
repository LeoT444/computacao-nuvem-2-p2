# Integration Plan

## Backend
- Project folder: `P2`
- Web entry point: `app.py` (FastAPI).
- CLI entry point: `src/drive_blob_cli/cli.py`; package command `drive-blob`.
- Build/install: `python -m pip install -e .`
- Runtime: Python 3.12+ on Vercel; Python 3.11+ for the CLI.
- `GET /` serves the interface; no separate health endpoint.

## Frontend
- Responsive static interface: `index.html`.
- Loads Drive and Azure listings, lets the user select files, and displays each
  copy result.

## API routes
- Web API: FastAPI entrypoint `app.py`, deployed as a Vercel Function.
  - `GET /api/config`: public OAuth client ID and optional default folder ID.
  - `POST /api` with `list-drive`: page and return Google Drive files.
  - `POST /api` with `list-azure`: page and return Azure blob names.
  - `POST /api` with `copy-file`: download one Drive file and upload it,
    overwrite enabled.
- CLI operations remain available through `drive-blob`.

## Database
- None.
- No migrations or seed data.

## Azure services
- Azure Blob Storage — Essential.
- Google Drive API — Essential.
- No Azure resources require provisioning or deployment.
- Vercel deployment uses environment variables for server-side credentials and
  requires each per-file transfer to fit within the function's 60-second limit.
- Web Drive requests use the connected user's short-lived OAuth access token;
  it stays in browser memory and is not persisted.

## Configuration
- `.env` variables: `GOOGLE_OAUTH_CLIENT_ID`, optional
  `GOOGLE_DRIVE_FOLDER_ID`, `AZURE_STORAGE_CONNECTION_STRING`,
  `AZURE_STORAGE_CONTAINER`.
- The web API has no app-level access token and is publicly callable. Google
  OAuth is still required for Drive actions; deployment requires a separate
  access-control layer if anonymous use is not intended.
- Optional CLI credentials: `GOOGLE_SERVICE_ACCOUNT_FILE` or
  `GOOGLE_SERVICE_ACCOUNT_JSON`; never commit.

## Testing
- Project: `P2`
- Test command: `py -3.12 -m unittest discover -s tests -v`
- Compile command: direct Python `compile()` check over `app.py`, `src/**/*.py`,
  and `tests/**/*.py`.
