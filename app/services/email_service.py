import httpx
from typing import List

from app.core.config import settings


class MailDoorService:
    """Sends emails via the MailDoor HTTP API."""

    def __init__(
        self,
        api_url: str = settings.MAILDOOR_API_URL,
        api_key: str = settings.MAILDOOR_API_KEY,
        from_name: str = settings.MAILDOOR_FROM_NAME,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.from_name = from_name

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        content_type: str = "html",
    ) -> None:
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "fromName": self.from_name,
            "contentType": content_type,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            response = httpx.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"MailDoor API returned {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise RuntimeError(f"MailDoor request failed: {e}")

    def send_plain(self, to: str, subject: str, body: str) -> None:
        self.send(to, subject, body, content_type="text")

    def send_html(self, to: str, subject: str, html_body: str) -> None:
        self.send(to, subject, html_body, content_type="html")


# Module-level instance for convenience
maildoor = MailDoorService()


# ---------------------------------------------------------------------------
# Backward-compatible wrapper – callers that `from email_service import send_email`
# continue to work without any changes.
# ---------------------------------------------------------------------------
def send_email(to_email: str, subject: str, body: str) -> None:
    maildoor.send_plain(to_email, subject, body)


# ---------------------------------------------------------------------------
# Update emails (HTML)
# ---------------------------------------------------------------------------
def send_updates_email(to_email: str, topic_title: str, updates: List[object]) -> None:

    safe_topic_title = topic_title or "your topic"

    if not updates:
        body = f"There are currently no new updates for '{safe_topic_title}'."
        maildoor.send_plain(to_email, f"No new updates for {safe_topic_title}", body)
        return

    items_html_parts = []
    for u in updates:
        title = getattr(u, "title", None) or "Update"
        summary = getattr(u, "summary", None) or "No description available."
        source_url = getattr(u, "source_url", None) or ""

        link_html = ""
        if source_url:
            link_html = (
                f'<a href="{source_url}" style="color:#2563eb;text-decoration:none;'
                f'font-size:13px;">View source</a>'
            )

        items_html_parts.append(
            f'<div style="width:100%;box-sizing:border-box;padding:12px 14px;'
            f'border-radius:10px;border:1px solid #e5e7eb;background-color:#f9fafb;'
            f'margin-bottom:12px;">'
            f'<div style="font-size:14px;font-weight:600;color:#111827;'
            f'margin-bottom:4px;">{title}</div>'
            f'<div style="font-size:13px;color:#4b5563;line-height:1.5;'
            f'margin-bottom:6px;">{summary}</div>'
            f'{link_html}'
            f'</div>'
        )

    items_html = "".join(items_html_parts)

    html_body = f"""\
<html>
  <body style="margin:0;padding:24px;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <div style="max-width:640px;margin:0 auto;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;">
      <h1 style="font-size:20px;margin:0 0 8px 0;color:#111827;font-weight:600;">Your updates on {safe_topic_title}</h1>
      <p style="margin:0 0 18px 0;color:#4b5563;font-size:14px;">A concise snapshot of what changed around this topic.</p>
        <div>
        {items_html}
      </div>
      <p style="margin-top:22px;font-size:12px;color:#9ca3af;">You're receiving this email because you asked Neuraletter to follow this topic.</p>
    </div>
  </body>
</html>
"""

    maildoor.send_html(to_email, f"New updates for {safe_topic_title}", html_body)
