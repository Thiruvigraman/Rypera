#commands.py

from typing import Dict, Any
from bot import send_message, send_file, delete_message
from config import ADMIN_ID, BOT_USERNAME
from database import get_movie_by_name, get_all_movies, save_movie, update_movie_name, delete_movie, save_temp_file_id, get_temp_file_id, delete_temp_file_id, track_user, get_all_users, schedule_message_deletion
from utils import log_to_discord, is_spamming, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def start(message: Dict[str, Any]) -> None:
    """Handle /start command, including deep links with movie names."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    track_user(message['from'])

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] User {user_id} is spamming /start")
        return

    if command_args:
        # Normalize movie name
        movie_name = " ".join(command_args.split())
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Processing deep link for movie: '{movie_name}' (raw: '{command_args}')")
        movie = get_movie_by_name(movie_name)
        if movie:
            # Send file with warning
            response = send_file(chat_id, movie['file_id'], f"Found movie: {escape_markdown_v2(movie['name'])}\n*IMPORTANT*: This file will be deleted in 30 minutes. Forward to somewhere and start downloading.")
            if response and 'result' in response:
                message_id = response['result']['message_id']
                # Schedule message deletion in user's chat after 30 minutes
                schedule_message_deletion(chat_id, message_id, movie['name'])
                log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[start] Sent movie '{movie['name']}' to chat {chat_id}, scheduled deletion for message {message_id}")
            else:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Failed to send movie '{movie['name']}' to chat {chat_id}", critical=True)
        else:
            error_msg = f"❌ Movie '{escape_markdown_v2(movie_name)}' not found.\nContact the admin for assistance."
            send_message(chat_id, error_msg)
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Movie '{movie_name}' not found for chat {chat_id}")
    else:
        welcome_msg = f"Welcome to {BOT_USERNAME}, I am a file-sharing bot."
        send_message(chat_id, welcome_msg)
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Sent welcome message to chat {chat_id}")

def help_command(message: Dict[str, Any]) -> None:
    """Handle /help command, showing all commands for admin only."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[help] Ignored non-admin request from user {user_id}")
        return

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[help] User {user_id} is spamming /help")
        return

    help_text = (
        f"Welcome to {BOT_USERNAME} Admin Commands!\n\n"
        "/start - Welcome message or access a movie via deep link\n"
        "/help - Show this list of commands\n"
        "/list_files - List all stored movies in MongoDB\n"
        "/get_movie_link <name> - Generate a shareable deep link for a movie\n"
        "/rename_file <old_name> <new_name> - Rename a stored movie\n"
        "/delete_file <name> - Delete a stored movie (with confirmation)\n"
        "/announce <message> - Send a message to all users\n"
        "/health - Check bot health (MongoDB, webhook, ping)"
    )
    send_message(chat_id, help_text)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[help] Sent help message to chat {chat_id}")

def list_files(message: Dict[str, Any]) -> None:
    """List all stored movies (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[list_files] Ignored non-admin request from user {user_id}")
        return

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[list_files] User {user_id} is spamming /list_files")
        return

    movies = get_all_movies()
    if not movies:
        send_message(chat_id, "No movies found.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] No movies for chat {chat_id}")
        return

    movie_list = "\n".join([f"- {escape_markdown_v2(movie['name'])}" for movie in movies])
    send_message(chat_id, f"Available movies:\n{movie_list}")
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] Listed {len(movies)} movies for chat {chat_id}")

def get_movie_link(message: Dict[str, Any]) -> None:
    """Generate a deep link for a movie (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_link] Ignored non-admin request from user {user_id}")
        return

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_link] User {user_id} is spamming /get_movie_link")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a movie name: /get_movie_link <name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_link] No name provided for chat {chat_id}")
        return

    movie_name = " ".join(command_args.split())
    movie = get_movie_by_name(movie_name)
    if movie:
        # Generate deep link with escaped underscores for URL
        url_safe_name = movie['name'].replace(' ', '_')
        deep_link = f"https://t.me/{BOT_USERNAME[1:]}?start={url_safe_name}"
        send_message(chat_id, f"Shareable link for '{escape_markdown_v2(movie['name'])}':\n{deep_link}")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[get_movie_link] Generated deep link for '{movie['name']}' for chat {chat_id}")
    else:
        send_message(chat_id, f"❌ Movie '{escape_markdown_v2(movie_name)}' not found.\nUse /list_files to see available movies.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie_link] Movie '{movie_name}' not found for chat {chat_id}")

def rename_file(message: Dict[str, Any]) -> None:
    """Rename a movie (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Ignored non-admin request from user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=2)[1:] if len(message.get('text', '').split()) > 2 else []
    if len(command_args) != 2:
        send_message(chat_id, "Please provide old and new names: /rename_file <old_name> <new_name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Invalid args for chat {chat_id}")
        return

    old_name, new_name = command_args
    old_name = " ".join(old_name.split())
    new_name = " ".join(new_name.split())
    if update_movie_name(old_name, new_name):
        send_message(chat_id, f"Movie '{escape_markdown_v2(old_name)}' renamed to '{escape_markdown_v2(new_name)}'.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Renamed '{old_name}' to '{new_name}' for chat {chat_id}")
    else:
        send_message(chat_id, f"❌ Movie '{escape_markdown_v2(old_name)}' not found.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Movie '{old_name}' not found for chat {chat_id}")

def delete_file(message: Dict[str, Any]) -> None:
    """Delete a movie with confirmation (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Ignored non-admin request from user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a movie name: /delete_file <name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] No name provided for chat {chat_id}")
        return

    movie_name = " ".join(command_args.split())
    movie = get_movie_by_name(movie_name)
    if not movie:
        send_message(chat_id, f"❌ Movie '{escape_markdown_v2(movie_name)}' not found.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Movie '{movie_name}' not found for chat {chat_id}")
        return

    # Create confirmation buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("OK", callback_data=f"delete_ok_{movie_name}"),
            InlineKeyboardButton("Cancel", callback_data=f"delete_cancel_{movie_name}")
        ]
    ])
    send_message(chat_id, f"Are you sure you want to delete '{escape_markdown_v2(movie_name)}'?", reply_markup=keyboard)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Sent confirmation for deleting '{movie_name}' to chat {chat_id}")

def handle_callback_query(query: Dict[str, Any]) -> None:
    """Handle callback queries from inline buttons."""
    chat_id = query['message']['chat']['id']
    user_id = query['from']['id']
    data = query['data']
    message_id = query['message']['message_id']

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_callback_query] Ignored non-admin callback from user {user_id}")
        return

    if data.startswith("delete_ok_"):
        movie_name = data[len("delete_ok_"):]
        if delete_movie(movie_name):
            send_message(chat_id, f"Movie '{escape_markdown_v2(movie_name)}' deleted.")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Deleted movie '{movie_name}' for chat {chat_id}")
        else:
            send_message(chat_id, f"❌ Failed to delete '{escape_markdown_v2(movie_name)}'.")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Failed to delete '{movie_name}' for chat {chat_id}", critical=True)
        # Delete the confirmation message
        delete_message(chat_id, message_id)
    elif data.startswith("delete_cancel_"):
        movie_name = data[len("delete_cancel_"):]
        send_message(chat_id, f"Deletion of '{escape_markdown_v2(movie_name)}' cancelled.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Cancelled deletion of '{movie_name}' for chat {chat_id}")
        delete_message(chat_id, message_id)

def announce(message: Dict[str, Any]) -> None:
    """Send an announcement to all users (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Ignored non-admin request from user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a message: /announce <message>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] No message provided for chat {chat_id}")
        return

    users = get_all_users()
    announcement = command_args.strip()
    for user in users:
        user_chat_id = user['user_id']
        try:
            send_message(user_chat_id, f"📢 Announcement: {announcement}")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Sent to user {user_chat_id}")
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Failed to send to user {user_chat_id}: {str(e)}", critical=True)
    send_message(chat_id, f"Announcement sent to {len(users)} users.")
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Sent announcement to {len(users)} users from chat {chat_id}")

def health_check(message: Dict[str, Any]) -> None:
    """Check bot health (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Ignored non-admin request from user {user_id}")
        return

    try:
        from database import client
        # Check MongoDB
        client.admin.command('ping')
        mongodb_status = "✅ MongoDB: Connected"
    except Exception as e:
        mongodb_status = f"❌ MongoDB: Failed ({str(e)})"

    # Check webhook
    from config import BOT_TOKEN
    import requests
    webhook_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo").json()
    webhook_status = "✅ Webhook: Set correctly" if webhook_info['result']['url'] else "❌ Webhook: Not set"

    # Ping task-health
    from config import APP_URL
    task_health = requests.get(f"{APP_URL}/task-health", timeout=10)
    task_status = "✅ Task Health: OK" if task_health.status_code == 200 else f"❌ Task Health: Failed ({task_health.status_code})"

    health_text = f"Bot Health Check:\n{mongodb_status}\n{webhook_status}\n{task_status}"
    send_message(chat_id, health_text)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Health check for chat {chat_id}: {health_text}")