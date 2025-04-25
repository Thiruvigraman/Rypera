import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from bot import handle_telegram_update

load_dotenv()

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

@app.route('/webhook/' + BOT_TOKEN, methods=['POST'])
def webhook():
    return handle_telegram_update(request)

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    response = requests.get(url)
    if response.status_code == 200:
        return "Webhook set successfully!"
    else:
        return f"Failed to set webhook: {response.text}", 400

if __name__ == '__main__':
    app.run(debug=True)