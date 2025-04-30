import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_to_discord(webhook_url, message, embed=None):
    try:
        data = {"content": message}
        if embed:
            data["embeds"] = [embed]
        requests.post(webhook_url, json=data)
    except Exception as e:
        logger.error(f"Discord log error: {e}")

def create_embed(title, desc, color=0x00ff00):
    return {
        "title": title,
        "description": desc,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Premium Bot"}
    }