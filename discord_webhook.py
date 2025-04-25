import requests
import os

def log_to_discord(webhook_url: str, message: str):
    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error logging to Discord: {e}")