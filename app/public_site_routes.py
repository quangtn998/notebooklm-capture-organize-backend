from __future__ import annotations

from html import escape
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .http_helpers import data_response


router = APIRouter()
DOCS_DIR_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "docs",
    Path(__file__).resolve().parents[1] / "docs",
)


def _render_page(title: str, body_html: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "Inter", "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #f7f3eb 0%, #fff 100%);
        color: #172033;
      }}
      main {{
        max-width: 820px;
        margin: 0 auto;
        padding: 48px 20px 64px;
      }}
      .card {{
        background: rgba(255, 255, 255, 0.96);
        border: 1px solid #d8deea;
        border-radius: 24px;
        box-shadow: 0 24px 60px rgba(24, 44, 82, 0.08);
        padding: 28px;
      }}
      h1, h2, h3 {{ line-height: 1.15; }}
      h1 {{ font-size: 2.25rem; margin: 0 0 0.75rem; }}
      h2 {{ font-size: 1.4rem; margin: 2rem 0 0.75rem; }}
      h3 {{ font-size: 1.1rem; margin: 1.25rem 0 0.5rem; }}
      p, li {{ color: #34415d; font-size: 0.98rem; line-height: 1.65; }}
      ul {{ padding-left: 1.2rem; }}
      a {{ color: #1d4ed8; text-decoration: none; }}
      .eyebrow {{ color: #1d4ed8; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.24em; text-transform: uppercase; }}
      .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 1.5rem; }}
      .button {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        background: #172033;
        color: #fff;
        cursor: pointer;
        font: inherit;
        padding: 0.85rem 1.1rem;
      }}
      .field {{ display: block; margin-top: 1rem; }}
      .field span {{ display: block; font-weight: 600; margin-bottom: 0.4rem; }}
      input, textarea {{
        border: 1px solid #c5cedf;
        border-radius: 16px;
        box-sizing: border-box;
        font: inherit;
        padding: 0.9rem 1rem;
        width: 100%;
      }}
      textarea {{ min-height: 160px; resize: vertical; }}
      .status {{ margin-top: 1rem; min-height: 1.5rem; font-size: 0.95rem; }}
      .meta {{ color: #56647f; font-size: 0.92rem; }}
    </style>
  </head>
  <body>
    <main>{body_html}</main>
  </body>
</html>"""
    return HTMLResponse(html)


def _render_markdown_document(filename: str, page_title: str, eyebrow: str) -> HTMLResponse:
    for docs_dir in DOCS_DIR_CANDIDATES:
        candidate = docs_dir / filename
        if candidate.exists():
            lines = candidate.read_text(encoding="utf-8").splitlines()
            break
    else:
        raise FileNotFoundError(f"Unable to find {filename} in docs directories: {DOCS_DIR_CANDIDATES!r}")
    parts = [f'<div class="card"><p class="eyebrow">{escape(eyebrow)}</p>']
    list_open = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if list_open:
                parts.append("</ul>")
                list_open = False
            continue
        if line.startswith("# "):
            if list_open:
                parts.append("</ul>")
                list_open = False
            parts.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            if list_open:
                parts.append("</ul>")
                list_open = False
            parts.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("- ") or re.match(r"^\\d+\\.\\s+", line):
            if not list_open:
                parts.append("<ul>")
                list_open = True
            item = re.sub(r"^\\d+\\.\\s+", "", line[2:] if line.startswith("- ") else line)
            parts.append(f"<li>{escape(item)}</li>")
            continue
        if list_open:
            parts.append("</ul>")
            list_open = False
        parts.append(f"<p>{escape(line)}</p>")
    if list_open:
        parts.append("</ul>")
    parts.append("</div>")
    return _render_page(page_title, "".join(parts))


@router.get("/", include_in_schema=False)
async def public_root() -> RedirectResponse:
    return RedirectResponse("/support", status_code=302)


@router.get("/support", response_class=HTMLResponse)
async def support_page(request: Request) -> HTMLResponse:
    settings = request.app.state.settings
    contact_line = (
        f'<p class="meta">Direct support email: <a href="mailto:{escape(settings.public_support_email)}">{escape(settings.public_support_email)}</a></p>'
        if settings.public_support_email
        else '<p class="meta">Use the support form below. This public page is the release support contact for the Chrome Web Store listing.</p>'
    )
    body = f"""
    <div class="card">
      <p class="eyebrow">Support</p>
      <h1>NotebookLM Capture Organize</h1>
      <p>Public support surface for the companion extension backend.</p>
      {contact_line}
      <p class="meta">Privacy policy: <a href="{escape(settings.privacy_policy_url)}">{escape(settings.privacy_policy_url)}</a></p>
      <div class="actions">
        <a class="button" href="{escape(settings.privacy_policy_url)}">Open privacy policy</a>
        <a class="button" href="{escape(settings.reviewer_notes_url)}">Open reviewer notes</a>
      </div>
      <form id="support-form">
        <label class="field"><span>Email</span><input id="email" type="email" autocomplete="email" required /></label>
        <label class="field"><span>Subject</span><input id="subject" type="text" maxlength="160" required /></label>
        <label class="field"><span>Message</span><textarea id="message" maxlength="4000" required></textarea></label>
        <div class="actions"><button class="button" type="submit">Send support request</button></div>
        <p class="status" id="status"></p>
      </form>
    </div>
    <script>
      const form = document.getElementById("support-form");
      const status = document.getElementById("status");
      form.addEventListener("submit", async event => {{
        event.preventDefault();
        status.textContent = "Sending...";
        const payload = {{
          email: document.getElementById("email").value.trim(),
          subject: document.getElementById("subject").value.trim(),
          message: document.getElementById("message").value.trim()
        }};
        const response = await fetch("/support/requests", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(payload)
        }});
        const json = await response.json().catch(() => ({{ data: {{ Success: false, Msg: "Support request failed." }} }}));
        status.textContent = json?.data?.Success
          ? `Request #${{json.data.RequestID}} received.`
          : (json?.data?.Msg || "Support request failed.");
        if (json?.data?.Success) form.reset();
      }});
    </script>
    """
    return _render_page("NotebookLM Capture Organize Support", body)


@router.post("/support/requests")
async def create_support_request(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        return data_response({"Success": False, "Msg": "Support request payload must be valid JSON."})
    email = str(payload.get("email", "")).strip().lower()
    subject = str(payload.get("subject", "")).strip()
    message = str(payload.get("message", "")).strip()
    if "@" not in email or len(email) > 320:
        return data_response({"Success": False, "Msg": "Enter a valid reply email."})
    if not subject or len(subject) > 160:
        return data_response({"Success": False, "Msg": "Enter a subject up to 160 characters."})
    if not message or len(message) > 4000:
        return data_response({"Success": False, "Msg": "Enter a message up to 4000 characters."})
    cursor = request.app.state.db.execute(
        "INSERT INTO support_requests (email, subject, message) VALUES (?, ?, ?)",
        (email, subject, message),
    )
    request.app.state.db.commit()
    return data_response({"Success": True, "RequestID": cursor.lastrowid})


@router.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy_page() -> HTMLResponse:
    return _render_markdown_document("privacy-policy.md", "NotebookLM Capture Organize Privacy Policy", "Privacy")


@router.get("/reviewer-notes", response_class=HTMLResponse)
async def reviewer_notes_page() -> HTMLResponse:
    return _render_markdown_document("reviewer-instructions.md", "NotebookLM Capture Organize Reviewer Notes", "Review")
