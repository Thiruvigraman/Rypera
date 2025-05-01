# Gunicorn configuration file
workers = 2
threads = 4
bind = "0.0.0.0:$PORT"
timeout = 120
max_requests = 500
max_requests_jitter = 50