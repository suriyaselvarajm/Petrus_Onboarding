
import os

path = r"c:\Petrus_Onboarding\gui\user_form.py"

# I have the file content in two parts from previous view_file calls.
# I will use a simplified version for this script to just fix the specific corruption.

with open(path, "rb") as f:
    data = f.read()

# 1. Fix the icons (they are the main source of "Non-UTF-8" errors if not handled correctly)
# I'll replace them with their original UTF-8 bytes.
icons = {
    b"dY`\x00": "👤",
    b"dY\x13\x0b": "📋",
    b"dY\x02": "☁",
    b"dY-\x3f": "🗝",
    b"dY\x14": "👔",
    b"dY\x10": "👥",
    b"dY\x15": "🖥",
    b"dY\x10\x12": "🔐",
    b"dY\x12\xb2": "🎲",
    b"dY\x12\x80": "🚀",
    b"dY\x13\x91": "🗑",
}

# 2. Fix the separators
# The separator is 80 chars of \u2500 (─)
separator_utf8 = ("─" * 80).encode("utf-8")
# It might be mangled as multiple "? or similar.
# I'll just look for long sequences of high-bit characters.

# Actually, I'll just use regex to replace any line that looks like a corrupted separator.
import re
data = re.sub(rb'# [\xe2\x94\x80]{20,}', b'# ' + separator_utf8, data)
data = re.sub(rb'# ["?]{20,}', b'# ' + separator_utf8, data)

# 3. Fix the specific IndentationError at line 371
# It likely happened because def _build_license lost its 4 spaces.
data = data.replace(b"\ndef _build_license", b"\n    def _build_license")
data = data.replace(b"\ndef _build_azure", b"\n    def _build_azure")
data = data.replace(b"\ndef _build_manager", b"\n    def _build_manager")
data = data.replace(b"\ndef _build_o365_groups", b"\n    def _build_o365_groups")
data = data.replace(b"\ndef _build_ad_config", b"\n    def _build_ad_config")
data = data.replace(b"\ndef _build_security", b"\n    def _build_security")
data = data.replace(b"\ndef _build_action_bar", b"\n    def _build_action_bar")

# 4. Fix the _build_personal indentation
# It was at line 220
data = data.replace(b"        def _build_personal", b"    def _build_personal")

with open(path, "wb") as f:
    f.write(data)

print("File fixed")
