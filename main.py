import os
import logging
import atexit
import json
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, Application
from dotenv import load_dotenv
from db import save_movie
from bot import start, help, forward_movie, save_movie_name, get_movie_link
from discord_webhook import log_bot_status  # Import the logging function
from threading import Thread

load_dotenv()

DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Movie Bot API!"  # Welcome message

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    
    Returns:
    str: Health status message.
    """
    return "✅ Bot is running!"

@app.route('/<bot_token>', methods=['POST'])
def webhook(bot_token):
    """
    Handles incoming webhook from Telegram.
    
    Returns:
    Response: HTTP response.
    """
    if bot_token != os.getenv('BOT_TOKEN'):
        return 'Unauthorized', 403  # Unauthorized if the bot token doesn't match

    try:
        json_str = request.get_data().decode('UTF-8')
        bot = Bot(os.getenv('BOT_TOKEN'))  # Initialize bot here if not passed
        update = Update.de_json(json.loads(json_str), bot)
        application.process_update(update)
    except Exception as e:
        app.logger.error(f"Error in webhook: {e}")
    return 'OK'

def start_bot():
    """
    Starts the Telegram bot in a separate thread.
    """
    bot = Bot(os.getenv('BOT_TOKEN'))
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(MessageHandler(filters.Document.ALL, forward_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_movie_name))
    application.add_handler(CommandHandler('get_movie_link', get_movie_link))

    # Start the bot
    application.run_polling()

def main():
    """
    Main function to set up the bot and start the Flask server.
    """
    # Log bot online status
    log_bot_status("online")

    # Start the Telegram bot in a separate thread
    bot_thread = Thread(target=start_bot)
    bot_thread.start()

    # Run Flask
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)

    # Register an exit function to log when the bot goes offline
    atexit.register(lambda: log_bot_status("offline", "Turned off by user"))  # Logs offline with reason on shutdown

if __name__ == '__main__':
    main()