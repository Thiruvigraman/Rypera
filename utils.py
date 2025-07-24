#utils.py

from database import get_pending_files, delete_sent_file_record
from bot import delete_user_messages
from webhook import log_to_discord
from config import DISCORD_WEBHOOK_STATUS

def cleanup_pending_files():
    try:
        pending_files = get_pending_files(expiry_minutes=15)
        for file_data in pending_files:
            try:
                delete_user_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Cleaned up pending file in chat {file_data['chat_id']} on startup", log_type='status')
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error cleaning up file in chat {file_data['chat_id']}: {e}", log_type='status')
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error in cleanup_pending_files: {e}", log_type='status')