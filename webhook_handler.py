#webhook_handler.py

from flask import request, jsonify
from typing import Dict, Any
import json
from commands import start, help_command, handle_admin_upload, name_file, list_files, get_movie, rename_file, delete_file, announce, health_check
from config import ADMIN_ID, BOT_USERNAME
from utils import log_to_discord, DISCORD_WEBHOOK_STATUS

def process_update(update: Dict[str, Any]) -> None:
    """Process Telegram update."""
    if 'message' not in update:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] No message in update")
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '').strip()

    if not text:
        if 'document' in message or 'video' in message:
            handle_admin_upload(message)
        else:
            log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Non-text message from chat {chat_id}")
        return

    # Preserve underscores in command and args
    raw_text = text
    command_parts = text.split(maxsplit=1)
    command = command_parts[0].lower()
    args = command_parts[1] if len(command_parts) > 1 else ''
    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Processing command: {raw_text} for user {user_id}")

    command_map = {
        f'/{BOT_USERNAME.lower()}': start,
        f'/start@{BOT_USERNAME.lower()}': start,
        '/start': start,
        '/help': help_command,
        '/addfile': handle_admin_upload,
        '/namefile': name_file,
        '/list_files': list_files,
        '/getmovie': get_movie,
        '/rename_file': rename_file,
        '/delete_file': delete_file,
        '/announce': announce,
        '/health': health_check
    }

    handler = command_map.get(command)
    if handler:
        handler(message)
    else:
        from bot import send_message
        send_message(chat_id, "Unknown command. Use /help for available commands.")
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Unknown command '{command}' from chat {chat_id}")

def handle_webhook():
    """Handle incoming Telegram webhook requests."""
    try:
        update = request.get_json()
        if not update:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[handle_webhook] Empty update received", critical=True)
            return jsonify({"status": "ok"}), 200

        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_webhook] Received update: {json.dumps(update, indent=2)}", debug=True)
        process_update(update)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_webhook] Error: {str(e)}", critical=True)
        return jsonify({"error": str(e)}), 500