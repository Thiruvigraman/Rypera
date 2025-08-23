#handlers.py 

import time
import psutil
import os
from bot import send_message, send_file, send_announcement, cleanup_pending_files
from database import load_movies, save_movie, delete_movie, rename_movie, add_user, get_all_users, get_stats
from webhook import log_to_discord
from config import ADMIN_ID, BOT_USERNAME, DISCORD_WEBHOOK_STATUS, DISCORD_WEBHOOK_LIST_LOGS, DISCORD_WEBHOOK_FILE_ACCESS

def process_update(update):
    try:
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user_id = message.get('from', {}).get('id')
        display_name = message.get('from', {}).get('username', 'Unknown')

        # Add user to database
        add_user(user_id, display_name)

        if text:
            # Admin commands
            if str(user_id) == str(ADMIN_ID):
                if text.startswith('/list_files'):
                    movies = load_movies()
                    if not movies:
                        send_message(chat_id, "No movies found.")
                    else:
                        movie_list = "\n".join(sorted(movies.keys()))
                        # Handle Telegram 4096-character limit
                        max_length = 4000
                        if len(movie_list) > max_length:
                            parts = [movie_list[i:i + max_length] for i in range(0, len(movie_list), max_length)]
                            for part in parts:
                                send_message(chat_id, part)
                        else:
                            send_message(chat_id, movie_list)
                    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} listed files", log_type='admin', severity='info')

                elif text.startswith('/rename_file'):
                    parts = text.split(maxsplit=2)
                    if len(parts) != 3:
                        send_message(chat_id, "Usage: /rename_file <OldName> <NewName>")
                    else:
                        old_name, new_name = parts[1], parts[2]
                        if rename_movie(old_name, new_name):
                            send_message(chat_id, f"Renamed '{old_name}' to '{new_name}'")
                        else:
                            send_message(chat_id, f"Movie '{old_name}' not found")
                        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} renamed file '{old_name}' to '{new_name}'", log_type='admin', severity='info')

                elif text.startswith('/delete_file'):
                    parts = text.split(maxsplit=1)
                    if len(parts) != 2:
                        send_message(chat_id, "Usage: /delete_file <FileName>")
                    else:
                        name = parts[1]
                        movies = load_movies()
                        if name in movies:
                            delete_movie(name)
                            send_message(chat_id, f"Deleted '{name}'")
                        else:
                            send_message(chat_id, f"Movie '{name}' not found")
                        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} deleted file '{name}'", log_type='admin', severity='info')

                elif text.startswith('/get_movie_link'):
                    parts = text.split(maxsplit=1)
                    if len(parts) != 2:
                        send_message(chat_id, "Usage: /get_movie_link <Movie Name>")
                    else:
                        name = parts[1]
                        movies = load_movies()
                        if name in movies:
                            link = f"https://t.me/{BOT_USERNAME}?start={name}"
                            send_message(chat_id, f"Link for '{name}': {link}")
                        else:
                            send_message(chat_id, f"Movie '{name}' not found")
                        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} requested link for '{name}'", log_type='admin', severity='info')

                elif text == '/stats':
                    stats = get_stats()
                    response = f"Total movies: {stats['movie_count']}\nTotal users: {stats['user_count']}"
                    send_message(chat_id, response)
                    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} checked stats", log_type='admin', severity='info')

                elif text == '/health':
                    process = psutil.Process()
                    mem = process.memory_info().rss / 1024 / 1024  # MB
                    cpu = process.cpu_percent(interval=0.1)
                    uptime = time.time() - time.time()  # Adjust to use main.py's start_time
                    response = f"Status: Healthy\nUptime: {uptime:.2f} seconds\nMemory: {mem:.2f} MB\nCPU: {cpu:.2f}%"
                    send_message(chat_id, response)
                    log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} checked health: {response}", log_type='admin', severity='info')
                    if mem > 480:
                        log_to_discord(DISCORD_WEBHOOK_STATUS, "Memory usage exceeded 480 MB, restarting...", log_type='status', severity='warning')
                        os._exit(1)

                elif text.startswith('/announce'):
                    parts = text.split(maxsplit=1)
                    if len(parts) != 2:
                        send_message(chat_id, "Usage: /announce <Message>")
                    else:
                        message = parts[1]
                        users = get_all_users()
                        user_ids = [user['user_id'] for user in users]
                        success_count, failed_count = send_announcement(user_ids, message)
                        send_message(chat_id, f"Announcement sent to {success_count} users, failed for {failed_count} users")
                        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} sent announcement to {success_count} users", log_type='admin', severity='info')

                elif text == '/users':
                    users = get_all_users()
                    if not users:
                        send_message(chat_id, "No users found.")
                    else:
                        user_list = "\n".join([f"{user['user_id']}: {user['display_name']}" for user in users])
                        max_length = 4000
                        if len(user_list) > max_length:
                            parts = [user_list[i:i + max_length] for i in range(0, len(user_list), max_length)]
                            for part in parts:
                                send_message(chat_id, part)
                        else:
                            send_message(chat_id, user_list)
                        log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} listed users", log_type='admin', severity='info')

            # User commands
            if text.startswith('/start'):
                parts = text.split(maxsplit=1)
                if len(parts) == 2:
                    movie_name = parts[1]
                    movies = load_movies()
                    if movie_name in movies:
                        send_file(chat_id, movies[movie_name]['file_id'])
                        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"User {user_id} ({display_name}) accessed movie '{movie_name}'", log_type='file_access', severity='info')
                    else:
                        send_message(chat_id, f"Movie '{movie_name}' not found")
                        log_to_discord(DISCORD_WEBHOOK_FILE_ACCESS, f"User {user_id} ({display_name}) failed to access movie '{movie_name}'", log_type='file_access', severity='warning')
                else:
                    send_message(chat_id, "Welcome! Use /start <movie_name> to access a movie.")

        # Handle file uploads (admin only)
        if str(user_id) == str(ADMIN_ID):
            document = message.get('document') or message.get('video')
            if document:
                file_id = document.get('file_id')
                send_message(chat_id, "Please provide a name for this file.")
                # Store file_id temporarily (you may want to implement a temporary storage mechanism)
                # For simplicity, assume the next message is the name
                def handle_file_name(update):
                    name_message = update.get('message', {})
                    if name_message.get('chat', {}).get('id') == chat_id and name_message.get('from', {}).get('id') == user_id:
                        name = name_message.get('text')
                        if name:
                            save_movie(name, file_id)
                            send_message(chat_id, f"Saved file as '{name}'")
                            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} saved file as '{name}'", log_type='admin', severity='info')
                        else:
                            send_message(chat_id, "Invalid name provided")
                            log_to_discord(DISCORD_WEBHOOK_LIST_LOGS, f"Admin {user_id} provided invalid name for file", log_type='admin', severity='warning')
                # Register the next update to handle the file name (simplified, you may need a proper state machine)
                return handle_file_name

    except Exception as e:
        log_to_discord(DISCORD_WEBHOOK_STATUS, f"Error processing update: {str(e)}", log_type='status', severity='error')
        send_message(chat_id, f"Error: {str(e)}")