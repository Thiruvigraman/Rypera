# commands.py
from typing import Optional, Dict, Any
from bot import send_message, send_file
from database import load_movies, save_movie, delete_movie, rename_movie
from utils import log_to_discord
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

TEMP_FILE_IDS: Dict[int, str] = {}

def handle_admin_upload(chat_id: int, user_id: int, document: Optional[Dict[str, Any]], video: Optional[Dict[str, Any]]) -> None:
    """Handle file upload by admin."""
    if user_id != ADMIN_ID:
        return

    file_id = None
    if document:
        file_id = document.get('file_id')
    elif video:
        file_id = video.get('file_id')

    if file_id:
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")

def handle_admin_naming_movie(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle naming a movie."""
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]

def handle_list_files(chat_id: int, user_id: int) -> None:
    """Handle listing all stored files."""
    if user_id != ADMIN_ID:
        return

    movies = load_movies()
    if movies:
        msg = "Stored Files:\n" + "\n".join(movies.keys())
    else:
        msg = "No files stored."
    send_message(chat_id, msg)

def handle_rename_file(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle renaming a file."""
    if user_id != ADMIN_ID or not text or not text.startswith('/rename_file'):
        return

    parts = text.strip().split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "Usage: /rename_file OldName NewName")
        return

    _, old_name, new_name = parts
    if rename_movie(old_name, new_name):
        send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Renamed '{old_name}' to '{new_name}'")
    else:
        send_message(chat_id, f"Movie '{old_name}' not found.")

def handle_delete_file(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle deleting a file."""
    if user_id != ADMIN_ID or not text or not text.startswith('/delete_file'):
        return

    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_file FileName")
        return

    file_name = parts[1]
    delete_movie(file_name)
    send_message(chat_id, f"Deleted '{file_name}'.")
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {file_name}")

def handle_get_movie_link(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle generating a movie link."""
    if user_id != ADMIN_ID or not text or not text.startswith('/get_movie_link'):
        return

    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /get_movie_link Movie Name")
        return

    movie_name = parts[1]
    movies = load_movies()
    if movie_name in movies:
        safe_name = movie_name.replace(" ", "_")
        movie_link = f"https://t.me/{BOT_USERNAME}?start={safe_name}"
        send_message(chat_id, f"Click here to get the movie: {movie_link}")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {movie_name}")
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_start(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle user clicking the movie link."""
    if not text or not text.startswith('/start '):
        return

    movie_name = text.replace('/start ', '').replace('_', ' ')
    movies = load_movies()
    movie = movies.get(movie_name)

    if movie and 'file_id' in movie:
        send_file(chat_id, movie['file_id'])
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}")
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")