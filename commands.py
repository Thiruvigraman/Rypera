#commands.py

from typing import Dict, Any
from bot import send_message, send_file
from config import ADMIN_ID, BOT_USERNAME
from database import get_movie_by_name, get_all_movies, save_movie, update_movie_name, delete_movie, save_temp_file_id, get_temp_file_id, delete_temp_file_id, track_user
from utils import log_to_discord, is_spamming, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

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
        # Preserve underscores in movie name
        movie_name = command_args.strip()
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Processing deep link for movie: '{movie_name}' (raw: '{command_args}')")
        movie = get_movie_by_name(movie_name)
        if movie:
            send_file(chat_id, movie['file_id'], f"Found movie: {movie['name']}")
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[start] Sent movie '{movie['name']}' to chat {chat_id}")
        else:
            # Suggest similar movies
            movies = get_all_movies()
            similar = [m['name'] for m in movies if movie_name.lower() in m['name'].lower() or m['name'].lower() in movie_name.lower()]
            error_msg = f"❌ Movie '{movie_name}' not found."
            if similar:
                error_msg += f"\nDid you mean: {', '.join(similar)}?"
            error_msg += "\nUse /list_files to see available movies."
            send_message(chat_id, error_msg)
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Movie '{movie_name}' not found for chat {chat_id}")
    else:
        welcome_msg = (
            f"Welcome to {BOT_USERNAME}!\n"
            "This is a file-sharing bot.\n"
            "Use /help for commands."
        )
        send_message(chat_id, welcome_msg)
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[start] Sent welcome message to chat {chat_id}")

def help_command(message: Dict[str, Any]) -> None:
    """Handle /help command, showing different responses for admins and users."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[help] User {user_id} is spamming /help")
        return

    if user_id == ADMIN_ID:
        help_text = (
            f"Welcome to {BOT_USERNAME} Admin Commands!\n\n"
            "/start - Start the bot or access a movie via deep link\n"
            "/help - Show this message\n"
            "/addfile - Upload a movie file (admin only)\n"
            "/namefile <name> - Name the last uploaded file (admin only)\n"
            "/list_files - List all stored movies\n"
            "/getmovie <name> - Retrieve a movie by name\n"
            "/rename_file <old_name> <new_name> - Rename a movie (admin only)\n"
            "/delete_file <name> - Delete a movie (admin only)\n"
            "/announce <message> - Send a message to all users (admin only)\n"
            "/health - Check bot health (admin only)"
        )
    else:
        help_text = (
            f"Welcome to {BOT_USERNAME}!\n"
            "This is a file-sharing bot.\n\n"
            "/start - Start the bot\n"
            "/help - Show this message\n"
            "/list_files - List all movies\n"
            "/getmovie <name> - Retrieve a movie by name"
        )
    send_message(chat_id, help_text)
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[help] Sent help message to chat {chat_id} (admin: {user_id == ADMIN_ID})")

def handle_admin_upload(message: Dict[str, Any]) -> None:
    """Handle movie file uploads from admin."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can upload files.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_admin_upload] Unauthorized upload attempt by user {user_id}")
        return

    if 'document' not in message and 'video' not in message:
        send_message(chat_id, "Please upload a movie file.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_admin_upload] No file in message from chat {chat_id}")
        return

    file_id = message.get('document', message.get('video'))['file_id']
    save_temp_file_id(chat_id, file_id)
    send_message(chat_id, "File uploaded. Please provide a name using /namefile <name>.")
    log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[handle_admin_upload] Temp file {file_id} saved for chat {chat_id}")

def name_file(message: Dict[str, Any]) -> None:
    """Name the last uploaded file."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can name files.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[name_file] Unauthorized name attempt by user {user_id}")
        return

    file_id = get_temp_file_id(chat_id)
    if not file_id:
        send_message(chat_id, "No file uploaded. Please upload a file first using /addfile.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[name_file] No temp file for chat {chat_id}")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a name: /namefile <name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[name_file] No name provided for chat {chat_id}")
        return

    movie_name = command_args.strip()
    save_movie(file_id, movie_name, chat_id)
    delete_temp_file_id(chat_id)
    log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[name_file] Named file {file_id} as '{movie_name}' for chat {chat_id}")

def list_files(message: Dict[str, Any]) -> None:
    """List all stored movies."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[list_files] User {user_id} is spamming /list_files")
        return

    movies = get_all_movies()
    if not movies:
        send_message(chat_id, "No movies found.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] No movies for chat {chat_id}")
        return

    movie_list = "\n".join([f"- {movie['name']}" for movie in movies])
    send_message(chat_id, f"Available movies:\n{movie_list}")
    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"[list_files] Listed {len(movies)} movies for chat {chat_id}")

def get_movie(message: Dict[str, Any]) -> None:
    """Retrieve a movie by name."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if is_spamming(user_id, ADMIN_ID):
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie] User {user_id} is spamming /getmovie")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a movie name: /getmovie <name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie] No name provided for chat {chat_id}")
        return

    movie_name = command_args.strip()
    movie = get_movie_by_name(movie_name)
    if movie:
        send_file(chat_id, movie['file_id'], f"Found movie: {movie['name']}")
        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"[get_movie] Sent movie '{movie['name']}' to chat {chat_id}")
    else:
        send_message(chat_id, f"❌ Movie '{movie_name}' not found.\nUse /list_files to see available movies.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[get_movie] Movie '{movie_name}' not found for chat {chat_id}")

def rename_file(message: Dict[str, Any]) -> None:
    """Rename a movie."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can rename files.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Unauthorized rename attempt by user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=2)[1:] if len(message.get('text', '').split()) > 2 else []
    if len(command_args) != 2:
        send_message(chat_id, "Please provide old and new names: /rename_file <old_name> <new_name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Invalid args for chat {chat_id}")
        return

    old_name, new_name = command_args
    if update_movie_name(old_name, new_name):
        send_message(chat_id, f"Movie '{old_name}' renamed to '{new_name}'.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Renamed '{old_name}' to '{new_name}' for chat {chat_id}")
    else:
        send_message(chat_id, f"❌ Movie '{old_name}' not found.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[rename_file] Movie '{old_name}' not found for chat {chat_id}")

def delete_file(message: Dict[str, Any]) -> None:
    """Delete a movie."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can delete files.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Unauthorized delete attempt by user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a movie name: /delete_file <name>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] No name provided for chat {chat_id}")
        return

    movie_name = command_args.strip()
    if delete_movie(movie_name):
        send_message(chat_id, f"Movie '{movie_name}' deleted.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Deleted movie '{movie_name}' for chat {chat_id}")
    else:
        send_message(chat_id, f"❌ Movie '{movie_name}' not found.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[delete_file] Movie '{movie_name}' not found for chat {chat_id}")

def announce(message: Dict[str, Any]) -> None:
    """Send an announcement to all users."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can send announcements.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Unauthorized announce attempt by user {user_id}")
        return

    command_args = message.get('text', '').split(maxsplit=1)[1] if len(message.get('text', '').split()) > 1 else ''
    if not command_args:
        send_message(chat_id, "Please provide a message: /announce <message>")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] No message provided for chat {chat_id}")
        return

    from database import get_all_users
    users = get_all_users()
    announcement = command_args.strip()
    for user in users:
        user_chat_id = user['user_id']
        try:
            send_message(user_chat_id, f"📢 Announcement: {announcement}")
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Sent to user {user_chat_id}")
        except Exception as e:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Failed to send to user {user_chat_id}: {str(e)}", critical=True)
    send_message(chat_id, "Announcement sent to all users.")
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[announce] Sent announcement to {len(users)} users from chat {chat_id}")

def health_check(message: Dict[str, Any]) -> None:
    """Check bot health (admin only)."""
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    track_user(message['from'])

    if user_id != ADMIN_ID:
        send_message(chat_id, "❌ Only admins can check health.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Unauthorized health check by user {user_id}")
        return

    try:
        from database import client
        client.admin.command('ping')
        send_message(chat_id, "✅ Bot is healthy: MongoDB connection OK.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Bot is healthy for chat {chat_id}")
    except Exception as e:
        send_message(chat_id, f"❌ Bot is unhealthy: {str(e)}")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[health_check] Bot is unhealthy for chat {chat_id}: {str(e)}", critical=True)