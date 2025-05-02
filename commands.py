# commands.py

from typing import Dict, Any, Optional
from bot import send_message, send_message_with_inline_keyboard
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS
from database import (
    save_movie, get_all_movies, update_movie_name, delete_movie,
    get_movie_by_name, save_temp_file_id, get_temp_file_id, delete_temp_file_id
)
from utils import log_to_discord


def handle_admin_upload(chat_id: int, user_id: int, document: Optional[Dict[str, Any]], video: Optional[Dict[str, Any]]) -> None:
    if int(user_id) != int(ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_admin_upload] Unauthorized access by {user_id}")
        return

    file_id = (
        document['file_id'] if document and 'file_id' in document else
        video['file_id'] if video and 'file_id' in video else
        None
    )

    if file_id:
        save_temp_file_id(chat_id, file_id)
        send_message(chat_id, "✅ File received! Now send the movie name to store it.")
    else:
        send_message(chat_id, "⚠️ No valid file found. Please upload again.")


def handle_admin_naming_movie(chat_id: int, user_id: int, text: Optional[str]) -> None:
    if int(user_id) != int(ADMIN_ID) or not text:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_admin_naming_movie] Invalid request by {user_id}")
        return

    text = text.strip()
    if len(text) > 100:
        send_message(chat_id, "✋ Movie name too long. Keep it under 100 characters.")
        return
    if not text.isprintable():
        send_message(chat_id, "⚠️ Movie name contains invalid characters.")
        return

    file_id = get_temp_file_id(chat_id)
    if file_id:
        save_movie(file_id, text, chat_id)
        delete_temp_file_id(chat_id)
        send_message(chat_id, f"🎬 Movie '{text}' stored successfully!")
    else:
        send_message(chat_id, "❌ No file found to name. Please upload a file first.")


def handle_list_files(chat_id: int, user_id: int) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized.")
        return

    movies = get_all_movies()
    if not movies:
        send_message(chat_id, "📂 No movies found.")
        return

    response = "🎞️ Stored movies:\n" + "\n".join([f"• {movie['name']}" for movie in movies])
    send_message(chat_id, response)
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] Admin {user_id} listed movies.")


def handle_rename_file(chat_id: int, user_id: int, text: str) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized.")
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "Usage: /rename_file old_name new_name")
        return

    old_name, new_name = parts[1], parts[2]
    if len(new_name) > 100 or not new_name.isprintable():
        send_message(chat_id, "⚠️ New movie name is invalid or too long.")
        return

    if update_movie_name(old_name, new_name):
        send_message(chat_id, f"✏️ Renamed '{old_name}' to '{new_name}'.")
    else:
        send_message(chat_id, f"❌ Movie '{old_name}' not found.")


def handle_delete_file(chat_id: int, user_id: int, text: str) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized.")
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /delete_file movie_name")
        return

    movie_name = parts[1]
    if delete_movie(movie_name):
        send_message(chat_id, f"🗑️ Deleted '{movie_name}'.")
    else:
        send_message(chat_id, f"❌ Movie '{movie_name}' not found.")


def handle_get_movie_link(chat_id: int, user_id: int, text: str) -> None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /get_movie_link movie_name")
        return

    movie_name = parts[1]
    movie = get_movie_by_name(movie_name)
    if movie:
        file_id = movie['file_id']
        send_message(chat_id, f"🔗 File ID for '{movie_name}': `{file_id}`")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[get_movie_link] User {user_id} accessed '{movie_name}'.")
    else:
        send_message(chat_id, f"❌ Movie '{movie_name}' not found.")


def handle_start(chat_id: int, user_id: int, text: str) -> None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, f"👋 Welcome to {BOT_USERNAME}!.")
        return

    movie_name = parts[1]
    movie = get_movie_by_name(movie_name)
    if movie:
        file_id = movie['file_id']
        send_message(chat_id, f"📦 File ID for '{movie_name}': `{file_id}`")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[start] User {user_id} accessed '{movie_name}' via /start.")
    else:
        send_message(chat_id, f"❌ Movie '{movie_name}' not found.")


def handle_health(chat_id: int, user_id: int) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized.")
        return

    try:
        from database import client
        client.admin.command('ping')
        send_message(chat_id, "✅ Bot is healthy and connected to MongoDB.")
    except Exception as e:
        send_message(chat_id, f"❌ Bot is unhealthy: {str(e)}")


def handle_help(chat_id: int, user_id: int) -> None:
    if int(user_id) != int(ADMIN_ID):
        response = (
            f"🤖 Welcome to {BOT_USERNAME}!\n"
            "Use links shared in the channel to access files."
        )
    else:
        response = (
            f"🤖 Welcome to {BOT_USERNAME} (Admin)!\n\n"
            "🛠️ Admin Commands:\n"
            "📥 Upload a file and send a name to store it\n"
            "📃 /list_files - List all movies\n"
            "✏️ /rename_file old_name new_name - Rename a movie\n"
            "🗑️ /delete_file movie_name - Delete a movie\n"
            "🔗 /get_movie_link movie_name - Get movie file ID\n"
            "❤️ /health - Check bot health\n"
            "📢 /announce message - Announce to all users"
        )
    send_message(chat_id, response)


def handle_announce(chat_id: int, user_id: int, text: str) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized.")
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_message(chat_id, "Usage: /announce message")
        return

    message = parts[1]
    if len(f"announce_confirm_{message}") > 64:
        send_message(chat_id, "⚠️ Message too long. Keep it under 50 characters.")
        return

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm", "callback_data": f"announce_confirm_{message}"},
                {"text": "❌ Cancel", "callback_data": "announce_cancel"}
            ]
        ]
    }
    send_message_with_inline_keyboard(chat_id, f"📢 Confirm announcement:\n{message}", keyboard)


def handle_announce_callback(chat_id: int, user_id: int, callback_data: str, callback_query: Dict[str, Any]) -> None:
    if int(user_id) != int(ADMIN_ID):
        send_message(chat_id, "❌ You are not authorized to confirm announcements.")
        return

    from database import get_all_users

    if callback_data == "announce_cancel":
        send_message(chat_id, "❌ Announcement cancelled.")
        return

    if callback_data.startswith("announce_confirm_"):
        message = callback_data[len("announce_confirm_"):]
        users = get_all_users()
        success_count = 0

        for user in users:
            try:
                if send_message(user['user_id'], f"📢 Announcement:\n{message}"):
                    success_count += 1
            except Exception:
                continue

        send_message(chat_id, f"✅ Announcement sent to {success_count} users.")
    else:
        send_message(chat_id, "⚠️ Invalid callback data.")