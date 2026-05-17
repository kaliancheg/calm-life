# 🌊 Tourism Dashboard - System Guide

## 📋 О проекте

**Название:** Tourism Dashboard (Волна Sea Village / Art-Life)  
**Тип:** Веб-приложение для учёта ежедневного туризма (ФОТ - фонд оплаты труда)  
**Версия:** 2.0 (с RBAC системой прав)  
**Последнее обновление:** 2026

---

## 🎯 Назначение

Система для:
- Учёта ежедневного туризма сотрудников (часы, ставки, начисления)
- Визуализации данных в виде дашборда с графиками
- Управления пользователями и правами доступа (RBAC)
- Импорта данных из Excel-табелей
- Аудита всех действий пользователей

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (443/80)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   /      │  │ /static  │  │ /dashboard│              │
│  │ (HTML)   │  │  (CSS)   │  │  (Flask) │              │
│  └──────────┘  └──────────┘  └────┬─────┘              │
│                                   │                      │
│                          ┌────────▼────────┐            │
│                          │  Gunicorn/Flask │            │
│                          │   (Unix Socket) │            │
│                          └────────┬────────┘            │
└───────────────────────────────────┼─────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │    MySQL 8.0      │
                          │  daily_tourism    │
                          └───────────────────┘
```

---

## 📁 Структура проекта

```
calm-life/
├── tourism/
│   ├── app.py                      # Основное Flask приложение
│   ├── gunicorn.conf.py            # Конфигурация Gunicorn
│   ├── tourism-dashboard.service   # Systemd сервис
│   ├── nginx.conf                  # Конфигурация Nginx
│   ├── requirements.txt            # Python зависимости
│   ├── migrations/
│   │   └── update_schema.sql       # Миграция БД (RBAC + audit_log)
│   ├── static/
│   │   └── css/
│   │       ├── base.css            # Общие стили (шрифты, reset, footer)
│   │       ├── login.css           # Страница входа
│   │       ├── dashboard.css       # Дашборд (фильтры, графики)
│   │       └── admin.css           # Админ-панель (другой дизайн)
│   └── templates/
│       ├── login.html              # Страница входа
│       ├── dashboard.html          # Дашборд с графиками
│       └── admin.html              # Админ-панель (5 вкладок)
```

---

## 🛠️ Технологический стек

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| **Backend** | Python + Flask | 3.x |
| **WSGI** | Gunicorn | 21.x |
| **Database** | MySQL | 8.0+ |
| **ORM** | mysql-connector-python | 8.x |
| **Frontend** | HTML5 + CSS3 + Vanilla JS | - |
| **Charts** | Plotly.js + Chart.js | 2.27.0 + 4.4.0 |
| **Excel** | pandas + openpyxl + SheetJS | 2.x |
| **Security** | bcrypt + Flask-Login | 5.x + 0.6.x |
| **Web Server** | Nginx | 1.24+ |
| **SSL** | Let's Encrypt | - |

---

## 🔐 Безопасность

### Аутентификация
- **bcrypt** для хеширования паролей (cost factor 12)
- **Flask-Login** для управления сессиями
- **Session timeout:** 1 час неактивности
- **Защита от брутфорс:** блокировка на 15 минут после 3 неудачных попыток
- **Сильные пароли:** минимум 6 символов

### Авторизация (RBAC)
```
admin → Полный доступ ко всему
manager → Просмотр данных + экспорт
user → Только просмотр своих данных
```

### Права на ресурсы
| Ресурс | Действия |
|--------|----------|
| users | view/create/update/delete |
| roles | view/create/update/delete |
| permissions | view/create/update/delete |
| data | view/export |
| audit_log | view |
| settings | view/update |

### Ограничения по данным
- **Подразделения:** фильтр по доступным подразделениям
- **Отделы:** фильтр по доступным отделам
- **can_view_all:** игнорировать ограничения (для менеджеров)

---

## 🗄️ База данных

### Основные таблицы

| Таблица | Назначение |
|---------|-----------|
| `users` | Пользователи системы |
| `records` | Записи туризма (ФИО, часы, начисления) |
| `permissions` | Основные права пользователя |
| `permissions_subdivisions` | Права на подразделения |
| `permissions_otdels` | Права на отделы |
| `audit_log` | Журнал всех действий |
| `roles` | Роли системы (будущее расширение) |

### Важные поля в `records`
```sql
- fio: ФИО сотрудника
- snils: СНИЛС
- podrazdelenie: Подразделение (детальное)
- otdel: Отдел (краткое)
- dolzhnost: Должность
- data: Дата
- chasy: Часы
- nachisleno: Начислено
- itogo: Итого
```

---

## 🚀 Запуск проекта

### Локальная разработка

```bash
# Установка зависимостей
cd calm-life/tourism
pip install -r requirements.txt

# Создание БД (если нет)
mysql -u root -p -e "CREATE DATABASE daily_tourism CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Миграция
mysql -u root -p daily_tourism < migrations/update_schema.sql

# Запуск
python app.py

# Открыть: http://localhost:5000
```

### Production (сервер)

```bash
# Service уже настроен как systemd
sudo systemctl start tourism-dashboard
sudo systemctl status tourism-dashboard
sudo systemctl enable tourism-dashboard  # Автозапуск при старте

# Nginx
sudo nginx -t
sudo systemctl reload nginx

# Логи
tail -f /var/log/tourism-dashboard/error.log
journalctl -u tourism-dashboard -f
```

---

## 📊 Маршруты приложения

### Публичные
- `GET /login` - Страница входа
- `POST /login` - Обработка входа
- `GET /health` - Health check для Xray

### Защищённые
- `GET /` или `GET /dashboard.html` - Дашборд
- `GET /api/data` - API данных с учётом прав
- `GET /logout` - Выход

### Админ-панель
- `GET /admin` - Главная админки
- `GET /admin/users` - Пользователи
- `GET /admin/permissions` - Права доступа
- `GET /admin/roles` - Роли
- `GET /admin/audit-log` - Журнал аудита
- `POST /admin/import-excel` - Импорт Excel

---

## 🎨 CSS Архитектура

### Гибридная структура (оптимизирована)
```
static/css/
├── base.css         # Общие стили (шрифты, reset, footer, таблицы, инпуты)
├── login.css        # Только стили входа
├── dashboard.css    # Только стили дашборда
└── admin.css        # Отдельный дизайн (Inter шрифт, CSS variables)
```

### Преимущества
- ✅ Меньше дублирования (шрифты и reset только в base.css)
- ✅ Быстрее кэширование (base.css общий для всех страниц)
- ✅ Легче поддерживать (общие изменения в одном месте)
- ✅ Масштабируемость для новых страниц

### Дизайн-система
- **Шрифты:** Orbitron (заголовки), Rajdhani (текст)
- **Цвета:** 
  - Основной: #00ffff (cyan)
  - Вторичный: #8a2be2 (purple)
  - Фон: #12162e → #1e2052 (gradient)
- **Эффекты:** box-shadow свечение при hover

### UI Дашборда
- **Заголовок:** 🌊 Volna Sea Village / Art-Life (ФОТ) — слева, с cyan-свечением
- **User-info (ФИО, Админ-панель, Выйти):** справа, выровнены по правому краю с остальными блоками
- **Контейнер:** padding 0 20px (на мобильных 10px/5px) для выравнивания всех блоков
- **Анимация:** пульсирующее свечение заголовка (3s ease-in-out infinite)

### Фильтры на дашборде
- **По умолчанию:** Текущий месяц
- **Быстрый выбор:** Позавчера, Текущий месяц, Прошлый месяц, Последние 7 дней
- **Навигация:** Кнопки для переключения дней/месяцев

---

## 🔧 Важные настройки

### В `app.py`
```python
# SECRET_KEY (ОБЯЗАТЕЛЬНО для production!)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Session timeout
app.config['SESSION_TIMEOUT'] = timedelta(hours=1)

# Brute-force protection
app.config['MAX_LOGIN_ATTEMPTS'] = 3  # Максимум неудачных попыток
app.config['BLOCK_DURATION'] = timedelta(minutes=15)  # Блокировка на 15 минут

# MySQL конфиг
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'tourism',
    'password': 'tourism123',  # ⚠️ Изменить в production!
    'database': 'daily_tourism',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
}
```

### В `nginx.conf`
```nginx
# Статика (кэширование 30 дней)
location /static {
    alias /var/www/calm-life/tourism/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Flask прокси
location /dashboard.html {
    proxy_pass http://unix:/tmp/tourism-dashboard.sock;
    ...
}
```

### В `gunicorn.conf.py`
```python
# Bind to Unix socket
bind = "unix:/tmp/tourism-dashboard.sock"

# Worker processes
workers = 2
worker_class = "sync"

# PID file (в /tmp для прав доступа www-data)
pidfile = "/tmp/tourism-dashboard.pid"

# Logging
errorlog = "/var/log/tourism-dashboard/error.log"
accesslog = "/var/log/tourism-dashboard/access.log"
loglevel = "info"
```
```nginx
# Статика (кэширование 30 дней)
location /static {
    alias /var/www/calm-life/tourism/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Flask прокси
location /dashboard.html {
    proxy_pass http://unix:/tmp/tourism-dashboard.sock;
    ...
}
```

---

## 🐛 Известные проблемы и решения

### Проблема: CSS не загружается на сервере
**Решение:** 
1. Проверить `app.py` имеет `static_folder`
2. Проверить `nginx.conf` имеет `location /static`
3. Перезагрузить nginx и сервис

### Проблема: "У вас нет прав для выполнения этого действия"
**Решение:**
1. Проверить роль пользователя в БД
2. Проверить таблицу `permissions`
3. Проверить `_allowed_subdivisions` и `_allowed_otdels`

### Проблема: Сессия истекает слишком быстро
**Решение:** Увеличить `SESSION_TIMEOUT` в `app.py`

### Проблема: "Слишком много неудачных попыток. Пользователь заблокирован"
**Решение:** 
- Подождать 15 минут после блокировки
- Или вручную сбросить в БД: 
```sql
UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE username = 'username';
```

### Проблема: Ошибка 502 Bad Gateway после неудачных попыток
**Решение:** Было исправлено - функции теперь используют существующее подключение к БД вместо создания нового. Обновите код через `git pull`.

### Проблема: Кнопки "Последние 7 дней" и "Сбросить" не светятся
**Решение:** Добавить `.btn-secondary:hover { box-shadow: ... }` в `dashboard.css`

### Проблема: Ошибка 502 Bad Gateway при запуске Gunicorn
**Решение:** PID файл Gunicorn должен быть в `/tmp/`, а не в `/var/run/` (нет прав у www-data). Изменить в `gunicorn.conf.py`:
```python
pidfile = "/tmp/tourism-dashboard.pid"
```

### Проблема: Лаг и белый засвет при скролле до пульсирующего заголовка
**Решение:** Добавлена GPU-акселерация для `.page-title` в `dashboard.css`:
```css
.page-title {
    /* ... остальные стили ... */
    transform: translateZ(0);
    will-change: text-shadow;
}
```
**Причина:** Анимация `text-shadow` без GPU-ускорения вызывала heavy repaint при скролле.  
**Статус:** ✅ Исправлено (2026)

---

## 📝 Следующие шаги (Roadmap)

### Приоритет 1
- [ ] Настройка мониторинга и алертов
- [ ] Регулярные бэкапы БД (cron + mysqldump)
- [ ] Настройка Sentry для отслеживания ошибок

### Приоритет 2
- [ ] Экспорт в PDF дашборда
- [ ] Email уведомления о критических событиях
- [ ] Мобильная адаптация (улучшить responsive)

### Приоритет 3
- [ ] API для интеграции с внешними системами
- [ ] Кэширование данных (Redis)
- [ ] WebSocket для real-time обновлений

---

## 📞 Контакты и поддержка

**Разработчик:** Kalian Roman  
**Команда:** NLP-Core-Team  
**Поддержка:** FitoFarm (https://fitofarm.ru)

**Репозиторий:** `github.com/kaliancheg/calm-life`  
**Домен:** `calm-life.ru`

---

## 📚 Полезные команды

```bash
# Локально
cd calm-life/tourism
python app.py
curl http://localhost:5000/health

# На сервере
cd /var/www/calm-life
git pull origin main
sudo systemctl restart tourism-dashboard
sudo nginx -t && sudo systemctl reload nginx

# БД
mysql -u root -p daily_tourism
SELECT COUNT(*) FROM records;
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;

# Логи
tail -f /var/log/nginx/calm-life-error.log
journalctl -u tourism-dashboard -f --no-pager
```

---

## ✅ Чек-лист перед деплоем

- [ ] SECRET_KEY изменён на случайную строку
- [ ] Пароль MySQL изменён в production
- [ ] HTTPS настроен (Let's Encrypt)
- [ ] Бэкапы БД настроены (cron)
- [ ] Администратор создан
- [ ] Права пользователей проверены
- [ ] Журнал аудита работает
- [ ] Nginx конфигурация протестирована (`nginx -t`)
- [ ] Все файлы CSS загружаются (`curl /static/css/base.css`)

---

**Последнее обновление:** 2026-05-17 (GPU-акселерация для .page-title)  
**Версия:** 2.0  
**Статус:** ✅ Production Ready