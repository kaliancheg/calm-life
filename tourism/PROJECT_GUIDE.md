# 🌊 Tourism Dashboard - System Guide

## 📋 О проекте

**Название:** Tourism Dashboard (Волна Sea Village / Art-Life / ФОТ)  
**Тип:** Веб-приложение для учёта ежедневного туризма сотрудников (ФОТ - фонд оплаты труда)  
**Версия:** 2.5 (с ФОТ-аналитикой, новыми API эндпоинтами `/api/fot/summary` и `/api/fot/breakdown`)  
**Последнее обновление:** 2026-05-24  
**Среда разработки:** MS VS Code + PowerShell (синтаксис команд адаптирован для Windows)  
**Процесс деплоя:** локальные правки → git push в GitHub → деплой на production сервер

---

## 🎯 Назначение

Система для:
- Учёта ежедневного туризма сотрудников (часы, ставки, начисления)
- Визуализации данных в виде дашборда с графиками
- LFL анализа (Like-for-Like) сравнения периодов (месяц/неделя/пользовательский)
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
- `GET /api/fot/summary` - API ключевых метрик ФОТ (сотрудники, часы, начисления, средняя ставка)
  - `?from=YYYY-MM-DD&to=YYYY-MM-DD` — фильтр по дате
  - `?granularity=day|week|month` — уровень агрегации
  - `?pod=Подразделение&otdel=Отдел` — фильтр по структурным единицам
- `GET /api/fot/breakdown` - API разбивки ФОТ по подразделениям/отделам/должностям
  - `?from=YYYY-MM-DD&to=YYYY-MM-DD` — фильтр по дате
  - `?by=podrazdelenie|otdel|dolzhnost` — параметр группировки
  - `?limit=50` — лимит строк
- `GET /api/lfl` - API LFL анализа (сравнение периодов)
  - `?mode=month` — Месяц к месяцу (по умолчанию)
  - `?mode=week` — Неделя к неделе
  - `?mode=custom&custom_from=YYYY-MM-DD&custom_to=YYYY-MM-DD&prev_from=YYYY-MM-DD&prev_to=YYYY-MM-DD` — Пользовательский период
  - `?filter_from=YYYY-MM-DD&filter_to=YYYY-MM-DD` — Фильтр по датам
  - `?selected_pod=Подразделение&selected_otdel=Отдел` — Фильтр по подразделениям
- `GET /logout` - Выход

### Админ-панель
- `GET /admin` - Главная админки
- `GET /admin/users` - Пользователи
- `GET /admin/permissions` - Права доступа
- `GET /admin/roles` - Роли
- `GET /admin/audit-log` - Журнал аудита
- `POST /admin/import-excel` - Импорт Excel

---

## 📡 LFL API Документация

### Эндпоинт: `GET /api/lfl`

**Описание:** Возвращает данные для сравнения периодов (Like-for-Like анализ)

**Параметры запроса:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `mode` | string | Нет | Режим сравнения: `month`, `week`, `custom` (по умолчанию: `month`) |
| `custom_from` | string | Нет | Начало текущего периода (формат: `YYYY-MM-DD`) |
| `custom_to` | string | Нет | Конец текущего периода (формат: `YYYY-MM-DD`) |
| `prev_from` | string | Нет | Начало предыдущего периода (формат: `YYYY-MM-DD`) |
| `prev_to` | string | Нет | Конец предыдущего периода (формат: `YYYY-MM-DD`) |
| `filter_from` | string | Нет | Фильтр по датам (начало) |
| `filter_to` | string | Нет | Фильтр по датам (конец) |
| `selected_pod` | string | Нет | Фильтр по подразделению |
| `selected_otdel` | string | Нет | Фильтр по отделу |

**Примеры запросов:**

```bash
# Месяц к месяцу (по умолчанию)
curl https://calm-life.ru/api/lfl?mode=month

# Неделя к неделе
curl https://calm-life.ru/api/lfl?mode=week

# Пользовательский период
curl "https://calm-life.ru/api/lfl?mode=custom&custom_from=2026-05-01&custom_to=2026-05-24&prev_from=2026-04-01&prev_to=2026-04-30"

# С фильтрами
curl "https://calm-life.ru/api/lfl?mode=month&selected_pod=Волна&selected_otdel=Администрация"
```

**Ответ API (успешный):**

```json
{
  "period_current": {
    "from": "2026-05-01",
    "to": "2026-05-24",
    "metrics": {
      "employees": 45,
      "hours": 720.5,
      "money": 150000.0,
      "records": 120
    }
  },
  "period_previous": {
    "from": "2026-04-01",
    "to": "2026-04-30",
    "metrics": {
      "employees": 42,
      "hours": 680.0,
      "money": 142000.0,
      "records": 115
    }
  },
  "change": {
    "employees": 7.14,
    "hours": 5.96,
    "money": 5.63,
    "records": 4.35
  },
  "delta": {
    "employees": 3,
    "hours": 40.5,
    "money": 8000.0,
    "records": 5
  }
}
```

**Поля ответа:**

| Поле | Тип | Описание |
|------|-----|----------|
| `period_current.from` | string | Начало текущего периода |
| `period_current.to` | string | Конец текущего периода |
| `period_current.metrics.employees` | number | Количество уникальных сотрудников |
| `period_current.metrics.hours` | number | Всего отработано часов |
| `period_current.metrics.money` | number | Всего начислено (₽) |
| `period_current.metrics.records` | number | Количество записей |
| `period_previous.*` | ... | То же самое для предыдущего периода |
| `change.*` | number | Изменение в % (относительно предыдущего периода) |
| `delta.*` | number | Абсолютное изменение (current - previous) |

**Ошибки:**

```json
{
  "error": "У вас нет прав для просмотра данных"
}
```

HTTP статус: `403 Forbidden`

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

### Проблема: 100% загрузка одного ядра CPU при просмотре дашборда/страницы входа
**Решение:** Удалены все CSS-анимации с пульсацией свечения:
- `dashboard.css`: убрана анимация `glow-cyan` у `.page-title`
- `login.css`: убраны анимации `glow-cyan`, `glow-purple`, `pulse` у заголовков и предупреждений
```css
/* Было:
animation: glow-cyan 3s ease-in-out infinite;
*/
/* Стало: статический text-shadow без animation */
```
**Причина:** Анимации `text-shadow` вызывали heavy repaint даже с GPU-акселерацией, загружая одно ядро на 100%.  
**Статус:** ✅ Исправлено (2026-05-17) — заголовки остались с постоянным свечением, без нагрузки на CPU

### Проблема: Время "Последний вход" отображается некорректно (UTC вместо локального)
**Решение:** 
1. Добавлена библиотека `pytz` для работы с часовыми поясами
2. Добавлена функция `format_datetime_to_server()` в `app.py` для форматирования datetime
3. Настроен системный часовой пояс сервера на `Europe/Moscow` (UTC+3)
4. Обновлена JS-функция `formatServerTime()` для форматирования времени в формате `DD.MM.YYYY HH:MM`

**Изменения в коде:**
- `app.py`: импортирован `pytz`, добавлена `SERVER_TIMEZONE`, добавлена `format_datetime_to_server()`
- `requirements.txt`: добавлена `pytz>=2024.1`
- `admin.html`: обновлена функция `formatServerTime()` для обработки формата GMT

**Команды на сервере:**
```bash
# Установить часовой пояс
sudo timedatectl set-timezone Europe/Moscow

# Перезапустить MySQL для применения настроек
sudo systemctl restart mysql

# Установить pytz в виртуальное окружение
cd /var/www/calm-life/tourism
./venv/bin/pip install pytz

# Перезапустить сервис
sudo systemctl restart tourism-dashboard
```

**Статус:** ✅ Исправлено (2026-05-23) — время отображается по времени сервера (MSK) на всех вкладках

### Проблема: При загрузке админ-панели не открывается ни одна вкладка по умолчанию
**Решение:** Добавлена логика автоматической активации вкладки "Обзор" для администратора в `admin.html`

**Изменения в коде:**
- `admin.html`: в блоке `DOMContentLoaded` добавлена проверка `role === 'admin'` с автоматической активацией вкладки "Обзор"
- Скрываются все вкладки, затем активная вкладка показывается с классом `active`

**Принцип работы:**
```javascript
// Для администратора активировать вкладку "Обзор" по умолчанию
if (role === 'admin') {
    const dashboardTab = document.querySelector('.nav-tab[data-tab="dashboard"]');
    const dashboardContent = document.getElementById('tab-dashboard');
    
    if (dashboardTab && dashboardContent) {
        // Убрать active со всех вкладок
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => {
            t.classList.remove('active');
            t.classList.add('hidden');
        });
        
        // Активировать вкладку "Обзор"
        dashboardTab.classList.add('active');
        dashboardContent.classList.remove('hidden');
        dashboardContent.classList.add('active');
    }
}
```

**Статус:** ✅ Исправлено (2026-05-23) — при загрузке админ-панели администратор сразу видит вкладку "Обзор"

### Проблема: Отсутствие сравнения периодов для анализа динамики ФОТ
**Решение:** Добавлен LFL (Like-for-Like) блок на дашборд с возможностью сравнения периодов

**Функционал:**
- **3 режима сравнения:**
  - Месяц к месяцу (MoM) — текущий месяц vs предыдущий месяц
  - Неделя к неделе (WoW) — последние 7 дней vs предыдущие 7 дней
  - Пользовательский период — выбор любых двух периодов для сравнения
- **Метрики:** Начислено (₽), Сотрудники (чел), Часы (ч)
- **Фильтрация:** Учитываются выбранные подразделение, отдел и даты
- **Визуализация:** 3 карточки (текущий период, предыдущий период, изменение в %)

**Изменения в коде:**
- `app.py`: добавлен новый эндпоинт `/api/lfl` с расчётом метрик на backend
- `dashboard.html`: добавлен HTML блок LFL с кнопками управления и инпутами дат
- `dashboard.css`: добавлены стили для LFL блока с адаптацией под мобильные устройства
- `dashboard.html` (JS): добавлены функции `setLFLMode()`, `calculateLFL()`, `updateLFLDisplay()`

**Пример API запроса:**
```
GET /api/lfl?mode=month&filter_from=2026-05-01&filter_to=2026-05-24
GET /api/lfl?mode=week
GET /api/lfl?mode=custom&custom_from=2026-04-01&custom_to=2026-04-30
```

**Пример ответа API:**
```json
{
  "period_current": {
    "from": "2026-05-01",
    "to": "2026-05-24",
    "metrics": {"employees": 45, "hours": 720, "money": 150000, "records": 120}
  },
  "period_previous": {
    "from": "2026-04-01",
    "to": "2026-04-30",
    "metrics": {"employees": 42, "hours": 680, "money": 142000, "records": 115}
  },
  "change": {
    "employees": 7.14,
    "hours": 5.88,
    "money": 5.63,
    "records": 4.35
  },
  "delta": {
    "employees": 3,
    "hours": 40,
    "money": 8000,
    "records": 5
  }
}
```

**Статус:** ✅ Реализовано (2026-05-24) — LFL анализ доступен на дашборде

### Проблема: Скролл в списке отделов/подразделений в админ-панели

**Решение:** Убрано ограничение высоты списка прав доступа

**Изменения в коде:**
- `admin.css`: удалены свойства `max-height: 300px` и `overflow-y: auto` из `.resource-list`
- Убрано ограничение `max-height: 250px` из мобильного медиа-запроса

**Результат:** Все отделы и подразделения отображаются полностью без скролла

**Статус:** ✅ Исправлено (2026-05-24) — список отделов/подразделений отображается полностью

### Проблема: Неинтуитивное отображение выбранных прав доступа

**Решение:** Улучшен визуальный стиль чекбоксов для подразделений и отделов

**Изменения в коде:**
- `admin.css`: добавлены стили для `.resource-item` с плавными переходами
- Чекбоксы теперь зелёные (`accent-color: var(--success)`)
- При выборе чекбокса текст загорается зелёным (`color: var(--success)`)
- Добавлен эффект hover с лёгким зелёным фоном
- Плавная анимация изменения цвета (transition: 0.3s)

**Визуальный результат:**
```
Было: ☐ Отдел (серый текст)
Стало: ☑ Отдел (зелёный текст ✓, зелёный чекбокс ✓)
```

**Статус:** ✅ Улучшено (2026-05-24) — чекбоксы прав доступа интуитивно понятны

### Проблема: Нет зелёной подсветки в блоке "Основные права" и клик по строке не работает

**Решение:** 
1. Добавлена зелёная подсветка для "Основных прав" (perm-item) — аналогично отделам/подразделениям
2. Исправлен порядок input/label в HTML для работы CSS-селектора `input:checked + label`
3. Добавлен cursor:pointer на строки ресурсов и JS обработчик клика

**Изменения в коде:**
- `admin.html`: поменяны местами input и label в perm-item, добавлена функция `attachResourceItemClickHandlers()`
- `admin.css`: добавлены стили для `.perm-item` с зелёной подсветкой при checked
- Клик по любой строке отдела/подразделения теперь переключает чекбокс

**Статус:** ✅ Исправлено (2026-05-24)

### Проблема: Клик по строке отдела переключает не тот чекбокс

**Причина:** ID чекбоксов генерировались только из названия отдела/подразделения. Если названия отличались только небуквенными символами (например, "IT-отдел" и "IT отдел"), они получали одинаковый ID после `replace(/[^a-zA-Z0-9]/g, '_')`, и label ссылался на неправильный чекбокс.

**Решение:** Добавлен уникальный индекс к ID каждого чекбокса.

**Изменения в коде:**
- `admin.html` (`renderPermissionLists()`): ID теперь формируется как `sub_0_Название` / `otd_0_Название` с индексом

**Было:**
```javascript
const safeId = s.replace(/[^a-zA-Z0-9]/g, '_');
// "IT-отдел" → "IT_отдел"
// "IT отдел" → "IT_отдел"  (дубль!)
```

**Стало:**
```javascript
const safeId = 'sub_' + index + '_' + s.replace(/[^a-zA-Z0-9]/g, '_');
// "IT-отдел" → "sub_0_IT_отдел"
// "IT отдел" → "sub_1_IT_отдел"  (уникально!)
```

**Статус:** ✅ Исправлено (2026-05-24) — клик по любой строке переключает правильный чекбокс

### Проблема: Нет детализации изменений в LFL блоке

**Решение:** Добавлено модальное окно с детализацией изменений при клике на блок "Изменение" в LFL анализе.

**Что показывает модалка:**
- Сводка изменений: начислено %, сотрудники %, часы %
- Таблица по отделам: текущий период, предыдущий период, изменение % (сортировка по абсолютному изменению)
- Топ-20 сотрудников по изменению: ФИО, отдел, текущий, предыдущий, изменение % (сортировка по абсолютному изменению)

**Техническая реализация:**
- Лёгкий вариант без нагрузки на сервер — используется уже загруженный `allData`
- Фильтрация данных на клиенте по датам периодов из кэша `lastLFLData`
- Агрегация по отделам и сотрудникам
- Закрытие по клику вне модалки, по кнопке ✕ или Escape

**Изменения в коде:**
- `dashboard.html`: добавлена HTML модалки, JS функции `openLFLDetails()`, `closeLFLDetails()`, `renderLFLDetails()`
- `dashboard.css`: стили `.modal-overlay`, `.lfl-modal-content`, `.lfl-modal-table`, мобильные стили
- `dashboard.html` (`updateLFLDisplay`): кэширование `lastLFLData = data` для использования в модалке

**Статус:** ✅ Реализовано (2026-05-24) — клик на блок "Изменение" открывает детальную информацию

### Проблема: Горизонтальный скролл в модалке LFL

**Решение:** Увеличена ширина модалки с 900px до 1200px, уменьшены padding в таблицах.

**Изменения в коде:**
- `dashboard.css`: `.lfl-modal-content` max-width: 1200px, width: 95%
- `dashboard.css`: `.lfl-modal-table` th/td padding уменьшен до 10px 12px
- `dashboard.css`: мобильные стили адаптированы под широкую модалку

**Статус:** ✅ Исправлено (2026-05-24) — модалка широкая, таблицы помещаются

### Проблема: Неочевидно, что блок "Изменение" в LFL кликабельный

**Решение:** Добавлен hover-эффект с зелёным свечением на блок "Изменение".

**Изменения в коде:**
- `dashboard.css`: `.lfl-card.lfl-change:hover` — зелёный фон, зелёная рамка, box-shadow свечение, подъём вверх на 3px

**Визуальный результат:**
- При наведении блок подсвечивается приятным зелёным цветом
- Появляется тень `box-shadow: 0 0 25px rgba(0, 255, 136, 0.4)`
- Блок слегка приподнимается (`transform: translateY(-3px)`)
- Курсор меняется на `pointer`

**Статус:** ✅ Улучшено (2026-05-24) — блок "Изменение" интуитивно кликабелен

### Проблема: Модальное окно LFL показывает все данные, игнорируя фильтры

**Причина:** Функция `renderLFLDetails()` фильтровала данные только по датам периодов, но не учитывала выбранные подразделение (`selectedPod`) и отдел (`selectedOtdel`).

**Решение:** Добавлена фильтрация по текущим выбранным фильтрам подразделения и отдела.

**Изменения в коде:**
- `dashboard.html`: добавлена функция `filterData(data, from, to)` которая фильтрует по:
  - Датам периода
  - `selectedPod` (подразделение)
  - `selectedOtdel` (отдел)

**Было:**
```javascript
const curData = allData.filter(r => r.data >= cur.from && r.data <= cur.to);
```

**Стало:**
```javascript
const filterData = (data, from, to) => {
    return data.filter(r => {
        if (r.data < from || r.data > to) return false;
        if (selectedPod && r.podrazdelenie !== selectedPod) return false;
        if (selectedOtdel && r.otdel !== selectedOtdel) return false;
        return true;
    });
};

const curData = filterData(allData, cur.from, cur.to);
const prevData = filterData(allData, prev.from, prev.to);
```

**Статус:** ✅ Исправлено (2026-05-24) — модалка показывает данные с учётом выбранных фильтров

### Проблема: Невозможно выбрать несколько отделов (служб) одновременно

**Решение:** Реализован множественный выбор отделов через toggle-логику кнопок.

**Изменения в коде:**

**Frontend (`dashboard.html`):**
- `selectedOtdel` (строка) → `selectedOtdels` (массив)
- Функция `selectOtdel()` заменена на `toggleOtdel()` — клик добавляет/убирает отдел из выбора
- Кнопка "Все" сбрасывает выбор
- Обновлены все функции фильтрации: `applyFilters()`, `exportData()`, `renderLFLDetails()`
- API запросы теперь передают несколько параметров `selected_otdel`

**Backend (`app.py`):**
- `/api/lfl`: `request.args.get('selected_otdel')` → `request.args.getlist('selected_otdel')`
- `/api/fot/summary`: `request.args.get('otdel')` → `request.args.getlist('otdel')`
- `/api/fot/breakdown`: добавлена поддержка множественных отделов
- SQL-запросы используют `IN (...)` для фильтрации списка отделов

**CSS (`dashboard.css`):**
- Добавлен стиль `.hint` для подсказки о множественном выборе

**Пример использования:**
1. Пользователь кликает "Служба питания" → она выделяется
2. Пользователь кликает "Администрация" → тоже выделяется
3. Данные фильтруются по обоим отделам
4. Клик на уже выбранный отдел — убирает его из фильтра
5. Клик "Все" — сбрасывает все выбранные отделы

**Статус:** ✅ Реализовано (2026-05-24) — можно выбирать несколько отделов одновременно

---

## � Изменения в версии 2.5 (2026-05-24)

### Новые компоненты аналитики ФОТ

#### Backend API
- **`GET /api/fot/summary`** — возвращает суммарные метрики ФОТ за период:
  - `total_money` — всего начислено (₽)
  - `total_hours` — всего часов
  - `employees` — уникальные сотрудники
  - `avg_rate` — средняя ставка
  - `records` — количество записей
  - `series` — временной ряд (по дням/неделям/месяцам)

- **`GET /api/fot/breakdown`** — разбивка ФОТ по структурным единицам:
  - Группировка по: `podrazdelenie` / `otdel` / `dolzhnost`
  - Для каждой группы: money, hours, employees, avg_rate, доля в общей сумме

#### Frontend UI
- **Секция «ФОТ — Обзор»** — KPI-карточки с анимацией:
  - 👥 Сотрудников
  - ⏰ Всего часов
  - 💰 Начислено
  - 📅 Записей

- **Секция «ФОТ по подразделениям»** — интерактивная таблица разбивки по отделам
  - Данные подтягиваются из `/api/fot/breakdown`
  - Обновляются при смене фильтров

- **Анимация LFL-блока** — плавное изменение значений процентов и дельт:
  - Текущий период (анимация)
  - Предыдущий период (анимация)
  - Изменение в % (анимация с + / - знаком)
  - Дельта в ₽ (анимация)

#### Database
- **SQL View `daily_records_agg`** — предварительно агрегированные данные для быстрых запросов
  - Группировка по дате, подразделению, отделу, должности
  - SUM(itogo), SUM(chasy), COUNT(DISTINCT fio)
  - Расположение: `calm-life/tourism/migrations/2026_05_23_add_fot_views.sql`

### Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `app.py` | + `_apply_permission_filters()` helper + `/api/fot/summary` + `/api/fot/breakdown` |
| `dashboard.html` | + блоки «ФОТ — Обзор» и «ФОТ по подразделениям» + обновлённая `animateValue()` + `fetchFotSummaryAndBreakdown()` |
| `dashboard.css` | + стили для `.fot-overview`, `.breakdown-section`, `.section-header` |
| `admin.css` | + улучшенные стили для чекбоксов прав доступа + убран скролл списка отделов |
| `migrations/` | + `2026_05_23_add_fot_views.sql` (View для агрегации) |

### Особенности реализации

- ✅ Учёт прав пользователя в обоих API (подразделения, отделы)
- ✅ Анимация обновления KPI (3-секундный transition)
- ✅ Поддержка фильтров (дата, подразделение, отдел)
- ✅ Гармоничный дизайн, согласованный с существующим дашбордом
- ✅ Мобильная адаптация (responsive grid)
- ✅ Улучшенный UI админ-панели: зелёные чекбоксы для выбранных прав
- ✅ Убран скролл в списке отделов/подразделений для полного отображения

---

## 🛠️ Среда разработки и процесс деплоя

### Инструменты

- **IDE:** Microsoft Visual Studio Code
- **Terminal:** PowerShell 5.1 (Windows)
- **Version Control:** Git (GitHub)
- **Python:** 3.x (через терминал PowerShell)
- **MySQL:** 8.0 (локальная разработка или подключение к удалённой БД)

### Синтаксис команд

Все команды в документации даны в формате **PowerShell** (для совместимости с Windows).

**Примеры:**

```powershell
# Навигация
cd c:\Projects\calm-life\tourism

# Python
python app.py
python -m pip install -r requirements.txt

# Git
git add .
git commit -m "Add FOT analytics API endpoints"
git push origin main

# MySQL
mysql -u root -p -e "SHOW DATABASES;"
```

**Для Linux/Mac (bash):** используйте эквивалентные команды (`python3` вместо `python`, `cd` прямо без пути).

### Процесс деплоя

```
┌─────────────────────────────────────────────────────────────┐
│  1️⃣  Локальная разработка (MS VS Code + PowerShell)        │
│    ├─ Редактирование файлов (app.py, dashboard.html, css)  │
│    ├─ Тестирование локально (python app.py)                │
│    └─ Проверка в браузере (http://localhost:5000)          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│  2️⃣  Коммит и Push в GitHub (локально)                     │
│    ├─ git add .                                             │
│    ├─ git commit -m "Description of changes"               │
│    └─ git push origin main                                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│  3️⃣  Деплой на production сервер                            │
│    ├─ SSH подключение                                       │
│    ├─ cd /var/www/calm-life                                │
│    ├─ git pull origin main                                 │
│    ├─ (если нужна миграция БД)                            │
│    │  mysql -u tourism -p daily_tourism < migrations/...   │
│    ├─ sudo systemctl restart tourism-dashboard             │
│    └─ sudo systemctl reload nginx                          │
└─────────────────────────────────────────────────────────────┘
```

### Пример полного цикла (PowerShell)

```powershell
# === На локальной машине ===

# 1. Открыть проект в VS Code
cd c:\Projects\calm-life
code .

# 2. После редактирования файлов — тестирование локально
cd tourism
python app.py
# Проверить в браузере: http://localhost:5000

# 3. Коммит и push
git add .
git commit -m "Add FOT summary and breakdown analytics"
git push origin main
# Ввести GitHub credentials если требуется

# === На production сервере (по SSH) ===
# ssh -i C:\Users\Роман\.ssh\id_ed25519 kalianu@158.160.210.143

# 1. Обновить код
cd /var/www/calm-life
git pull origin main

# 2. Если были изменения в БД (миграции)
mysql -u tourism -p daily_tourism < tourism/migrations/2026_05_23_add_fot_views.sql

# 3. Если были изменения в Python зависимостях
cd tourism
source venv/bin/activate
pip install -r requirements.txt

# 4. Перезапустить сервис
sudo systemctl restart tourism-dashboard
sudo systemctl reload nginx

# 5. Проверить статус
sudo systemctl status tourism-dashboard
```

### Важные правила

1. **Все правки производятся локально** — не редактируйте файлы напрямую на сервере
2. **Только через Git** — используйте git для синхронизации кода
3. **Миграции БД** — перед деплоем проверьте, есть ли `.sql` файлы в `migrations/`
4. **Тестируйте локально** — убедитесь, что код работает перед пушем в GitHub
5. **Логируйте изменения** — в коммит-сообщение помещайте подробное описание
6. **Коммиты на русском языке** — все сообщения коммитов (`git commit -m "..."`) должны быть на русском языке:
   - ✅ Правильно: `git commit -m "Добавлена модалка детализации LFL"`
   - ❌ Неправильно: `git commit -m "Added LFL details modal"`

---

## �📝 Следующие шаги (Roadmap)

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

**Последнее обновление:** 2026-05-24 (Множественный выбор отделов в фильтрах, исправлена фильтрация в модалке LFL)  
**Версия:** 2.5.7  
**Статус:** ✅ Production Ready

---

## 🤖 Автоматизация процесса загрузки данных

### Текущий ручной процесс

```
Google Sheets (16 книг) → Power Query (Excel) → Штатное расписание → Архив → Админ-панель → Дашборд
```

**Шаги:**
1. С 16 книг Google Sheets через Power Query (Excel) собираются данные по табелям сотрудников
2. В Power Query преобразование в строчный вид (Unpivot)
3. В Excel подстановка значений ставок из листа штатного расписания
4. Расчет "Начислено" = Часы × Ставка
5. Копирование с листа "Реестр" на лист "Архив"
6. Заливка изменений через Админ-панель на дашборд

---

### Анализ Power Query скрипта (convert_tabel.pq)

**Операции:**
| Операция | Power Query | Python аналог |
|----------|-------------|---------------|
| Подключение к Google Sheets | `Excel.Workbook(Web.Contents(url))` | `pd.read_excel(url)` |
| Пропуск 2 строк | `Table.Skip(2)` | `df.iloc[2:]` |
| Повышение заголовков | `Table.PromoteHeaders()` | `df.columns = df.iloc[0]` |
| Фильтрация пустых строк | `Table.SelectRows()` | `df[df['Column1'].notna()]` |
| Unpivot (свертывание дат) | `Table.UnpivotOtherColumns()` | `df.melt()` |
| Фильтрация служебных строк | `Table.SelectRows()` | `df[~df['Дата'].str.contains('Column')]` |
| Преобразование типов | `Table.TransformColumnTypes()` | `df.astype({'Дата': 'datetime'})` |
| Переименование | `Table.RenameColumns()` | `df.rename(columns={...})` |

---

### Предложенные варианты автоматизации

#### Вариант 1: Python + Google Sheets API (Рекомендуется ⭐)

**Архитектура:**
```
Google Sheets → Google Sheets API → Python скрипт → MySQL → Дашборд
```

**Компоненты:**
- `tourism_automation.py` — основной скрипт обработки
- `google_credentials.json` — OAuth2 credentials (секретный)
- Планировщик задач (cron / Task Scheduler)

**Плюсы:**
- ✅ Прямой доступ к Google Sheets без Excel
- ✅ Power Query не нужен
- ✅ Полный контроль над логикой обработки
- ✅ Можно добавить валидацию и логи
- ✅ Работает на сервере без GUI
- ✅ Бесплатно

**Минусы:**
- ❌ Нужно настроить OAuth2 credentials
- ❌ Требует разработки дополнительного скрипта

**Файлы для создания:**
```
calm-life/tourism/
├── tourism_automation.py      # Основной скрипт автоматизации
├── google_credentials.json     # OAuth credentials (добавить в .gitignore)
├── requirements.txt            # Зависимости (google-api-python-client, pandas, mysql-connector-python)
└── logs/
    └── automation.log          # Логи выполнения
```

**План реализации:**
1. Создать сервисный аккаунт Google Cloud
2. Дать доступ к Google Sheets (share с сервисным аккаунтом)
3. Написать скрипт обработки (аналог Power Query на pandas)
4. Настроить планировщик задач (ежедневно в 18:00)
5. Добавить логирование и email-алерты при ошибках

---

#### Вариант 2: Google Apps Script + Webhook

**Архитектура:**
```
Google Sheets → Apps Script (триггер) → Webhook (Flask API) → MySQL
```

**Плюсы:**
- ✅ Работает внутри Google Sheets
- ✅ Триггеры на события (при изменении)
- ✅ Не нужен отдельный сервер для скрипта

**Минусы:**
- ❌ Ограничения выполнения (max 6 мин)
- ❌ Сложнее отладка
- ❌ Меньше гибкости в логике

---

#### Вариант 3: Power Automate / Zapier (No-code)

**Архитектура:**
```
Google Sheets → Power Automate → HTTP Request → Flask API → MySQL
```

**Плюсы:**
- ✅ Визуальный конструктор
- ✅ Быстрая настройка
- ✅ Не нужен код

**Минусы:**
- ❌ Платные подписки
- ❌ Ограничения по количеству вызовов
- ❌ Меньше контроля

---

#### Вариант 4: Гибридный (Excel + Python монитор)

**Архитектура:**
```
Google Sheets → Power Query (автоматически) → Excel файл → Python монитор → MySQL
```

**Плюсы:**
- ✅ Сохраняется текущий процесс с Excel
- ✅ Python только мониторит изменения

**Минусы:**
- ❌ Требуется Excel на сервере
- ❌ Мониторинг файлов менее надежен

---

### Вопросы для проработки (TODO)

- [ ] **Структура штатного расписания:** Какие колонки? (СНИЛС, ФИО, Ставка, Должность...)
- [ ] **Формула расчета:** `Начислено = Часы × Ставка`? Коэффициенты СП/НСП?
- [ ] **16 книг:** Все в одинаковом формате? Список URL-ов?
- [ ] **Архив:** Нужно ли накапливать исторические данные?
- [ ] **Google Sheets API:** Готовность настроить сервисный аккаунт?
- [ ] **Выбор варианта:** Какой вариант автоматизации реализуем?

---

### Текущий статус автоматизации

**Статус:** 📋 Планирование (не реализовано)  
**Приоритет:** Средний  
**Следующий шаг:** Обсудить вопросы выше и выбрать вариант