# Gunicorn configuration file

import multiprocessing
import os

# Bind to this address - используем Unix socket для лучшей совместимости
# Каталог /run/tourism-dashboard создаётся systemd (RuntimeDirectory) при старте сервиса
bind = "unix:/run/tourism-dashboard/tourism-dashboard.sock"

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
pidfile = "/run/tourism-dashboard/tourism-dashboard.pid"
umask = 0o000
user = "www-data"
group = "www-data"

# Рабочая директория для временных файлов Gunicorn
# Должна существовать всегда: systemd создаёт её через RuntimeDirectory
worker_tmp_dir = "/run/tourism-dashboard"

# Control-сокет gunicorn 26+ по умолчанию ищет в $XDG_RUNTIME_DIR или $HOME,
# а у www-data HOME=/var/www недоступен на запись -> ошибка в логе при старте.
control_socket = "/run/tourism-dashboard/gunicorn.ctl"

# Logging
errorlog = "/var/log/tourism-dashboard/error.log"
accesslog = "/var/log/tourism-dashboard/access.log"
loglevel = "info"

# Process names
def worker_title(worker):
    return f"tourism-dashboard-worker-{worker.pid}"
