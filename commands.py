#commands.py
from typing import Dict, Any, Optional
from bot import send_message, send_message_with_inline_keyboard
from config import ADMIN_ID, TEMP_FILE_IDS, BOT_USERNAME
from database import save_movie, get_all_movies, update_movie_name, delete_movie, get_movie_by_name
from utils import log_to_discord, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

def handle_admin_upload(chat_id: int, user_id: int, document: Optional[Dict[str, Any]], video: Optional[Dict[str, Any]]) -> None:
    """Handle file uploads from admin."""
    if user_id != ADMIN_ID:
        return
    file_id = None
    file_size = None
    if document and 'file_id' in document:
        file_id = document['file_id']
        file_size = document.get('file_size', 0)
    elif video and 'file_id' in video:
        file_id = video['file_id']
        file_size = video.get('file_size', 0)
    if file_size and file_size > 50 * 1024 * 1024:  # 50 MB limit
        send_message(chat_id, "File too large. Max size is 50 MB.")
        return
    if file_id:
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
    else:
        send_message(chat_id, "No valid file found in the message.")

def handle_admin_naming_movie(chat_id: int, user_id: int, text: Optional[str]) -> None:
    """Handle naming of uploaded movies."""
    if user_id != ADMIN_ID or not text or chat_id not in TEMP_FILE_IDS:
        return
    file_id = TEMP_FILE_IDS.pop(chat_id, None)
    if file_id:
        save_movie(file_id, text, chat_id)
        send_message(chat_id, f"Movie '{text}' stored successfully!")
    else:
        send_message(chat_id, "No file found to name. Please upload a file first.")

def handle_list_files(chat_id: int, user_id: int) -> None:
    """List all stored movies."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to list files.")
        return
    movies = get_all_movies()
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
    if len(parts) < 3:
        send_message(chat_id, "Usage: /rename_file old_name new_name")
        return
    old_name, new_name = parts[1], parts[2]
    if update_movie_name(old_name, new_name):
        send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
    else:
        send_message(chat_id, f"Movie '{old_name}' not found.")

def handle_delete_file(chat_id: int, user_id: int, text: str) -> None:
    """Delete a movie."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to delete files.")
        return
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_file movie_name")
        return
    movie_name = parts[1]
    if delete_movie(movie_name):
        send_message(chat_id, f"Deleted '{movie_name}'.")
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_get_movie_link(chat_id: int, user_id: int, text: str) -> None:
    """Get movie file link."""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /get_movie_link movie_name")
        return
    movie_name = parts[1]
    movie = get_movie_by_name(movie_name)
    if movie:
        file_id = movie['file_id']
        send_message(chat_id, f"File ID for '{movie_name}': {file_id}")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[get_movie_link] User {user_id} accessed '{movie_name}'.")
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_start(chat_id: int, user_id: int, text: str) -> None:
    """Handle /start command with optional movie name."""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, f"Welcome to {BOT_USERNAME}! Use /help for commands.")
        return
    movie_name = parts[1]
    movie = get_movie_by_name(movie_name)
    if movie:
        file_id = movie['file_id']
        send_message(chat_id, f"File ID for '{movie_name}': {file_id}")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[start] User {user_id} accessed '{movie_name}' via /start.")
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_health(chat_id: int, user_id: int) -> None:
    """Check bot health."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to check health.")
        return
    try:
        from database import client
        client.admin.command('ping')
        send_message(chat_id, "Bot is healthy and connected to MongoDB.")
    except Exception as e:
        send_message(chat_id, f"Bot is unhealthy: {str(e)}")

def handle_help(chat_id: int, user_id: int) -> None:
    """Show help message."""
    if user_id != ADMIN_ID:
        response = (
            f"Welcome to {BOT_USERNAME}!\n"
            "Available commands:\n"
            "/start [movie_name] - Get a movie link\n"
            "/help - Show this help message"
        )
    else:
        response = (
            f"Welcome to {BOT_USERNAME} (Admin)!\n"
            "Admin commands:\n"
            "- Upload a file and send a name to store it\n"
            "/list_files - List all movies\n"
            "/rename_file old_name new_name - Rename a movie\n"
            "/delete_file movie_name - Delete a movie\n"
            "/get_movie_link movie_name - Get movie file ID\n"
            "/health - Check bot health\n"
            "/announce message - Announce to all users\n"
            "/help - Show this help message"
        )
    send_message(chat_id, response)

def handle_announce(chat_id: int, user_id: int, text: str) -> None:
    """Handle /announce command."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to announce.")
        return
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /announce message")
        return
    message = parts[1]
    keyboard = {
        "inline_keyboard": [
            [{"text": "Confirm", "callback_data": f"announce_confirm_{message}"}, {"text": "Cancel", "callback_data": "announce_cancel"}]
        ]
    }
    send_message_with_inline_keyboard(chat_id, f"Confirm announcement:\n{message}", keyboard)

def handle_announce_callback(chat_id: int, user_id: int, callback_data: str, callback_query: Dict[str, Any]) -> None:
    """Handle announcement callback."""
    if user_id != ADMIN_ID:
        send_message(chat_id, "You are not authorized to confirm announcements.")
        return
    from database import get_all_users
    if callback_data == "announce_cancel":
        send_message(chat_id, "Announcement cancelled.")
        return
    if callback_data.startswith("announce_confirm_"):
        message = callback_data[len("announce_confirm_"):]
        users = get_all_users()
        success_count = 0
        for user in users:
            user_id = user['user_id']
            try:
                send_message(user_id, f"Announcement: {message}")
                success_count += 1
            except Exception:
                continue
        send_message(chat_id, f"Announcement sent to {success_count} users.")
    else:
        send_message(chat_id, "Invalid callback data.")