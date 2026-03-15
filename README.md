# NotebookLM Capture Organize Backend

Minimal backend for:

- local email/password login
- Google login
- session state
- folder organization
- notebook-to-folder mapping
- capture metadata

## Endpoints

- `/health`
- `/support`
- `/support/requests`
- `/privacy-policy`
- `/reviewer-notes`
- `/rest/v1/auth/oauth2/link`
- `/rest/v1/auth/login`
- `/rest/v1/auth/oauth2/login`
- `/auth/google/start`
- `/auth/google/callback`
- `/rest/v1/auth/is-logged-in`
- `/rest/v1/auth/logout`
- `/rest/v1/users`
- `/rest/v1/users/info`
- `/rest/v1/users/update-password`
- `/rest/v1/users/forgot-password`
- `/rest/v1/users/reset-password`
- `/rest/v1/folders`
- `/rest/v1/notebooks`
- `/rest/v1/captures`
- `/rest/v1/extension/info`
- stub compatibility routes for:
  - `/rest/v1/payments/*`
  - `/rest/v1/oauth2/onedrive/*`
  - `/rest/v1/external/youtube/videos`
  - `/rest/v1/sources/*`

## Run

```bash
cd /Users/tranngocquang/extension/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

## Notes

- The extension defaults to `http://127.0.0.1:8787`
- The chosen production host is `https://notebooklm-capture-organize-backend.onrender.com`
- The support route can switch the runtime backend target between the pinned local and production origins
- Email/password auth works without Google OAuth setup
- Google OAuth is optional and only needed if you want `Continue with Google`
- payment/connectors/source-helper routes currently return safe stub responses, not full product implementations
- deferred feature routes now identify themselves explicitly as `FeatureStatus: deferred`
- session cookies were verified from `chrome-extension://` pages in a real Chromium runtime
- the dashboard auth modal, folder list fetch, and folder creation flow were verified against this backend
- public support requests are stored in the SQLite backend under `support_requests`
- backend MVP contracts now have a real regression suite in:
  - `/Users/tranngocquang/extension/backend/tests/test_owned_mvp_contracts.py`
- auth endpoints now have simple in-memory rate limiting
- API responses now include request IDs, `Cache-Control: no-store`, and baseline security headers

## Render deployment

This repo now ships a Render blueprint and Docker image definition:

- `/Users/tranngocquang/extension/render.yaml`
- `/Users/tranngocquang/extension/backend/Dockerfile`

Render was chosen because the current FastAPI backend still uses SQLite and needs a persistent writable volume.

## Google OAuth

Create a Google OAuth web application and set:

- authorized redirect URI:
  - `http://127.0.0.1:8787/auth/google/callback`

Use the generated client ID and secret in `.env`.
