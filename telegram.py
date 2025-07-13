# telegram.py
import requests
import threading
from config import BOT_TOKEN

def send_message(chat_id, text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode
    response = requests.post(url, json=payload)
    return response.json()

def send_file(chat_id, file_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    response = requests.post(url, json=payload)
    message_data = response.json()

    if message_data.get('ok'):
        file_message_id = message_data['result']['message_id']

        warning_text = (
            "❗️ *IMPORTANT* ❗️\n\n"
            "This Video / File Will Be Deleted In *30 minutes* _(Due To Copyright Issues)_\n\n"
            "📌 *Please Forward This Video / File To Somewhere Else And Start Downloading There.*"
        )
        warning_response = send_message(chat_id, warning_text, parse_mode="Markdown")
        warning_message_id = warning_response['result']['message_id']

        threading.Timer(1800, delete_message, args=[chat_id, file_message_id]).start()
        threading.Timer(1800, delete_message, args=[chat_id, warning_message_id]).start()

def delete_message(chat_id, message_id):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage'
    payload = {'chat_id': chat_id, 'message_id': message_id}
    requests.post(url, json=payload)

def send_announcement(user_ids, message, parse_mode=None):
    """Send an announcement to all specified user IDs."""
    success_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            send_message(user_id, message, parse_mode)
            success_count += 1
        except Exception as e:
            failed_count += 1
            # Optionally log failed attempts to Discord (requires importing log_to_discord)
            # log_to_discord(DISCORD_WEBHOOK_STATUS, f"Failed to send announcement to {user_id}: {e}")
    return success_count, failed_count