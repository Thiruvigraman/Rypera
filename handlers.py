# handlers.py
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS
from database import load_movies, save_movie, delete_movie, rename_movie, add_user, get_all_users, get_stats
from telegram import send_message, send_file, send_announcement
from discord import log_to_discord

TEMP_FILE_IDS = {}

def process_update(update):
    if 'message' not in update:
        return

    chat_id = update['message']['chat']['id']
    user_id = update['message']['from']['id']
    text = update['message'].get('text', '')
    document = update['message'].get('document')
    video = update['message'].get('video')

    # Store user ID for any interaction (except admin)
    if user_id != ADMIN_ID:
        add_user(user_id)

    # Admin uploading file
    if (document or video) and user_id == ADMIN_ID:
        file_id = document['file_id'] if document else video['file_id']
        TEMP_FILE_IDS[chat_id] = file_id
        send_message(chat_id, "Send the name of this movie to store it:")
        return

    # Admin naming movie
    if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
        save_movie(text, TEMP_FILE_IDS[chat_id])
        send_message(chat_id, f"Movie '{text}' has been added.")
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Movie added: {text}")
        del TEMP_FILE_IDS[chat_id]
        return

    # List files
    if text == '/list_files' and user_id == ADMIN_ID:
        movies = load_movies()
        msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
        send_message(chat_id, msg)
        return

    # Rename file
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

    # Delete file
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
            movie_link = f"https://t.me/{BOT_USERNAME}?start={safe_name}"
            send_message(chat_id, f"Click here to get the movie: {movie_link}")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Generated link for: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return

    # Stats command
    if text == '/stats' and user_id == ADMIN_ID:
        stats = get_stats()
        msg = f"📊 Bot Statistics:\nTotal Movies: {stats['movie_count']}\nTotal Users: {stats['user_count']}"
        send_message(chat_id, msg)
        return

    # Announce command
    if text.startswith('/announce') and user_id == ADMIN_ID:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /announce Your announcement message")
            return
        announcement = parts[1]
        user_ids = get_all_users()
        if not user_ids:
            send_message(chat_id, "No users to announce to.")
            return
        success_count, failed_count = send_announcement(user_ids, announcement, parse_mode="Markdown")
        send_message(
            chat_id,
            f"📢 Announcement sent!\nSuccess: {success_count} users\nFailed: {failed_count} users",
        )
        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Announcement sent to {success_count} users, failed for {failed_count} users")
        return

    # User clicking movie link
    if text.startswith('/start '):
        movie_name = text.replace('/start ', '').replace('_', ' ')
        movies = load_movies()
        if movie_name in movies and 'file_id' in movies[movie_name]:
            send_file(chat_id, movies[movie_name]['file_id'])
            log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"{user_id} accessed movie: {movie_name}")
        else:
            send_message(chat_id, f"Movie '{movie_name}' not found.")
        return