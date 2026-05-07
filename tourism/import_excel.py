#!/usr/bin/env python3
"""
Скрипт для импорта данных из Excel файла в базу данных Tourism Dashboard
Поддерживает формат файла: Табель_ежедневный_туризм.xlsx, лист "Реестр"
"""

import pandas as pd
import mysql.connector
import sys
import os
from datetime import datetime

# Конфигурация базы данных
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'tourism',
    'password': 'tourism123',
    'database': 'daily_tourism',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

def parse_excel(file_path, sheet_name='Реестр'):
    """Читает Excel файл и возвращает DataFrame"""
    try:
        print(f"📖 Чтение файла: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"✅ Найдено строк: {len(df)}")
        return df
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return None

def map_columns(df):
    """Преобразует колонки Excel в формат базы данных"""
    # Названия колонок в Excel (предполагаемые)
    column_mapping = {
        'ФИО': 'fio',
        'СНИЛС': 'snils',
        'Подразделение': 'podrazdelenie',
        'Отдел': 'otdel',
        'Должность': 'dolzhnost',
        'Дата': 'data',
        'Часы': 'chasy',
        'Начислено': 'nachisleno',
        'Итого': 'itogo'
    }
    
    # Проверяем наличие колонок
    missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
    if missing_cols:
        print(f"⚠️  Предупреждение: отсутствуют колонки: {missing_cols}")
        print(f"📋 Доступные колонки: {list(df.columns)}")
    
    # Переименовываем колонки
    df_renamed = df.rename(columns={v: k for k, v in column_mapping.items() if v in df.columns})
    
    return df_renamed

def insert_records(df):
    """Вставляет данные в базу данных"""
    if df is None or df.empty:
        print("❌ Нет данных для импорта")
        return 0, 0
    
    conn = None
    cursor = None
    inserted = 0
    skipped = 0
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        for idx, row in df.iterrows():
            try:
                # Преобразуем дату
                data = row.get('data')
                if pd.isna(data):
                    print(f"⚠️  Пропуск строки {idx+2}: отсутствует дата")
                    skipped += 1
                    continue
                
                # Преобразуем в формат date
                if isinstance(data, datetime):
                    data_str = data.strftime('%Y-%m-%d')
                else:
                    data_str = str(data)
                
                # Получаем значения
                fio = str(row.get('fio', '')).strip()
                snils = str(row.get('snils', '')).strip() if pd.notna(row.get('snils')) else None
                podrazdelenie = str(row.get('podrazdelenie', '')).strip() if pd.notna(row.get('podrazdelenie')) else None
                otdel = str(row.get('otdel', '')).strip() if pd.notna(row.get('otdel')) else None
                dolzhnost = str(row.get('dolzhnost', '')).strip() if pd.notna(row.get('dolzhnost')) else None
                chasy = float(row.get('chasy', 0)) if pd.notna(row.get('chasy')) else 0.0
                nachisleno = float(row.get('nachisleno', 0)) if pd.notna(row.get('nachisleno')) else 0.0
                itogo = float(row.get('itogo', 0)) if pd.notna(row.get('itogo')) else 0.0
                
                if not fio:
                    print(f"⚠️  Пропуск строки {idx+2}: отсутствует ФИО")
                    skipped += 1
                    continue
                
                # Вставляем запись
                query = """
                    INSERT INTO records 
                    (fio, snils, podrazdelenie, otdel, dolzhnost, data, chasy, nachisleno, itogo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    chasy = VALUES(chasy),
                    nachisleno = VALUES(nachisleno),
                    itogo = VALUES(itogo)
                """
                
                cursor.execute(query, (
                    fio, snils, podrazdelenie, otdel, dolzhnost, 
                    data_str, chasy, nachisleno, itogo
                ))
                inserted += 1
                
                if (idx + 1) % 100 == 0:
                    print(f"📊 Импорт: {idx+1} строк обработано...")
                    
            except Exception as row_error:
                print(f"❌ Ошибка строки {idx+2}: {row_error}")
                skipped += 1
                continue
        
        conn.commit()
        print(f"\n✅ Импорт завершен!")
        print(f"   Добавлено записей: {inserted}")
        print(f"   Пропущено: {skipped}")
        
        return inserted, skipped
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return 0, skipped
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def main():
    """Основная функция"""
    print("="*60)
    print("Импорт данных из Excel в Tourism Dashboard")
    print("="*60)
    
    # Проверяем аргументы командной строки
    if len(sys.argv) < 2:
        print("\nИспользование: python import_excel.py <путь_к_файлу.xlsx>")
        print("\nПример:")
        print("  python import_excel.py C:/Users/Roman/Downloads/Табель.xlsx")
        print("  python import_excel.py /home/user/data/Табель.xlsx")
        print("\nФормат Excel файла:")
        print("  - Лист: 'Реестр'")
        print("  - Колонки: ФИО, СНИЛС, Подразделение, Отдел, Должность, Дата, Часы, Начислено, Итого")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        sys.exit(1)
    
    # Проверяем расширение файла
    if not file_path.lower().endswith(('.xlsx', '.xls')):
        print(f"❌ Неверный формат файла. Используйте .xlsx или .xls")
        sys.exit(1)
    
    # Читаем Excel
    df = parse_excel(file_path)
    if df is None:
        sys.exit(1)
    
    # Преобразуем колонки
    df_mapped = map_columns(df)
    
    # Вставляем в БД
    inserted, skipped = insert_records(df_mapped)
    
    if inserted > 0:
        print(f"\n🎉 Успешно импортировано {inserted} записей!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Ни одна запись не импортирована")
        sys.exit(1)

if __name__ == '__main__':
    main()
