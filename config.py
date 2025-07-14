# config.py

MONGODB_URI = "your_mongodb_uri"  # Replace with your MongoDB Atlas URI
BOT_TOKEN = "your_bot_token"  # Replace with your Telegram bot token
ADMIN_ID = 123456789  # Replace with your Telegram user ID
BOT_USERNAME = "your_bot_username"  # Replace with @YourBotUsername
DISCORD_WEBHOOK_STATUS = "https://discord.com/api/webhooks/1357644159888003237/..."
DISCORD_WEBHOOK_LIST_LOGS = "https://discord.com/api/webhooks/1357644530136125603/..."
DISCORD_WEBHOOK_FILE_ACCESS = "https://discord.com/api/webhooks/1357644928016191549/..."

EMBED_CONFIG = {
    'default': {
        'color': 0x7289DA,  # Default blue
        'author': 'Telegram Bot',
        'footer': 'Powered by xAI'
    },
    'status': {
        'color': 0xFF0000,  # Red for startup/shutdown/errors
        'title': 'Bot Status Update'
    },
    'list_logs': {
        'color': 0x00FF00,  # Green for admin actions
        'title': 'Admin Action Log'
    },
    'file_access': {
        'color': 0x0000FF,  # Blue for file access
        'title': 'File Access Log'
    },
    'health': {
        'color': 0xFFFF00,  # Yellow for health checks
        'title': 'Health Check',
        'author': 'Bot Health Monitor',
        'footer': 'System Status'
    }
}