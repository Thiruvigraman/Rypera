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

load_dotenv()

DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    
    Returns:
    str: Health status message.
    """
    return "✅ Bot is running!"

@app.route('/', methods=['GET'])
def home():
    """
    Root endpoint (optional). Can be used for basic information or redirection.
    
    Returns:
    str: A message or redirect response.
    """
    return "Welcome to the bot service! Use /health for status."

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handles incoming webhook from Telegram.
    
    Returns:
    Response: HTTP response.
    """
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json.loads(json_str), bot)
    application.process_update(update)
    return 'OK'

def main():
    """
    Main function to set up the bot and start the Flask server.
    """
    bot = Bot(os.getenv('BOT_TOKEN'))
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Log bot online status
    log_bot_status("online")

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(MessageHandler(filters.Document.ALL, forward_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_movie_name))
    application.add_handler(CommandHandler('get_movie_link', get_movie_link))

    # Start the application in a background thread (as Flask is blocking)
    atexit.register(lambda: log_bot_status("offline", "Turned off by user"))  # Logs offline with reason on shutdown

    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)

if __name__ == '__main__':
    main()