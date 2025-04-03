import json
import re
import threading
from flask import Flask
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = "YOUR_BOT_TOKEN"
PRIVATE_CHANNEL_ID = -1002553617087  
# private channel ID
PUBLIC_CHANNEL_ID = --1002660015956  
# main channel ID

app = Flask(__name__)
bot = Bot(token=TOKEN)

# Load stored movies
def load_movies():
    try:
        with open("storage.json", "r") as f:
            return json.load(f)
    except:
        return {}

movies = load_movies()

def save_movies():
    with open("storage.json", "w") as f:
        json.dump(movies, f)

# Extract movie name from the forwarded message caption
def extract_movie_name(text):
    if text:
        pattern = r"^(.*?)\s*\|"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else text.strip()
    return None

# Detect and store forwarded movie uploads
def detect_movie_upload(update: Update, context: CallbackContext):
    if update.message.forward_from_chat and update.message.forward_from_chat.id == PRIVATE_CHANNEL_ID:
        message_id = update.message.message_id
        movie_name = extract_movie_name(update.message.caption)

        if movie_name:
            movies[movie_name] = message_id
            save_movies()
            update.message.reply_text(f"✅ Movie '{movie_name}' stored with ID {message_id}")
        else:
            update.message.reply_text("❌ Please add a caption with the movie name before forwarding.")

# Webhook endpoint for Render
@app.route('/')
def home():
    return "Bot is running!"

# Run the bot
def run_bot():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.forwarded & (Filters.video | Filters.document), detect_movie_upload))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8080)