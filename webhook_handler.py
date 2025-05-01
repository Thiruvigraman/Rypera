# webhook_handler.py

from flask import request, jsonify
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

TEMP_FILE_IDS = {}
USER_COOLDOWNS = {}

def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    if is_spamming(user_id):
        send_message(chat_id, "You're doing that too much. Please wait a few seconds.")
        return

    # Admin uploading file
    handle_admin_upload(chat_id, user_id, document, video)

    # Admin naming movie
    handle_admin_naming_movie(chat_id, user_id, text)

    # List files
    if text == '/list_files':
        handle_list_files(chat_id, user_id)

    # Rename file
    handle_rename_file(chat_id, user_id, text)

    # Delete file
    handle_delete_file(chat_id, user_id, text)

    # Generate movie link
    handle_get_movie_link(chat_id, user_id, text)

    # User clicking movie link
    handle_start(chat_id, user_id, text)

def handle_webhook():
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500