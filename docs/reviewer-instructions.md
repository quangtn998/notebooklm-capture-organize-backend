# NotebookLM Capture Organize Reviewer Instructions

Last updated: 2026-03-15

## Product framing

This extension is a companion for `notebooklm.google.com`.
It is not a replacement for NotebookLM.

NotebookLM remains the notebook and source system of record.
This extension owns:

- extension auth
- organize metadata
- capture metadata
- companion workflow surfaces

## Reviewer prerequisites

1. Sign in to a Google account that has access to NotebookLM.
2. Sign in to `https://notebooklm.google.com/`.
3. Ensure the hosted backend is reachable at `https://140.245.110.91.sslip.io`.
4. Public support page: `https://140.245.110.91.sslip.io/support`
5. Public privacy policy: `https://140.245.110.91.sslip.io/privacy-policy`
6. Open the extension Support route if you need to confirm or switch the backend target.

## Primary review flows

### 1. Extension account flow

1. Open the popup or `dashboard.html#/account`.
2. Create an extension account with email/password or use Google sign-in if configured.
3. Confirm that account state is separate from the NotebookLM web session state.

### 2. Organize flow

1. Open `dashboard.html#organize`.
2. Create a folder.
3. Rename the folder.
4. Move the folder.
5. Confirm the folder tree updates without leaving the dashboard.

### 3. Capture flow

1. Open `dashboard.html#capture`.
2. Select a NotebookLM notebook.
3. Use the capture workbench to import a supported source type.
4. Confirm the companion shell stays inside the extension while NotebookLM remains the target workspace.

### 4. NotebookLM page integration

1. Open a signed-in NotebookLM page.
2. Confirm the extension can detect whether the page is:
   - home
   - notebook
   - unsupported
3. Confirm the extension does not try to inject capture/organize actions into unsupported pages.

## Sensitive permissions

See `docs/permission-audit.md` for the detailed justification.

Short version:

- `tabs`, `activeTab`, `scripting`: required to inspect the active NotebookLM tab and inject companion UI/actions
- `debugger`, `offscreen`, `tabCapture`, `downloads`: required for page capture and recording-related flows inherited by the companion build
- backend origins are now pinned to local dev plus the hosted Oracle Cloud production service

## Deferred features

The following routes intentionally return deferred metadata instead of pretending to be active product features:

- billing
- OneDrive connector
- YouTube helper routes
- document mirror routes
- SEC mirror routes

These are not part of the owned MVP review path.
