#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания первого администратора системы

Запуск:
    python create_admin.py

Параметры (опционально):
    --username <логин>
    --password <пароль>
    --full-name <ФИО>
"""

import sys
import mysql.connector
import bcrypt
import argparse
import codecs

# Для корректного отображения кириллицы в Windows
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Конфигурация БД (совпадает с app.py)
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root123',  # Измените на ваш пароль MySQL
    'database': 'daily_tourism',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
}

def create_admin(username='admin', password='admin123', full_name='Администратор'):
    """Создание пользователя администратора"""
    try:
        # Проверка подключения к БД
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Проверка существования пользователя
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            print(f"WARN: Пользователь '{username}' уже существует")
            response = input("Хотите обновить пароль? (y/n): ").strip().lower()
            if response == 'y':
                # Обновление пароля
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cursor.execute('''
                    UPDATE users SET password_hash = %s, role = 'admin', is_active = TRUE 
                    WHERE username = %s
                ''', (password_hash, username))
                conn.commit()
                print(f"OK: Пароль пользователя '{username}' обновлен")
            else:
                print("CANCEL: Отменено")
                cursor.close()
                conn.close()
                return
        else:
            # Создание нового пользователя
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (%s, %s, %s, 'admin', TRUE)
            ''', (username, password_hash, full_name))
            conn.commit()
            print(f"OK: Администратор '{username}' успешно создан")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("DATA: Данные для входа:")
        print(f"   Логин: {username}")
        print(f"   Пароль: {password}")
        print("="*60)
        print("\nIMPORTANT: Измените пароль после первого входа!")
        print("INFO: Откройте http://localhost:5000/admin/profile\n")
        
    except mysql.connector.Error as e:
        print(f"ERROR: Ошибка БД: {e}")
        print("\nПроверьте:")
        print("  1. MySQL запущен")
        print("  2. Верны параметры подключения в MYSQL_CONFIG")
        print("  3. База данных 'daily_tourism' создана")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Ошибка: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Создание администратора системы')
    parser.add_argument('--username', default='admin', help='Логин администратора')
    parser.add_argument('--password', default='admin123', help='Пароль администратора')
    parser.add_argument('--full-name', default='Администратор', help='ФИО администратора')
    
    args = parser.parse_args()
    
    print("="*60)
    print("ADMIN: Создание администратора системы")
    print("="*60)
    print(f"LOGINS: Логин: {args.username}")
    print(f"INFO: ФИО: {args.full_name}")
    print("="*60)
    print()
    
    create_admin(args.username, args.password, args.full_name)

if __name__ == '__main__':
    main()
