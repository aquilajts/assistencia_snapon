import os

bind = "0.0.0.0:%s" % os.environ.get("PORT", "10000")
worker_class = "gthread"
workers = 1
threads = 4
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True