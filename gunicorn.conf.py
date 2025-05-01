# Gunicorn configuration file
bind = "0.0.0.0:$PORT"
workers = 1
threads = 2
timeout = 60
loglevel = "info"
accesslog = "-"
errorlog = "-"