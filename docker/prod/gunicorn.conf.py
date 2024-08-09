import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
access_log_format = '%(u)s %(t)s "%(r)s" %(s)s'  # this wont work yet: https://github.com/encode/uvicorn/issues/527
