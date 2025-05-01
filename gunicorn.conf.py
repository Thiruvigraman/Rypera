# Gunicorn configuration file
bind = "0.0.0.0:$PORT"
workers = 2  # Use 2 workers to balance load and memory usage
timeout = 60  # Increase timeout to handle slow Telegram API calls
loglevel = "info"  # Log level for debugging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stdout