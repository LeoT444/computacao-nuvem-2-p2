# Google Drive to Azure Blob

A minimal Python 3.11+ application with a web interface and CLI. It lists files
from a Google Drive folder, lists Azure blobs, and copies selected files.

## Setup

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -e .
python -m pip install pytest
Copy-Item .env.example .env
```

For the CLI, set a Google service-account JSON path and Drive folder ID. For the
web app, set a Google OAuth client ID, Azure connection string, container name,
and optionally a default Drive folder ID. Web users can enter a folder ID
themselves.

## Web interface

Run locally with the Vercel CLI:

```powershell
npm install --global vercel
vercel dev
```

On Windows, if `vercel dev` fails with `EPERM` while creating symlinks, enable
Developer Mode in **Settings > System > For developers**, then reopen the
terminal and retry. Alternatively, run the terminal as Administrator.

Create a Google OAuth client ID of type **Web application** in Google Cloud,
enable the Google Drive API, and add your Vercel domain and local origin
(`http://localhost:3000`) as authorized JavaScript origins. Configure the
OAuth consent screen and add test users while the app is in testing mode.

Set `GOOGLE_OAUTH_CLIENT_ID` in `.env`, then open the local URL. Connect a
Google account and paste the ID of a Drive folder. The app requests read-only
Drive access. The short-lived Google access token is kept only in browser
memory and sent to this app's API; it is not persisted. After it expires or
the page is closed, the user connects again. Azure credentials remain
server-side.

Deploy the project to Vercel and set these project environment variables:

- `GOOGLE_OAUTH_CLIENT_ID`: the Google OAuth web client ID.
- `GOOGLE_DRIVE_FOLDER_ID`: optional default folder ID; users can enter their
  own folder ID in the interface.
- `AZURE_STORAGE_CONNECTION_STRING`: the Azure Storage connection string.
- `AZURE_STORAGE_CONTAINER`: the destination container.

The app automatically creates the configured container if it does not exist.
The storage account itself must already exist, and the connection string must
allow creating containers.

The web API has no app-level access token and is publicly callable. Anyone can
list blob names and, with their own Google authorization, copy files they can
access into the configured container; a copied file can overwrite a blob with
the same name. Do not deploy this configuration with sensitive data unless
you add another access-control layer.

Use Vercel's encrypted Environment Variables; do not commit secrets. The OAuth
client ID is public, but the Azure connection string must remain private.
Google may require OAuth app verification before users outside the configured
test-user list can authorize the Drive read-only scope.

The per-file copy action runs in a single serverless invocation, so each file
must finish within the function's configured duration and memory limits. The
interface copies selected files sequentially and reports each result.

## Commands

```powershell
drive-blob list-drive
drive-blob list-azure
drive-blob copy
```

Copies use each Drive filename as the blob name and replace an existing blob
with the same name. The CLI continues to authenticate with a service account;
the web interface uses each user's OAuth authorization. Credentials and `.env`
are ignored by Git.

## Tests

```powershell
python -m pytest
python -m compileall -q src tests
```
