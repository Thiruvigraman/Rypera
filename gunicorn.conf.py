# Gunicorn configuration file

import os

bind = f"0.0.0.0:{os.getenv('PORT', 8443)}"
workers = 2
threads = 2
timeout = 30
max_requests = 100
max_requests_jitter = 10
loglevel = "info"  # Changed from default (debug) to info
accesslog = "-"
errorlog = "-"