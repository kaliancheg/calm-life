#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки состояния системы

Запуск:
    python check_system.py

Проверяет:
    - Подключение к MySQL
    - Существование необходимых таблиц
    - Наличие миграций
    - Создание тестовых данных (опционально)
"""

import sys
import mysql.connector
from datetime import datetime

# Для корректного отображения кириллицы в Windows
import codecs
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

def check_connection():
    """Проверка подключения к MySQL"""
    print("Подключение к MySQL...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT VERSION()')
        version = cursor.fetchone()[0]
        print(f"OK: MySQL {version} подключен")
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as e:
        print(f"ERROR: Ошибка подключения: {e}")
        return False

def check_tables():
    """Проверка существования таблиц"""
    print("\nПроверка таблиц...")
    required_tables = [
        'users', 'records', 'permissions', 
        'permissions_subdivisions', 'permissions_otdels',
        'audit_log', 'roles'
    ]
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute('SHOW TABLES')
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_ok = True
        for table in required_tables:
            if table in existing_tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"  OK: {table}: {count} записей")
            else:
                print(f"  ERROR: {table}: НЕ НАЙДЕНА")
                all_ok = False
        
        cursor.close()
        conn.close()
        return all_ok
        
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")
        return False

def check_admin_user():
    """Проверка наличия администратора"""
    print("\nПроверка администратора...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT username, full_name, role, is_active 
            FROM users WHERE role = 'admin' AND is_active = TRUE
        ''')
        admins = cursor.fetchall()
        
        if admins:
            print(f"OK: Найдено {len(admins)} администратора(ов):")
            for admin in admins:
                print(f"   - {admin['username']} ({admin['full_name']})")
        else:
            print("ERROR: Администраторы не найдены!")
            print("   Запустите: python create_admin.py")
        
        cursor.close()
        conn.close()
        return len(admins) > 0
        
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")
        return False

def check_permissions_structure():
    """Проверка структуры прав"""
    print("\nПроверка структуры прав...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Проверка таблицы permissions
        cursor.execute('DESCRIBE permissions')
        cols = [row[0] for row in cursor.fetchall()]
        required = ['user_id', 'can_view_all', 'can_export']
        if all(col in cols for col in required):
            print("  OK: Таблица permissions")
        else:
            print(f"  ERROR: Таблица permissions: Нехватает колонок {set(required) - set(cols)}")
        
        # Проверка таблицы permissions_subdivisions
        cursor.execute('DESCRIBE permissions_subdivisions')
        cols = [row[0] for row in cursor.fetchall()]
        if 'user_id' in cols and 'subdivision' in cols:
            print("  OK: Таблица permissions_subdivisions")
        else:
            print("  ERROR: Таблица permissions_subdivisions")
        
        # Проверка таблицы permissions_otdels
        cursor.execute('DESCRIBE permissions_otdels')
        cols = [row[0] for row in cursor.fetchall()]
        if 'user_id' in cols and 'otdel' in cols:
            print("  OK: Таблица permissions_otdels")
        else:
            print("  ERROR: Таблица permissions_otdels")
        
        # Проверка audit_log
        cursor.execute('DESCRIBE audit_log')
        cols = [row[0] for row in cursor.fetchall()]
        required = ['user_id', 'action', 'resource', 'created_at']
        if all(col in cols for col in required):
            print("  OK: Таблица audit_log")
        else:
            print(f"  ERROR: Таблица audit_log: Нехватает колонок {set(required) - set(cols)}")
        
        cursor.close()
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")
        return False

def create_sample_data():
    """Создание тестовых данных"""
    print("\nСоздание тестовых данных...")
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Проверка наличия данных
        cursor.execute('SELECT COUNT(*) FROM records')
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"   INFO: Уже есть {count} записей в records")
        else:
            print("   WARN: Таблица records пуста")
            response = input("   Создать тестовые данные? (y/n): ").strip().lower()
            
            if response == 'y':
                test_data = [
                    ('Иванов Иван Иванович', '123-456-789 01', 'Подразделение 1', 'Отдел А', 'Менеджер', '2024-01-15', 8, 5000, 5000),
                    ('Петров Петр Петрович', '987-654-321 02', 'Подразделение 2', 'Отдел Б', 'Разработчик', '2024-01-15', 8, 7000, 7000),
                    ('Сидорова Анна Сергеевна', '456-789-123 03', 'Подразделение 1', 'Отдел А', 'Аналитик', '2024-01-16', 6, 3750, 3750),
                ]
                
                cursor.executemany('''
                    INSERT INTO records (fio, snils, podrazdelenie, otdel, dolzhnost, data, chasy, nachisleno, itogo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', test_data)
                conn.commit()
                print(f"   OK: Создано {len(test_data)} тестовых записей")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"ERROR: {e}")

def main():
    print("="*60)
    print("Проверка системы Волна")
    print("="*60)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Проверка подключения
    if not check_connection():
        print("\nERROR: Невозможно продолжить без подключения к БД")
        sys.exit(1)
    
    # Проверка таблиц
    check_tables()
    
    # Проверка структуры прав
    check_permissions_structure()
    
    # Проверка администратора
    check_admin_user()
    
    print("\n" + "="*60)
    print("INFO: Следующие шаги:")
    print("  1. Если нет администратора: python create_admin.py")
    print("  2. Если нет данных: заполните через импорт Excel")
    print("  3. Запустите сервер: python app.py")
    print("  4. Откройте: http://localhost:5000")
    print("="*60)

if __name__ == '__main__':
    main()
