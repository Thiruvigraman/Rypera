import requests

BOT_TOKEN = "8169755402:AAGJoZ_8yXhp02uq2bI5qVytY-jPSd__99c"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id: str, text: str) -> requests.Response:
    """
    Send a message to a Telegram chat.
    """
    url = f"{BASE_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"✅ Message sent to {chat_id}: {text}")
    except Exception as e:
        log_to_discord(os.getenv('DISCORD_WEBHOOK_STATUS'), f"❌ Failed to send message to {chat_id}: {e} 🔴")
        print(f"❌ Failed to send message: {e}")
    return response

def log_to_discord(webhook_url, message):
    """
    Log the activity to a Discord webhook.
    """
    data = {'content': message}
    response = requests.post(webhook_url, json=data)
    return response

def start(update, context):
    """
    /start command handler.
    """
    welcome_message = "Welcome to the Movie Bot! Use /help to see the available commands."
    send_message(update.message.chat_id, welcome_message)

def help(update, context):
    """
    /help command handler.
    """
    help_message = "Here are the available commands:\n/start - Start the bot\n/help - Show help"
    send_message(update.message.chat_id, help_message)

def forward_movie(update, context):
    """
    Handle forwarded movie files.
    """
    if update.message.document:
        file_id = update.message.document.file_id
        send_message(update.message.chat_id, "🎬 File received! What is the name of the movie?")
        context.user_data['file_id'] = file_id
    else:
        send_message(update.message.chat_id, "⚠️ Please forward a movie file. 📥")

def save_movie_name(update, context):
    """
    Save the movie name.
    """
    if 'file_id' not in context.user_data:
        send_message(update.message.chat_id, "⚠️ No file to associate with a movie name. Please forward the file first. 📥")
        return
    movie_name = update.message.text
    file_id = context.user_data['file_id']
    # Here you would save the movie data to the database or another storage.
    send_message(update.message.chat_id, f"🎬 Movie '{movie_name}' saved successfully!")

def get_movie_link(update, context):
    """
    Get the movie link.
    """
    movie_name = update.message.text
    # Here you would retrieve the movie link from the database.
    send_message(update.message.chat_id, f"Here is the link to the movie: <link_for_{movie_name}>")