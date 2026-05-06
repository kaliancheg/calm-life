#!/bin/bash
# Скрипт автоматической установки Tourism Dashboard на сервер

set -e

echo "=========================================="
echo "Tourism Dashboard - Установка на сервер"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Ошибка: Запустите скрипт от имени root (sudo ./deploy.sh)${NC}"
    exit 1
fi

# Переменные
PROJECT_NAME="calm-life"
PROJECT_PATH="/var/www/$PROJECT_NAME"
TOURISM_PATH="$PROJECT_PATH/tourism"
LOG_DIR="/var/log/tourism-dashboard"
VENV_PATH="$TOURISM_PATH/venv"

echo -e "${GREEN}Шаг 1/8: Создание директорий...${NC}"
mkdir -p "$TOURISM_PATH"
mkdir -p "$LOG_DIR"
chown -R www-data:www-data "$LOG_DIR"

echo -e "${GREEN}Шаг 2/8: Клонирование репозитория...${NC}"
if [ -d "$PROJECT_PATH/.git" ]; then
    cd "$PROJECT_PATH"
    git pull origin main
else
    echo -e "${YELLOW}Репозиторий не найден. Клонируем...${NC}"
    echo -e "${YELLOW}Пожалуйста, вручную выполните:${NC}"
    echo -e "${YELLOW}  cd /var/www && git clone https://github.com/kaliancheg/$PROJECT_NAME.git${NC}"
    echo -e "${YELLOW}  cd $PROJECT_PATH && git pull origin main${NC}"
    exit 1
fi

echo -e "${GREEN}Шаг 3/8: Установка Python зависимостей...${NC}"
cd "$TOURISM_PATH"
python3 -m venv "$VENV_PATH"
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install -r requirements.txt

echo -e "${GREEN}Шаг 4/8: Настройка базы данных...${NC}"
echo -e "${YELLOW}Проверьте, что база данных 'daily_tourism' создана:${NC}"
echo -e "${YELLOW}  mysql -u root -p -e 'CREATE DATABASE daily_tourism;'${NC}"
echo -e "${YELLOW}Затем выполните миграции:${NC}"
echo -e "${YELLOW}  mysql -u root -p daily_tourism < $TOURISM_PATH/migrations/update_schema.sql${NC}"
read -p "База данных настроена? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Отмена. Настройте БД и запустите скрипт заново.${NC}"
    exit 0
fi

echo -e "${GREEN}Шаг 5/8: Создание администратора...${NC}"
echo -e "${YELLOW}Запустите вручную:${NC}"
echo -e "${YELLOW}  cd $TOURISM_PATH${NC}"
echo -e "${YELLOW}  source venv/bin/activate${NC}"
echo -e "${YELLOW}  python create_admin.py${NC}"

echo -e "${GREEN}Шаг 6/8: Настройка логов...${NC}"
touch "$LOG_DIR/error.log" "$LOG_DIR/access.log"
chown www-data:www-data "$LOG_DIR"/*.log

echo -e "${GREEN}Шаг 7/8: Установка systemd сервиса...${NC}"
cp "$TOURISM_PATH/tourism-dashboard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable tourism-dashboard

echo -e "${GREEN}Шаг 8/8: Настройка Nginx...${NC}"
echo -e "${YELLOW}Скопируйте конфигурацию Nginx:${NC}"
echo -e "${YELLOW}  cp $TOURISM_PATH/nginx.conf /etc/nginx/sites-available/calm-life${NC}"
echo -e "${YELLOW}  ln -s /etc/nginx/sites-available/calm-life /etc/nginx/sites-enabled/${NC}"
echo -e "${YELLOW}  nginx -t && systemctl reload nginx${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo -e "Установка завершена!"
echo -e "==========================================${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo "1. Настройте базу данных (если ещё не сделано)"
echo "2. Создайте администратора: python create_admin.py"
echo "3. Настройте Nginx (см. выше)"
echo "4. Запустите сервис: systemctl start tourism-dashboard"
echo "5. Проверьте статус: systemctl status tourism-dashboard"
echo ""
echo -e "${GREEN}Доступ: http://calm-life.ru/dashboard.html${NC}"
echo -e "${GREEN}Логин/Пароль: admin / admin123 (измените после входа!)${NC}"
echo ""
