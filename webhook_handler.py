#webhook_handler.py
from flask import request, jsonify
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS
from bot import send_message, send_file
from database import load_movies, save_movie, delete_movie, rename_movie
from utils import log_to_discord, is_spamming

TEMP_FILE_IDS = {}

def process_update(update):
    if 'message' not in update:
        return

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    document = message.get('document')
    video = message.get('video')

    if is_spamming(user_id):
        send_message(chat_id, "You're doing that too much. Please wait a few seconds.")
        return

    # Admin uploading a file
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin naming the movie
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]
        return

    # List movies
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    # Rename movie
    if text.startswith('/rename_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /rename_file OldName NewName")
        else:
            _, old_name, new_name = parts
            if rename_movie(old_name, new_name):
                send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Renamed '{old_name}' to '{new_name}'")
            else:
                send_message(chat_id, f"Movie '{old_name}' not found.")
        return

    # Delete movie
    if text.startswith('/delete_file') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /delete_file FileName")
        else:
            file_name = parts[1]
            delete_movie(file_name)
            send_message(chat_id, f"Deleted '{file_name}'.")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Deleted movie: {file_name}")
        return

    # Generate movie link
    if text.startswith('/get_movie_link') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /get_movie_link Movie Name")
            return
        movie_name = parts[1]
        movies = load_movies()
        if movie_name in movies:
            safe_name = movie_name.replace(" ", "_")
            link = f"https://t.me/{BOT_USERNAME}?start={safe_name}"
            send_message(chat_id, f"Click here to get the movie:\n{link}")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

    # User accessing via start link
    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies:
            send_file(chat_id, movies[movie_name]['file_id'])
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

def handle_webhook():
    from config import DISCORD_WEBHOOK_STATUS
    try:
        update = request.get_json()
        process_update(update)
        return jsonify(success=True)
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error: {e}")
        return jsonify({"error": str(e)}), 500