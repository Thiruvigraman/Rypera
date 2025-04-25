import requests
import os

def log_to_discord(webhook_url: str, message: str):
    data = {"content": message}
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        print(f"Log sent: {message}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to log to Discord: {e}")

def log_status(message: str):
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Status: {message}")

def log_movie_action(action: str, movie_name: str, file_id: str):
    webhook = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')
    if action == 'added':
        log_to_discord(webhook, f"Added: {movie_name} (File ID: {file_id})")
    elif action == 'renamed':
        log_to_discord(webhook, f"Renamed: {movie_name} (File ID: {file_id})")
    elif action == 'deleted':
        log_to_discord(webhook, f"Deleted: {movie_name} (File ID: {file_id})")
    else:
        log_to_discord(webhook, f"Unknown action: {action} on {movie_name}")

def log_error(message: str):
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"Error: {message}")