# Gunicorn configuration file
workers = 2
threads = 4
bind = "0.0.0.0:$PORT"
timeout = 60
max_requests = 100
max_requests_jitter = 10