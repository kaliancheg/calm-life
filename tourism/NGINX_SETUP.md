# Интеграция с Nginx

## Готовая конфигурация

Файл `nginx.conf` содержит **полную конфигурацию** для вашего сервера, которая:

✅ Отдаёт лендинг по `/` (статические файлы из корня сайта)  
✅ Проксирует `/dashboard.html` на Flask (порт 5000)  
✅ Проксирует `/health` на Xray (порт 4000)  
✅ Использует SSL/TLS (Let's Encrypt)  
✅ Редирект HTTP → HTTPS  

## Установка (полная замена конфига)

```bash
# Скопировать конфиг
sudo cp /var/www/calm-life/tourism/nginx.conf /etc/nginx/sites-available/calm-life

# Проверить синтаксис
sudo nginx -t

# Перезагрузить Nginx
sudo systemctl reload nginx
```

## Установка (добавить в существующий конфиг)

Если вы хотите сохранить текущую конфигурацию, добавьте только этот блок в ваш существующий конфиг Nginx (внутри `server { }`):

```nginx
# Дашборд - проксирование на Flask/Gunicorn
location /dashboard.html {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

## Проверка работы

После настройки проверьте:

```bash
# Проверка синтаксиса Nginx
sudo nginx -t

# Проверка статуса сервиса
sudo systemctl status nginx

# Просмотр логов (если есть проблемы)
sudo tail -f /var/log/nginx/calm-life-error.log
```

## Доступы

- **Лендинг:** https://calm-life.ru/
- **Дашборд:** https://calm-life.ru/dashboard.html
- **Health check:** https://calm-life.ru/health
