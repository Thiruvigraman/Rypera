# Gunicorn configuration file
workers = 1
threads = 1
bind = "0.0.0.0:$PORT"
timeout = 30
max_requests = 100  # Restart workers after 100 requests to free memory
max_requests_jitter = 10