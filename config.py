#config.py

import os
from typing import Dict
import re

def validate_env_vars():
    """Validate required environment variables."""
    required_vars = [
        "BOT_TOKEN",
        "MONGODB_URI",
        "ADMIN_ID",
        "BOT_USERNAME",
        "DISCORD_WEBHOOK_STATUS",
        "DISCORD_WEBHOOK_LIST_LOGS",
        "DISCORD_WEBHOOK_FILE_ACCESS",
        "APP_URL"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")
    try:
        int(os.getenv("ADMIN_ID"))
    except ValueError:
        raise EnvironmentError("ADMIN_ID must be an integer")
    app_url = os.getenv("APP_URL")
    if not re.match(r'^https://[a-zA-Z0-9-]+\.onrender\.com$', app_url):
        raise EnvironmentError("APP_URL must be a valid Render URL (e.g., https://your-app.onrender.com)")

validate_env_vars()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BOT_USERNAME = os.getenv("BOT_USERNAME")
DISCORD_WEBHOOK_STATUS = os.getenv("DISCORD_WEBHOOK_STATUS")
DISCORD_WEBHOOK_LIST_LOGS = os.getenv("DISCORD_WEBHOOK_LIST_LOGS")
DISCORD_WEBHOOK_FILE_ACCESS = os.getenv("DISCORD_WEBHOOK_FILE_ACCESS")
APP_URL = os.getenv("APP_URL")
DELETION_MINUTES = int(os.getenv("DELETION_MINUTES", 30))