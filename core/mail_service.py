"""
core/mail_service.py
Service for sending welcome emails using SMTP.
"""

import smtplib
from email.message import EmailMessage
from typing import Tuple, Dict, Any

from config import (
    WELCOME_EMAIL_SUBJECT, WELCOME_EMAIL_TEMPLATE,
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
        Populates the template and sends a welcome email.
        """
        try:
            # Prepare the body
            body = WELCOME_EMAIL_TEMPLATE.format(
                first_name=user_data.get("first_name", ""),
                email=user_data.get("email", ""),
                password=user_data.get("password", ""),
                sam_account_name=user_data.get("sam_account_name", "")
            )

            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = WELCOME_EMAIL_SUBJECT
            msg['From'] = sender_email
            msg['To'] = to_email
            if cc_email:
                msg['Cc'] = cc_email

            # Connect to Office 365 SMTP server
            # Note: O365 SMTP requires 'modern authentication' (OAuth2) in many tenants, 
            # but legacy SMTP AUTH might still work if enabled.
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            return True, "Welcome email sent successfully"
        except smtplib.SMTPAuthenticationError:
            return False, "Email authentication failed. Check your password."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
