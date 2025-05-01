#webhook_handler.py
from flask import request, jsonify
from typing import Dict, Any, Optional
from config import ADMIN_ID, DISCORD_WEBHOOK_STATUS
from commands import (
    handle_admin_upload,
    handle_admin_naming_movie,
    handle_list_files,
    handle_rename_file,
    handle_delete_file,
    handle_get_movie_link,
    handle_start,
    handle_health,
    handle_help,
    handle_announce,
    handle_announce_callback
)
from utils import log_to_discord, is_spamming
from bot import send_message
from database import track_user

def process_update(update: Dict[str, Any]) -> None:
    """Process Telegram update."""
    try:
        callback_query = update.get('callback_query')
        if callback_query:
            user = callback_query.get('from')
            chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
            user_id = user.get('id')
            callback_data = callback_query.get('data')

            if not chat_id or not user_id or not callback_data:
                log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] Missing callback query info.", critical=True)
                return

            if callback_data.startswith('announce_'):
                if not callback_data.startswith(('announce_confirm_', 'announce_cancel_')):
                    log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Invalid callback_data: {callback_data}", critical=True)
                    return
                handle_announce_callback(chat_id, user_id, callback_data, callback_query)
            return

        message = update.get('message')
        if not message:
            return

        chat = message.get('chat')
        user = message.get('from')

        if not chat or not user:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] Missing chat or user info.", critical=True)
            return

        chat_id = chat.get('id')
        user_id = user.get('id')
        text: Optional[str] = message.get('text')
        document = message.get('document')
        video = message.get('video')

        if not isinstance(chat_id, int) or not isinstance(user_id, int):
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[process_update] Invalid chat_id or user_id.", critical=True)
            return

        if user_id != ADMIN_ID and is_spamming(user_id):
            send_message(chat_id, "You're doing that too much. Please wait a few seconds.")
            return

        track_user(user_id)
        handle_admin_upload(chat_id, user_id, document, video)
        handle_admin_naming_movie(chat_id, user_id, text)

        if text:
            text = text.strip().lower()
            if text == '/list_files':
                handle_list_files(chat_id, user_id)
            elif text.startswith('/rename_file'):
                handle_rename_file(chat_id, user_id, text)
            elif text.startswith('/delete_file'):
                handle_delete_file(chat_id, user_id, text)
            elif text.startswith('/get_movie_link'):
                handle_get_movie_link(chat_id, user_id, text)
            elif text.startswith('/start '):
                handle_start(chat_id, user_id, text)
            elif text == '/health':
                handle_health(chat_id, user_id)
            elif text == '/help':
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Handling /help command for user {user_id}", critical=True)
                handle_help(chat_id, user_id)
            elif text.startswith('/announce '):
                handle_announce(chat_id, user_id, text)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[process_update] Exception: {str(e)}\n{traceback.format_exc()}", critical=True)

def handle_webhook():
    """Flask webhook handler for Telegram bot."""
    try:
        update = request.get_json(force=True)
        if not update:
            log_to_discord(DISCORD_WEBHOOK_STATUS, "[handle_webhook] Empty payload received.", critical=True)
            return jsonify({"error": "Empty payload"}), 400
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"[handle_webhook] Exception: {e}", critical=True)
        return jsonify({"error": str(e)}), 500