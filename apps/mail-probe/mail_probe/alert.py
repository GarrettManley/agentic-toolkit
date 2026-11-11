"""Failure alert by email via Gmail SMTP submission — deliberately independent of the
forwarding path under test (sends straight to the Gmail address)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


def send_alert(user: str, app_password: str, *, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = user
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, app_password)
        smtp.send_message(msg)
