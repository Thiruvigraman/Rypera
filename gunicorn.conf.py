# Gunicorn configuration file
workers = 1  # Reduced for Render free tier
threads = 2  # Reduced for Render free tier
bind = "0.0.0.0:$PORT"
timeout = 120
max_requests = 500
max_requests_jitter = 50
loglevel = "debug"  # Enable debug logging