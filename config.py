# file: config.py

import os
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()


# ================= REQUIRED VARS =================
REQUIRED_VARS = [
    "BOT_TOKEN",
    "ADMIN_IDS",
    "BOT_USERNAME",
    "MONGODB_URI",
    "STORAGE_CHAT_ID",
    "DISCORD_WEBHOOK_STATUS"
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]

if missing:
    raise ValueError(f"Missing environment variables: {missing}")


# ================= ENV VARIABLES =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
]

STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID"))

MONGODB_URI = os.getenv("MONGODB_URI")

DISCORD_WEBHOOK_STATUS = os.getenv("DISCORD_WEBHOOK_STATUS")
DISCORD_WEBHOOK_LIST_LOGS = os.getenv("DISCORD_WEBHOOK_LIST_LOGS")
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv("DISCORD_WEBHOOK_FILE_ACCESS")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")


# ================= OPTIONAL VALIDATION =================
def validate_webhook(url):
    return url and url.startswith("https://discord.com/api/webhooks/")


if not validate_webhook(DISCORD_WEBHOOK_STATUS):
    raise ValueError("Invalid DISCORD_WEBHOOK_STATUS")

# optional (no crash if missing)
if DISCORD_WEBHOOK_LIST_LOGS and not validate_webhook(DISCORD_WEBHOOK_LIST_LOGS):
    print("⚠️ Invalid LIST_LOGS webhook")

if DISCORD_WEBHOOK_FILE_ACCESS and not validate_webhook(DISCORD_WEBHOOK_FILE_ACCESS):
    print("⚠️ Invalid FILE_ACCESS webhook")

if DISCORD_WEBHOOK_ERRORS and not validate_webhook(DISCORD_WEBHOOK_ERRORS):
    print("⚠️ Invalid ERRORS webhook")


# ================= EMBED CONFIG =================
EMBED_CONFIG = {
    "default": {
        "color": 0x7289DA,
        "author": "Vanmam thavir Bot",
        "footer": "Powered by Rypera"
    },

    "status": {
        "color": 0xE74C3C,  # red
        "title": "⚙️ Bot Status"
    },

    "startup": {
        "color": 0x2ECC71,  # green
        "title": "🚀 Startup"
    },

    "list": {
        "color": 0x9B59B6,  # purple
        "title": "🧾 Admin Logs"
    },

    "access": {
        "color": 0xF1C40F,  # yellow
        "title": "📥 File Access"
    }
}