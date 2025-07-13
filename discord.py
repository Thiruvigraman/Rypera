# discord.py
import requests

def log_to_discord(webhook, message):
    if webhook:
        try:
            requests.post(webhook, json={"content": message})
        except:
            pass