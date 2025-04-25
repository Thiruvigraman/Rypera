import requests
import os

def log_to_discord(webhook_url: str, message: str) -> None:
    """
    Sends a log message to the specified Discord webhook.
    
    Args:
    webhook_url (str): The Discord webhook URL.
    message (str): The message to send.
    """
    data = {"content": message}
    
    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()  # Check if the request was successful
        print(f"✅ Log sent successfully: {message}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send log: {e}")

def log_status(message: str) -> None:
    """
    Sends a status log message to the Discord webhook.
    
    Args:
    message (str): The status message.
    """
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"🚀 Status Update: {message} ✔️")

def log_movie_action(action: str, movie_name: str, file_id: str) -> None:
    """
    Logs movie-related actions such as adding, renaming, or deleting movies.
    
    Args:
    action (str): The action performed (e.g., added, renamed, deleted).
    movie_name (str): The name of the movie.
    file_id (str): The file ID of the movie.
    """
    if action == 'added':
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"🎥 Movie added: {movie_name} 📎 (File ID: {file_id})")
    elif action == 'renamed':
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"📝 Movie renamed: {movie_name} 🎬 (File ID: {file_id})")
    elif action == 'deleted':
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"🗑️ Movie deleted: {movie_name} 🔴 (File ID: {file_id})")
    else:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_LIST_LOGS'), f"⚠️ Unknown action: {action} for movie: {movie_name}")

def log_error(error_message: str) -> None:
    """
    Logs error messages to the Discord webhook.
    
    Args:
    error_message (str): The error message to log.
    """
    log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"⚠️ Error: {error_message} ❌")