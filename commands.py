# commands.py
from typing import Dict, Any, Optional
from threading import Lock  # For thread-safe operations
from bot import send_message, send_message_with_inline_keyboard
from config import ADMIN_ID, TEMP_FILE_IDS, BOT_USERNAME, FILE_SIZE_LIMIT
from database import save_movie, get_all_movies, update_movie_name, delete_movie, get_movie_by_name
from utils import log_to_discord, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

# Thread-safe lock for TEMP_FILE_IDS
temp_file_ids_lock = Lock()

def handle_admin_upload(chat_id: int, user_id: int, document: Optional[Dict[str, Any]], video: Optional[Dict[str, Any]]) -> None:
    """Handle file uploads from admin."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to upload files.")
        return
    
    file_id = None
    file_size = None

    # Extract file details
    if document and 'file_id' in document:
        file_id = document['file_id']
        file_size = document.get('file_size', 0)
    elif video and 'file_id' in video:
        file_id = video['file_id']
        file_size = video.get('file_size', 0)

    # Validate file size
    if file_size and file_size > FILE_SIZE_LIMIT:  # FILE_SIZE_LIMIT is now configurable
        send_message(chat_id, f"File too large. Max size is {FILE_SIZE_LIMIT / (1024 * 1024)} MB.")
        return

    if not file_id:
        send_message(chat_id, "No valid file found in the message.")
        return

    # Thread-safe update to TEMP_FILE_IDS
    with temp_file_ids_lock:
        TEMP_FILE_IDS[chat_id] = file_id

    send_message(chat_id, "Send the name of this movie to store it:")

def handle_admin_naming_movie(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle naming of uploaded movies."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to name movies.")
        return

    if not text:
        send_message(chat_id, "Movie name cannot be empty. Please provide a valid name.")
        return

    # Thread-safe access to TEMP_FILE_IDS
    with temp_file_ids_lock:
        file_id = TEMP_FILE_IDS.pop(chat_id, None)

    if not file_id:
        send_message(chat_id, "No file found to name. Please upload a file first.")
        return

    try:
        save_movie(file_id, text, chat_id)
        send_message(chat_id, f"Movie '{text}' stored successfully!")
    except Exception as e:
        send_message(chat_id, f"Failed to store movie. Error: {str(e)}")

def handle_list_files(chat_id: int, user_id: int) -> None:
    """List all stored movies."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to list files.")
        return

    try:
        movies = get_all_movies()
    except Exception as e:
        send_message(chat_id, f"Failed to fetch movies. Error: {str(e)}")
        return

    if not movies:
        send_message(chat_id, "No movies found.")
        return

    response = "Stored movies:\n" + "\n".join([f"- {movie['name']}" for movie in movies])
    send_message(chat_id, response)
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] Admin {user_id} listed movies.")

def handle_rename_file(chat_id: int, user_id: int, text: str) -> None:
    """Rename a movie."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to rename files.")
        return

    parts = text.split(maxsplit=2)
    if len(parts) != 3:
        send_message(chat_id, "Usage: /rename_file old_name new_name")
        return

    old_name, new_name = parts[1], parts[2]

    try:
        if update_movie_name(old_name, new_name):
            send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
        else:
            send_message(chat_id, f"Movie '{old_name}' not found.")
    except Exception as e:
        send_message(chat_id, f"Failed to rename movie. Error: {str(e)}")

def handle_delete_file(chat_id: int, user_id: int, text: str) -> None:
    """Delete a movie."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to delete files.")
        return

    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        send_message(chat_id, "Usage: /delete_file movie_name")
        return

    movie_name = parts[1]

    try:
        if delete_movie(movie_name):
            send_message(chat_id, f"Deleted '{movie_name}'.")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
    except Exception as e:
        send_message(chat_id, f"Failed to delete movie. Error: {str(e)}")

def handle_get_movie_link(chat_id: int, user_id: int, text: str) -> None:
    """Get movie file link."""
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        send_message(chat_id, "Usage: /get_movie_link movie_name")
        return

    movie_name = parts[1]

    try:
        movie = get_movie_by_name(movie_name)
        if movie:
            file_id = movie['file_id']
            send_message(chat_id, f"File ID for '{movie_name}': {file_id}")
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[get_movie_link] User {user_id} accessed '{movie_name}'.")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
    except Exception as e:
        send_message(chat_id, f"Failed to fetch movie link. Error: {str(e)}")

# Other functions like handle_start, handle_health, handle_help, handle_announce, and handle_announce_callback
# should also follow the same principles of error handling, validation, logging, and thread safety.