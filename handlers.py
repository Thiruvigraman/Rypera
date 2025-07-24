#handlers.py

from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS
from database import load_movies, save_movie, delete_movie, rename_movie, add_user, get_all_users, get_stats, db
from bot import send_message, send_file, send_announcement
from webhook import log_to_discord
import time
import psutil
import traceback

TEMP_FILE_IDS = {}

def get_user_display_name(user):
    username = user.get('username')
    if username:
        return f"@{username}"
    first_name = user.get('first_name', '')
    last_name = user.get('last_name', '')
    return f"{first_name} {last_name}".strip() or "Unknown User"

def process_update(update):
    try:
        if 'message' not in update:
            return

        chat_id = update['message']['chat']['id']
        user_id = update['message']['from']['id']
        user = update['message']['from']
        text = update['message'].get('text', '')
        document = update['message'].get('document')
        video = update['message'].get('video')

        if user_id != ADMIN_ID:
            display_name = get_user_display_name(user)
            add_user(user_id, display_name)

        if (document or video) and user_id == ADMIN_ID:
            file_id = document['file_id'] if document else video['file_id']
            TEMP_FILE_IDS[chat_id] = file_id
            send_message(chat_id, "Send the name of this movie to store it:")
            return

        if user_id == ADMIN_ID and chat_id in TEMP_FILE_IDS and text:
            save_movie(text, TEMP_FILE_IDS[chat_id])
            send_message(chat_id, f"Movie '{text}' has been added.")
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Movie added: {text}", log_type='list_logs')
            del TEMP_FILE_IDS[chat_id]
            return

        if text == '/list_files' and user_id == ADMIN_ID:
            movies = load_movies()
            msg = "Stored Files:\n" + "\n".join(movies.keys()) if movies else "No files stored."
            send_message(chat_id, msg)
            return

        if text.startswith('/rename_file') and user_id == ADMIN_ID:
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                send_message(chat_id, "Usage: /rename_file OldName NewName")
            else:
                _, old_name, new_name = parts
                if rename_movie(old_name, new_name):
                    send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'.")
                    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Renamed '{old_name}' to '{new_name}'", log_type='list_logs')
                else:
                    send_message(chat_id, f"Movie '{old_name}' not found.")
            return

        if text.startswith('/delete_file') and user_id == ADMIN_ID:
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                send_message(chat_id, "Usage: /delete_file FileName")
            else:
                file_name = parts[1]
                delete_movie(file_name)
                send_message(chat_id, f"Deleted '{file_name}'.")
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Deleted movie: {file_name}", log_type='list_logs')
            return

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
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Generated link for: {movie_name}", log_type='list_logs')
            else:
                send_message(chat_id, f"Movie '{movie_name}' not found.")
            return

        if text == '/stats' and user_id == ADMIN_ID:
            stats = get_stats()
            msg = f"📊 Bot Statistics:\nTotal Movies: {stats['movie_count']}\nTotal Users: {stats['user_count']}"
            send_message(chat_id, msg)
            return

        if text == '/health' and user_id == ADMIN_ID:
            try:
                process = psutil.Process()
                mem = process.memory_info().rss / 1024 / 1024  # MB
                cpu = process.cpu_percent(interval=0.1)
                process_start_time = process.create_time()
                uptime = time.time() - process_start_time
                # Format uptime: show days if > 24 hours, else hours
                if uptime >= 86400:  # 24 hours in seconds
                    days = int(uptime // 86400)
                    hours = int((uptime % 86400) // 3600)
                    minutes = int((uptime % 3600) // 60)
                    seconds = int(uptime % 60)
                    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
                else:
                    hours = int(uptime // 3600)
                    minutes = int((uptime % 3600) // 60)
                    seconds = int(uptime % 60)
                    uptime_str = f"{hours}h {minutes}m {seconds}s"
                # Get MongoDB storage stats
                db_stats = db.command("dbStats")
                storage_used_mb = db_stats.get('dataSize', 0) / 1024 / 1024  # Convert bytes to MB
                storage_total_mb = 512  # MongoDB Atlas M0 limit
                msg = (
                    f"🩺 *Bot Health Check*\n\n"
                    f"*Uptime*: {uptime_str}\n"
                    f"*Memory Usage*: {mem:.2f} MB\n"
                    f"*CPU Usage*: {cpu:.2f}%\n"
                    f"*MongoDB Storage Used*: {storage_used_mb:.2f} MB\n"
                    f"*MongoDB Storage Total*: {storage_total_mb:.2f} MB"
                )
                send_message(chat_id, msg, parse_mode="Markdown")
                log_to_discord(
                    DISCORD_WEBHOOK_LIST_LOGS,
                    f"Attempting to log: Admin requested health check: Uptime {uptime_str}, Memory {mem:.2f} MB, CPU {cpu:.2f}%, MongoDB Storage {storage_used_mb:.2f}/{storage_total_mb:.2f} MB",
                    log_type='list_logs'
                )
            except Exception as e:
                send_message(chat_id, f"Error checking health: {e}")
                log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Health check error: {e}\n{traceback.format_exc()}", log_type='list_logs')
            return

        if text == '/users' and user_id == ADMIN_ID:
            try:
                users = get_all_users()
                if not users:
                    send_message(chat_id, "No users found in the database.")
                    return
                user_list = "\n".join([f"ID: {user['user_id']} - Name: {user['display_name']}" for user in users])
                msg = f"📋 *Registered Users*:\n\n{user_list}"
                send_message(chat_id, msg, parse_mode="Markdown")
                log_to_discord(
                    DISCORD_WEBHOOK_LIST_LOGS,
                    f"Attempting to log: Admin requested user list, found {len(users)} users",
                    log_type='list_logs'
                )
            except Exception as e:
                send_message(chat_id, f"Error retrieving users: {e}")
                log_to_discord(
                    DISCORD_WEBHOOK_LIST_LOGS,
                    f"Attempting to log: Error retrieving user list: {e}\n{traceback.format_exc()}",
                    log_type='list_logs'
                )
            return

        if text.startswith('/announce') and user_id == ADMIN_ID:
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                send_message(chat_id, "Usage: /announce Your announcement message")
                return
            announcement = parts[1]
            users = get_all_users()
            if not users:
                send_message(chat_id, "No users to announce to.")
                return
            user_ids = [user['user_id'] for user in users]
            success_count, failed_count = send_announcement(user_ids, announcement, parse_mode="Markdown")
            send_message(
                chat_id,
                f"📢 Announcement sent!\nSuccess: {success_count} users\nFailed: {failed_count} users",
            )
            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Attempting to log: Announcement sent to {success_count} users, failed for {failed_count} users", log_type='list_logs')
            return

        if text.startswith('/start '):
            movie_name = text.replace('/start ', '').replace('_', ' ')
            movies = load_movies()
            if movie_name in movies and 'file_id' in movies[movie_name]:
                display_name = get_user_display_name(user)
                send_file(chat_id, movies[movie_name]['file_id'])
                log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"Attempting to log: {display_name} (ID: {user_id}) accessed movie: {movie_name}", log_type='file_access')
            else:
                send_message(chat_id, f"Movie '{movie_name}' not found.")
            return
    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Attempting to log: Error in process_update: {e}\n{traceback.format_exc()}", log_type='status')
        raise  # Re-raise to trigger 500 error logging in main.py