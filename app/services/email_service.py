import smtplib
from email.message import EmailMessage
from typing import List

from app.core.config import settings


def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()

    # ✅ Sender name + email
    msg["From"] = f"{settings.SMTP_SENDER_NAME} <{settings.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise RuntimeError(f"Email send failed: {e}")


def send_updates_email(to_email: str, topic_title: str, updates: List[object]):
    """Send a minimal, structured HTML email containing a list of updates.

    - ``updates`` is expected to be a list of objects with ``title``,
      ``summary`` and optional ``source_url`` attributes (e.g. ``Update`` models).
    - The email uses a clean, minimal layout without gradients.
    """
    safe_topic_title = topic_title or "your topic"

    # Fallback: if there are no updates, send a simple text email and return
    if not updates:
        body = f"There are currently no new updates for '{safe_topic_title}'."
        send_email(to_email, f"No new updates for {safe_topic_title}", body)
        return

    # Build plain-text body
    lines = [
        f"Here is a quick snapshot of your latest updates for '{safe_topic_title}':",
        "",
    ]

    for idx, u in enumerate(updates, start=1):
        title = getattr(u, "title", None) or "Update"
        summary = getattr(u, "summary", None) or ""
        source_url = getattr(u, "source_url", None) or ""

        lines.append(f"{idx}. {title}")
        if summary:
            lines.append(f"   {summary}")
        if source_url:
            lines.append(f"   Source: {source_url}")
        lines.append("")

    text_body = "\n".join(lines).strip()

    # Build minimal HTML body
    items_html_parts = []
    for u in updates:
        title = getattr(u, "title", None) or "Update"
        summary = getattr(u, "summary", None) or "No description available."
        source_url = getattr(u, "source_url", None) or ""

        link_html = ""
        if source_url:
            link_html = f"""
              <a href=\"{source_url}\" style=\"color:#2563eb;text-decoration:none;font-size:13px;\">View source</a>
            """

          # Use full-width block cards with bottom margin so they
          # reliably stack as rows in email clients (no flexbox).
          items_html_parts.append(
              f"""
              <div style=\"width:100%;box-sizing:border-box;padding:12px 14px;border-radius:10px;border:1px solid #e5e7eb;background-color:#f9fafb;margin-bottom:12px;\">
                <div style=\"font-size:14px;font-weight:600;color:#111827;margin-bottom:4px;\">{title}</div>
                <div style=\"font-size:13px;color:#4b5563;line-height:1.5;margin-bottom:6px;\">{summary}</div>
                {link_html}
              </div>
              """
          )

    items_html = "".join(items_html_parts)

    html_body = f"""\
<html>
  <body style=\"margin:0;padding:24px;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;\">
    <div style=\"max-width:640px;margin:0 auto;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;\">
      <h1 style=\"font-size:20px;margin:0 0 8px 0;color:#111827;font-weight:600;\">Your updates on {safe_topic_title}</h1>
      <p style=\"margin:0 0 18px 0;color:#4b5563;font-size:14px;\">A concise snapshot of what changed around this topic.</p>
        <div>
        {items_html}
      </div>
      <p style=\"margin-top:22px;font-size:12px;color:#9ca3af;\">You're receiving this email because you asked Neuraletter to follow this topic.</p>
    </div>
  </body>
</html>
"""

    msg = EmailMessage()
    msg["From"] = f"{settings.SMTP_SENDER_NAME} <{settings.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = f"New updates for {safe_topic_title}"
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise RuntimeError(f"Email send failed: {e}")
