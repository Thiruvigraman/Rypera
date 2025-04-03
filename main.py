import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# 🔹 Load or Create Movie Storage File
STORAGE_FILE = "storage.json"
if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "w") as f:
        json.dump({}, f)

# 🔹 Load Movie Data from File
def load_movies():
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def save_movies(movies):
    with open(STORAGE_FILE, "w") as f:
        json.dump(movies, f, indent=4)

movies = load_movies()

# 🔹 Your Telegram Bot Token & Admin ID
TOKEN = "YOUR_BOT_TOKEN"  # bot token
ADMIN_ID = 6778132055  # Admin ID

# 🔹 Start Command (Users can fetch movies)
def start(update: Update, context: CallbackContext):
    args = context.args
    if args:
        movie_name = " ".join(args).replace("_", " ")
        if movie_name in movies:
            update.message.reply_document(document=movies[movie_name])
            return
    update.message.reply_text("Welcome! Send me a movie name to get the file.")

# 🔹 Store Movie File (Admin Only)
def store_movie(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 You are not allowed to store movies.")
        return

    if update.message.document or update.message.video:
        file = update.message.document or update.message.video
        file_id = file.file_id
        file_name = file.file_name or "Unknown File"

        movies[file_name] = file_id
        save_movies(movies)

        update.message.reply_text(f"✅ Movie **{file_name}** stored successfully!")
    else:
        update.message.reply_text("❌ Please send a movie file.")

# 🔹 Get Movie Link (Admin Only)
def get_movie_link(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 You are not allowed to use this command.")
        return

    if len(context.args) == 0:
        update.message.reply_text("Usage: /getlink <Movie Name>")
        return

    movie_name = " ".join(context.args)
    if movie_name in movies:
        bot_username = context.bot.username
        movie_link = f"https://t.me/{bot_username}?start={movie_name.replace(' ', '_')}"
        update.message.reply_text(f"🎬 **Share this link:**\n\n[{movie_name}]({movie_link})", parse_mode="Markdown")
    else:
        update.message.reply_text("❌ Movie not found.")

# 🔹 Delete Movie (Admin Only)
def delete_movie(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 You are not allowed to delete movies.")
        return

    if len(context.args) == 0:
        update.message.reply_text("Usage: /delete <Movie Name>")
        return

    movie_name = " ".join(context.args)
    if movie_name in movies:
        del movies[movie_name]
        save_movies(movies)
        update.message.reply_text(f"🗑️ Movie **{movie_name}** deleted successfully!")
    else:
        update.message.reply_text("❌ Movie not found.")

# 🔹 List All Movies (Admin Only)
def list_movies(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("🚫 You are not allowed to use this command.")
        return

    if not movies:
        update.message.reply_text("📂 No movies stored.")
        return

    movie_list = "\n".join(movies.keys())
    update.message.reply_text(f"🎞 **Stored Movies:**\n\n{movie_list}")

# 🔹 Set Up the Bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_args=True))
    dp.add_handler(MessageHandler(Filters.document | Filters.video, store_movie))
    dp.add_handler(CommandHandler("getlink", get_movie_link, pass_args=True))
    dp.add_handler(CommandHandler("delete", delete_movie, pass_args=True))
    dp.add_handler(CommandHandler("listmovies", list_movies))  # ✅ Shows all stored movies

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()