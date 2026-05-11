import json
import os
from typing import Any, Dict
import config

SETTINGS_FILE = "settings.json"

class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        # Default values from config.py
        self.settings: Dict[str, Any] = {
            # Email
            "welcome_email_subject": config.WELCOME_EMAIL_SUBJECT,
            "welcome_email_template": config.WELCOME_EMAIL_TEMPLATE,
            "offboarding_email_subject": config.OFFBOARDING_EMAIL_SUBJECT,
            "offboarding_email_template": config.OFFBOARDING_EMAIL_TEMPLATE,
            "default_email_sender": config.DEFAULT_EMAIL_SENDER,
            "default_email_cc": config.DEFAULT_EMAIL_CC,

            # Defaults
            "default_city": config.DEFAULT_CITY,
            "default_state": config.DEFAULT_STATE,
            "default_zip": config.DEFAULT_ZIP,
            "default_country": config.DEFAULT_COUNTRY,
            "default_office": config.DEFAULT_OFFICE,
            "default_street": config.DEFAULT_STREET,

            # AD
            "ad_domain": config.AD_DOMAIN,
            "ad_server": config.AD_SERVER,

            # Lookups
            "departments": config.DEPARTMENTS,
        }

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except Exception as e:
                print(f"Error loading settings.json: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True, "Settings saved successfully."
        except Exception as e:
            return False, f"Error saving settings: {e}"

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value

# Global instance
sm = SettingsManager()
