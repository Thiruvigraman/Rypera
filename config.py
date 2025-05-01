#config.py

import os
from typing import Dict

def validate_env_vars():
    """Validate required environment variables."""
    required_vars = [
        "BOT_TOKEN",
        "MONGODB_URI",
        "ADMIN_ID",
        "BOT_USERNAME",
        "DISCORD_WEBHOOK_STATUS",
        "DISCORD_WEBHOOK_LIST_LOGS",
        "DISCORD_WEBHOOK_FILE_ACCESS"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")
    try:
        int(os.getenv("ADMIN_ID"))
    except ValueError:
        raise EnvironmentError("ADMIN_ID must be an integer")

validate_env_vars()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BOT_USERNAME = os.getenv("BOT_USERNAME")
DISCORD_WEBHOOK_STATUS = os.getenv("DISCORD_WEBHOOK_STATUS")
DISCORD_WEBHOOK_LIST_LOGS = os.getenv("DISCORD_WEBHOOK_LIST_LOGS")
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv("DISCORD_WEBHOOK_FILE_ACCESS")
APP_URL = os.getenv("APP_URL", "https://rypera.onrender.com")