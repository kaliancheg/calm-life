# Gunicorn configuration file

import multiprocessing
import os

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

# Создаем отдельную директорию для временных файлов Gunicorn
# Примечание: директорию нужно создать вручную с правами www-data
tmpdir = "/tmp/tourism-dashboard"
try:
    os.makedirs(tmpdir, exist_ok=True)
except PermissionError:
    # Если нет прав на создание, используем стандартный /tmp
    tmpdir = None

# Server mechanics (продолжение)
tmp_upload_dir = tmpdir

# Logging
errorlog = "/var/log/tourism-dashboard/error.log"
accesslog = "/var/log/tourism-dashboard/access.log"
loglevel = "info"

# Process names
def worker_title(worker):
    return f"tourism-dashboard-worker-{worker.pid}"
