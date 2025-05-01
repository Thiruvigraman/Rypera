# webhook_handler.py
from flask import request, jsonify
from typing import Dict, Any, Optional
from commands import (
    handle_admin_upload,
    handle_admin_naming_movie,
    handle_list_files,
    handle_rename_file,
    handle_delete_file,
    handle_get_movie_link,
    handle_start
)
from utils import log_to_discord, is_spamming
from bot import send_message
from config import DISCORD_WEBHOOK_STATUS

def process_update(update: Dict[str, Any]) -> None:
    """Process Telegram update."""
    message = update.get('message')
    if not message:
        return

    chat = message.get('chat')
    user = message.get('from')

    if not chat or not user:
        log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] Missing chat or user info.")
        return

    chat_id = chat.get('id')
    user_id = user.get('id')
    text: Optional[str] = message.get('text')
    document = message.get('document')
    video = message.get('video')

    if not isinstance(chat_id, int) or not isinstance(user_id, int):
        log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] Invalid chat_id or user_id.")
        return

    if is_spamming(user_id):
        send_message(chat_id, "You're doing that too much. Please wait a few seconds.")
        return

    # Command Dispatch
    handle_admin_upload(chat_id, user_id, document, video)
    handle_admin_naming_movie(chat_id, user_id, text)

    if text == '/list_files':
        handle_list_files(chat_id, user_id)
    elif text and text.startswith('/rename_file'):
        handle_rename_file(chat_id, user_id, text)
    elif text and text.startswith('/delete_file'):
        handle_delete_file(chat_id, user_id, text)
    elif text and text.startswith('/get_movie_link'):
        handle_get_movie_link(chat_id, user_id, text)
    elif text and text.startswith('/start '):
        handle_start(chat_id, user_id, text)

def handle_webhook():
    """Flask webhook handler for Telegram bot."""
    try:
        update = request.get_json(force=True)
        if not update:
            return jsonify({"error": "Empty payload"}), 400

        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_webhook] Exception: {e}")
        return jsonify({"error": str(e)}), 500