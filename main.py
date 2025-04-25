import os
import logging
import atexit
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher, MessageHandler, Filters
from dotenv import load_dotenv
from db import load_movies, save_movie, delete_movie, rename_movie
from discord_webhook import log_to_discord
from bot import start, help, forward_movie, save_movie_name, get_movie_link

load_dotenv()

DISCORD_WEBHOOK_STATUS = os.getenv('DISCORD_WEBHOOK_STATUS')
DISCORD_WEBHOOK_LIST_LOGS = os.getenv('DISCORD_WEBHOOK_LIST_LOGS')

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    
    Returns:
    str: Health status message.
    """
    return "✅ Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handles incoming webhook from Telegram.
    
    Returns:
    Response: HTTP response.
    """
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json.loads(json_str), bot)
    dispatcher.process_update(update)
    return 'OK'

def main():
    """
    Main function to set up the bot and start the Flask server.
    """
    bot = Bot(os.getenv('BOT_TOKEN'))
    dispatcher = Dispatcher(bot, None)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help))
    dispatcher.add_handler(MessageHandler(Filters.document, forward_movie))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_movie_name))
    dispatcher.add_handler(CommandHandler('get_movie_link', get_movie_link))
    
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)

if __name__ == '__main__':
    main()