import os
import requests
from flask import Flask, request
from db import add_movie, get_movie, update_movie, delete_movie
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get bot token and webhook URL from .env file
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Define the admin ID (replace with your own Telegram ID)
ADMIN_ID = int(os.getenv("ADMIN_ID"))"

# Set up webhook route for Telegram updates
@app.route('/webhook/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.method == 'POST':
        json_data = request.get_json()
        chat_id = json_data['message']['chat']['id']
        command = json_data['message']['text']
        
        # Allow /start for all users
        if command == '/start':
            send_message(chat_id, "Welcome to the Movie Bot!")
        
        # Only allow other commands for the admin
        elif chat_id == int(ADMIN_ID):  # Check if the sender is the admin
            if command == '/add_movie':
                # Example command to add a movie
                movie_data = {"title": "Movie Title", "description": "Movie Description"}
                if add_movie(movie_data):
                    send_message(chat_id, "Movie added successfully.")
                else:
                    send_message(chat_id, "Failed to add movie.")
            
            elif command == '/get_movie':
                # Example command to get a movie
                movie = get_movie("Movie Title")
                if movie:
                    send_message(chat_id, f"Movie found: {movie['title']} - {movie['description']}")
                else:
                    send_message(chat_id, "Movie not found.")
            
            elif command == '/update_movie':
                # Example command to update a movie
                updated_data = {"description": "Updated Movie Description"}
                if update_movie("Movie Title", updated_data):
                    send_message(chat_id, "Movie updated successfully.")
                else:
                    send_message(chat_id, "Failed to update movie.")
            
            elif command == '/delete_movie':
                # Example command to delete a movie
                if delete_movie("Movie Title"):
                    send_message(chat_id, "Movie deleted successfully.")
                else:
                    send_message(chat_id, "Failed to delete movie.")
            
            # Add other admin-only commands here
            else:
                send_message(chat_id, "Unknown command.")
        else:
            send_message(chat_id, "You are not authorized to use this command.")
        
        return 'OK', 200

# Function to send message to a chat
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, data=payload)
    
    return response.json()

# Set the webhook with Telegram API
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return "Webhook set successfully!"
    else:
        return f"Failed to set webhook: {response.text}", 400

if __name__ == '__main__':
    app.run(debug=True)