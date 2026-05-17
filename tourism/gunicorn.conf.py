# Gunicorn configuration file

import multiprocessing
import os

# Bind to this address - используем Unix socket для лучшей совместимости
bind = "unix:/tmp/tourism-dashboard.sock"

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50

# Process naming
daemon = False
pidfile = "/tmp/tourism-dashboard.pid"
umask = 0o000
user = "www-data"
group = "www-data"

# Рабочая директория для временных файлов Gunicorn
worker_tmp_dir = "/tmp/tourism-dashboard"

# Logging
errorlog = "/var/log/tourism-dashboard/error.log"
accesslog = "/var/log/tourism-dashboard/access.log"
loglevel = "info"

# Process names
def worker_title(worker):
    return f"tourism-dashboard-worker-{worker.pid}"
