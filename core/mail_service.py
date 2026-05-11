"""
core/mail_service.py
Service for sending welcome emails using SMTP.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple, Dict, Any

from core.settings_manager import sm
from config import (
    DEFAULT_EMAIL_SENDER, DEFAULT_EMAIL_CC
)

class MailService:
    def __init__(self):
        pass

    def send_welcome_email(self, 
                           sender_email: str, 
                           sender_password: str, 
                           to_email: str, 
                           cc_email: str, 
                           user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Populates the template and sends a welcome email as HTML
        to prevent email clients (e.g. Gmail) from splitting the message.
        """
        try:
            # Populate the template from SettingsManager
            template = sm.get("welcome_email_template")
            plain_body = template.format(
                first_name=user_data.get("first_name", ""),
                email=user_data.get("email", ""),
                password=user_data.get("password", ""),
                sam_account_name=user_data.get("sam_account_name", "")
            )

            # Convert plain text to a minimal HTML version so that
            # the email is sent as a single MIME part and never split.
            html_body = "<html><body><pre style=\"font-family:Arial,sans-serif;font-size:14px;white-space:pre-wrap;\">" \
                        + plain_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
                        + "</pre></body></html>"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = sm.get("welcome_email_subject")
            msg["From"]    = sender_email
            msg["To"]      = to_email
            if cc_email:
                msg["Cc"] = cc_email

            # Attach plain text first, then HTML (email clients prefer the last part)
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body,  "html",  "utf-8"))

            recipients = [to_email] + ([cc_email] if cc_email else [])

            server = smtplib.SMTP("smtp.office365.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()

            return True, "Welcome email sent successfully"
        except smtplib.SMTPAuthenticationError:
            return False, "Email authentication failed. Check your password."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
