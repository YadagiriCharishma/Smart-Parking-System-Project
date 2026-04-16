from flask_mail import Message
from flask import current_app
from .extensions import mail


def send_email(subject: str, recipients: list[str], body: str, attachments: list[tuple[str, str, bytes]] | None = None):
    if not recipients:
        return
    msg = Message(subject=subject, recipients=recipients, body=body)
    if attachments:
        for filename, content_type, data in attachments:
            msg.attach(filename, content_type, data)
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Email send failed: {e}")


