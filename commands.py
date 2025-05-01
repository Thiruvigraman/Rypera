#commands.py
from typing import Optional, Dict, Any
from bot import send_message, send_file, answer_callback_query
from database import (
    load_movies, save_movie, delete_movie, rename_movie,
    get_all_users, track_user
)
from utils import log_to_discord, is_valid_movie_name
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

TEMP_FILE_IDS: Dict[int, str] = {}
PENDING_ANNOUNCEMENTS: Dict[int, str] = {}

def handle_admin_upload(chat_id: int, user_id: int, document: Optional[Dict[str, Any]], video: Optional[Dict[str, Any]]) -> None:
    if user_id != ADMIN_ID:
        return
    file_id = None
    if document and 'file_id' in document:
        file_id = document['file_id']
    elif video and 'file_id' in video:
        file_id = video['file_id']

    if file_id:
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
    else:
        send_message(chat_id, "No valid file found in the message.")

def handle_admin_naming_movie(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if user_id != ADMIN_ID or chat_id not in TEMP_FILE_IDS or not text:
        if chat_id in TEMP_FILE_IDS:
            del TEMP_FILE_IDS[chat_id]  # Clean up on invalid input
        return
    if not is_valid_movie_name(text):
        send_message(chat_id, "Invalid movie name. Use alphanumeric characters, spaces, underscores, or hyphens.")
        del TEMP_FILE_IDS[chat_id]
        return
    save_movie(text, TEMP_FILE_IDS[chat_id])
    send_message(chat_id, f"Movie '{text}' has been added.")
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}", critical=True)
    del TEMP_FILE_IDS[chat_id]

def handle_list_files(chat_id: int, user_id: int) -> None:
    if user_id != ADMIN_ID:
        return
    movies = load_movies()
    if not movies:
        send_message(chat_id, "No files stored.")
        return

    max_message_length = 4000
    message = "Stored Files:\n"
    current_length = len(message)
    messages = []

    for movie_name in sorted(movies.keys()):
        line = f"- {movie_name}\n"
        line_length = len(line)
        if current_length + line_length > max_message_length:
            messages.append(message)
            message = "Stored Files (continued):\n"
            current_length = len(message)
        message += line
        current_length += line_length

    if message:
        messages.append(message)

    for msg in messages:
        send_message(chat_id, msg)

def handle_rename_file(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if user_id != ADMIN_ID or not text or not text.startswith('/rename_file'):
        return
    parts = text.strip().split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "Usage: /rename_file OldName NewName")
        return
    _, old_name, new_name = parts
    if not is_valid_movie_name(new_name):
        send_message(chat_id, "Invalid new movie name. Use alphanumeric characters, spaces, underscores, or hyphens.")
        return
    if rename_movie(old_name, new_name):
        send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Renamed '{old_name}' to '{new_name}'", critical=True)
    else:
        send_message(chat_id, f"Movie '{old_name}' not found.")

def handle_delete_file(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if user_id != ADMIN_ID or not text or not text.startswith('/delete_file'):
        return
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_file FileName")
        return
    file_name = parts[1]
    if delete_movie(file_name):
        send_message(chat_id, f"Deleted '{file_name}'.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {file_name}", critical=True)
    else:
        send_message(chat_id, f"Movie '{file_name}' not found.")

def handle_get_movie_link(chat_id: int, user_id: int, text: Optional[str]) -> None:
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
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {movie_name}", critical=True)
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_start(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if not text or not text.startswith('/start '):
        return
    movie_name = text.replace('/start ', '').replace('_', ' ').strip().lower()
    movies = load_movies()
    movie = movies.get(movie_name)
    if movie and 'file_id' in movie:
        send_file(chat_id, movie['file_id'])
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}", critical=True)
    else:
        send_message(chat_id, f"Movie '{movie_name}' not found.")

def handle_health(chat_id: int, user_id: int) -> None:
    if user_id == ADMIN_ID:
        send_message(chat_id, "✅ Bot is up and database is connected.")

def handle_help(chat_id: int, user_id: int) -> None:
    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ This command is for admins only.")
        return

    help_text = (
        "*Admin Commands Help:*\n\n"
        "Here are all available admin commands:\n\n"
        "📋 /list_files - List all stored movies.\n"
        "✏️ /rename_file OldName NewName - Rename a movie.\n"
        "🗑️ /delete_file FileName - Delete a movie.\n"
        "🔗 /get_movie_link Movie Name - Generate a shareable link for a movie.\n"
        "📢 /announce Your Message - Send a message to all users (with preview).\n"
        "🩺 /health - Check bot and database status.\n"
        "❓ /help - Show this help message.\n\n"
        "*Upload Process:*\n"
        "- Send a video or document to upload.\n"
        "- Reply with the movie name to store it."
    )
    send_message(chat_id, help_text, parse_mode="Markdown")

def handle_announce(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ This command is for admins only.")
        return
    if not text or not text.startswith('/announce '):
        send_message(chat_id, "Usage: /announce Your message here")
        return

    message = text.replace('/announce ', '', 1).strip()
    if not message:
        send_message(chat_id, "Usage: /announce Your message here")
        return

    PENDING_ANNOUNCEMENTS[chat_id] = message
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Confirm", "callback_data": f"announce_confirm_{chat_id}"},
                {"text": "Cancel", "callback_data": f"announce_cancel_{chat_id}"}
            ]
        ]
    }
    preview_text = (
        f"*Announcement Preview:*\n\n"
        f"{message}\n\n"
        f"Press 'Confirm' to send to all users or 'Cancel' to discard."
    )
    send_message(chat_id, preview_text, parse_mode="Markdown", reply_markup=reply_markup)
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Announcement preview sent to admin: {message}", critical=True)

def handle_announce_callback(chat_id: int, user_id: int, callback_data: str, callback_query: Dict[str, Any]) -> None:
    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ This action is for admins only.")
        return

    action, target_chat_id = callback_data.split('_', 1)[0], int(callback_data.split('_')[-1])

    if target_chat_id != chat_id:
        send_message(chat_id, "❌ Invalid action.")
        return

    if chat_id not in PENDING_ANNOUNCEMENTS:
        send_message(chat_id, "❌ No pending announcement found.")
        return

    answer_callback_query(callback_query['id'])
    message = PENDING_ANNOUNCEMENTS[chat_id]

    if action == "confirm":
        user_ids = get_all_users()
        failed = 0
        for uid in user_ids:
            try:
                res = send_message(uid, f"📢 *Announcement:*\n\n{message}", parse_mode="Markdown")
                if not res.get('ok'):
                    failed += 1
            except Exception:
                failed += 1
        send_message(chat_id, f"Announcement sent. Failed to deliver to {failed} user(s).")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Announcement sent to {len(user_ids) - failed}/{len(user_ids)} users: {message}", critical=True)
    elif action == "cancel":
        send_message(chat_id, "Announcement cancelled.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Announcement cancelled by admin: {message}", critical=True)

    del PENDING_ANNOUNCEMENTS[chat_id]