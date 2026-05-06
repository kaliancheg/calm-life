# Gunicorn configuration file

import multiprocessing

# Bind to this address
bind = "127.0.0.1:5000"

# Worker processes
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50

# Process naming
proc_name = "tourism-dashboard"

# Server mechanics
daemon = False
pidfile = "/var/run/tourism-dashboard.pid"
umask = 0
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# Logging
errorlog = "/var/log/tourism-dashboard/error.log"
accesslog = "/var/log/tourism-dashboard/access.log"
loglevel = "info"

# Process names
def worker_title(worker):
    return f"tourism-dashboard-worker-{worker.pid}"
