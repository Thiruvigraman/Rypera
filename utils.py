#utils.py

from database import get_pending_files, delete_sent_file_record
from bot import delete_user_messages
from webhook import log_to_discord, log_to_betterstack
from config import DISCORD_WEBHOOK_STATUS

def cleanup_pending_files():
    try:
        pending_files = get_pending_files(expiry_minutes=15)
        for file_data in pending_files:
            try:
                delete_user_messages(file_data['chat_id'], file_data['file_message_id'], file_data['warning_message_id'])
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Cleaned up pending file in chat {file_data['chat_id']}", log_type='status', severity='info')
                log_to_betterstack("file_cleaned_up", {"chat_id": file_data['chat_id']})
            except Exception as e:
                log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error cleaning up file in chat {file_data['chat_id']}: {str(e)}", log_type='status', severity='error')
                log_to_betterstack("cleanup_error", {"chat_id": file_data['chat_id'], "error": str(e)})
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error in cleanup_pending_files: {str(e)}", log_type='status', severity='error')
        log_to_betterstack("cleanup_pending_files_error", {"error": str(e)})