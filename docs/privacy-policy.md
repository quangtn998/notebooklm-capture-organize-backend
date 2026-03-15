# NotebookLM Capture Organize Privacy Policy

Last updated: 2026-03-15

## Product scope

NotebookLM Capture Organize is a companion extension for `notebooklm.google.com`.
It helps users capture sources, organize notebooks, and manage extension-owned account data.

## Data we process

1. Extension account data
- email address
- password hash when email/password auth is used
- optional Google profile data when Google sign-in is used

2. Organize metadata
- folder names
- folder hierarchy
- notebook-to-folder mappings

3. Capture metadata
- capture title
- capture source URL
- capture source type
- optional user note
- optional raw payload needed to restore the capture record

4. Companion page context
- active NotebookLM tab URL
- notebook identifier parsed from NotebookLM URLs
- DOM anchor checks needed to mount companion UI into NotebookLM pages

## What we do not claim to own

- NotebookLM notebooks themselves
- NotebookLM source files themselves
- NotebookLM model output itself

Those remain part of the user's NotebookLM and Google account context.

## Storage

- Extension-local state is stored in Chrome extension storage and local browser storage.
- Owned account, organize, and capture metadata are stored in the companion backend selected by the extension.
- The development default backend is `http://127.0.0.1:8787`.
- Production deployments should use an HTTPS backend with secure cookies.

## Sharing and third parties

- The extension interacts with `notebooklm.google.com` because that is the companion target.
- Google OAuth is optional and only used when the user chooses Google sign-in for the extension account.
- Legacy analytics have been disabled in this build.
- Deferred connector and billing routes do not operate as active third-party services in this build.

## Security

- Passwords are stored as salted PBKDF2 hashes in the owned backend.
- Backend auth routes are rate limited.
- API responses include `Cache-Control: no-store`.
- Production deployments should enable HTTPS, secure cookies, and a narrowed CORS allow-list.

## User controls

- Users can sign out of the extension account.
- Users can change the configured backend target from the Support route.
- Users can reset the backend target to the local development default from the Support route.

## Contact

Public support site:

- `https://notebooklm-capture-organize-backend.onrender.com/support`

Public privacy policy URL:

- `https://notebooklm-capture-organize-backend.onrender.com/privacy-policy`

If `PUBLIC_SUPPORT_EMAIL` is configured on the hosted backend, the support page will also display the direct support email.
