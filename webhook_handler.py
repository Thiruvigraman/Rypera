
#webhook_handler.py
from typing import Dict, Any
from config import ADMIN_ID
from commands import start, help_command, list_files, get_movie_link, rename_file, delete_file, announce, health_check, handle_callback_query
from bot import send_message
from utils import log_to_discord, DISCORD_WEBHOOK_STATUS

def handle_webhook_update(update: Dict[str, Any]) -> None:
    """Handle incoming Telegram webhook updates."""
    try:
        if 'message' in update:
            message = update['message']
            if 'text' in message and message['text'].startswith('/'):
                command = message['text'].split()[0].lower()
                user_id = message['from']['id']

                # Always handle /start (for all users)
                if command == '/start':
                    start(message)
                    return

                # Ignore non-admin commands (except /start)
                if user_id != ADMIN_ID:
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[webhook_handler] Ignored non-admin command '{command}' from user {user_id}")
                    return

                # Admin commands
                if command == '/help':
                    help_command(message)
                elif command == '/list_files':
                    list_files(message)
                elif command == '/get_movie_link':
                    get_movie_link(message)
                elif command == '/rename_file':
                    rename_file(message)
                elif command == '/delete_file':
                    delete_file(message)
                elif command == '/announce':
                    announce(message)
                elif command == '/health':
                    health_check(message)
                else:
                    send_message(message['chat']['id'], "Unknown command. Use /help for available commands.")
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[webhook_handler] Unknown command '{command}' from chat {message['chat']['id']}")
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[webhook_handler] Error: {str(e)}", critical=True)