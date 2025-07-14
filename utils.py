from database import get_pending_files, delete_sent_file_record
from telegram_bot import delete_messages
from discord_webhook import log_to_discord

def cleanup_pending_files():
    pending_files = get_pending_files(expiry_minutes=15)
    for file_data in pending_files:
        try:
            delete_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])
            log_to_discord(None, f"Cleaned up pending file in chat {file_data['chat_id']} on startup", log_type='status')
        except Exception as e:
            log_to_discord(None, f"Error cleaning up file in chat {file_data['chat_id']}: {e}", log_type='status')