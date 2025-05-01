# Gunicorn configuration file
bind = "0.0.0.0:$PORT"
workers = 1  # Reduce to 1 to minimize memory usage
threads = 2  # Use threads to handle concurrent requests
timeout = 60  # Allow slow Telegram API responses
loglevel = "info"  # Log for debugging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stdout