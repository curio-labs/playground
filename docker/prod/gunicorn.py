import multiprocessing
import os

DEFAULT_PORT = 8000
PORT = os.getenv("PORT", DEFAULT_PORT)
bind = f"0.0.0.0:{PORT}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
access_log_format = '%(u)s %(t)s "%(r)s" %(s)s'  # this wont work yet: https://github.com/encode/uvicorn/issues/527
