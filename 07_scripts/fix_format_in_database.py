#!/usr/bin/env python3
"""
Исправление форматов в уже загруженных данных в PostgreSQL
Обновляет format для паблишеров с неправильно определенным форматом
"""
import pandas as pd
import sys
import io
import re
from sqlalchemy import create_engine, text
from db_utils import get_postgres_connection_string

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("ИСПРАВЛЕНИЕ ФОРМАТОВ В БАЗЕ ДАННЫХ")
print("=" * 80)
print()

def extract_format_improved(publisher_str):
    """Улучшенная функция определения формата"""
    name_upper = str(publisher_str).upper()
    
    # Проверяем форматы в правильном порядке - сначала более специфичные
    # POP - проверяем перед PUSH, чтобы перехватить "-POP" раньше
    if re.search(r'-POP\b|POP-|POP\s|POP$', name_upper):
        return 'POP'
    # BANNER - проверяем первым среди остальных, так как может быть в конце названия
    elif re.search(r'-BANNER\b|BANNER-|BANNER\s|BANNER$', name_upper):
        return 'BANNER'
    # VIDEO - проверяем перед PUSH
    elif re.search(r'-VIDEO\b|VIDEO-|VIDEO\s|VIDEO$', name_upper):
        return 'VIDEO'
    # PUSH - проверяем последним, исключая случаи где PUSH внутри слова
    # Ищем PUSH только как отдельное слово (после/перед дефисом или пробелом)
    elif (re.search(r'-PUSH\b|PUSH-|PUSH\s|PUSH$|IN-PAGE|INPAGE', name_upper) and 
          not re.search(r'[A-Z]PUSH[A-Z]', name_upper)):  # Исключаем PUSH внутри слова
        return 'PUSH'
    # NATIVE
    elif re.search(r'-NATIVE\b|NATIVE-|NATIVE\s|NATIVE$', name_upper):
        return 'NATIVE'
    else:
        return 'OTHER'

# Connect to PostgreSQL
print("1. Подключение к PostgreSQL...")
pg_uri = get_postgres_connection_string()
engine = create_engine(pg_uri)
print("   ✓ Подключено")
print()

# Get all unique publishers with their names
print("2. Загрузка данных о паблишерах...")
print()

# Check both tables
tables_to_fix = ['publisher_spend', 'publisher_spend_daily']

for table_name in tables_to_fix:
    print(f"3. Проверка таблицы {table_name}...")
    print()
    
    try:
        # Get all unique publisher_name entries
        query = f"""
        SELECT DISTINCT publisher_id, publisher_name, format
        FROM {table_name}
        WHERE publisher_name IS NOT NULL
        ORDER BY publisher_id;
        """
        
        df = pd.read_sql(query, engine)
        
        if len(df) == 0:
            print(f"   Таблица {table_name} пуста или не существует, пропускаю...")
            print()
            continue
        
        print(f"   Найдено уникальных паблишеров: {len(df)}")
        print()
        
        # Recalculate format for each publisher
        print("4. Пересчет форматов...")
        print()
        
        updates = []
        changes = []
        
        for idx, row in df.iterrows():
            publisher_id = row['publisher_id']
            publisher_name = row['publisher_name']
            old_format = row['format']
            
            # Calculate new format
            new_format = extract_format_improved(publisher_name)
            
            if old_format != new_format:
                changes.append({
                    'publisher_id': publisher_id,
                    'publisher_name': publisher_name,
                    'old_format': old_format,
                    'new_format': new_format
                })
                updates.append({
                    'publisher_id': publisher_id,
                    'new_format': new_format
                })
        
        if len(changes) > 0:
            print(f"   Найдено несоответствий: {len(changes)}")
            print()
            print("   Примеры изменений:")
            for change in changes[:10]:  # Show first 10
                print(f"   - Publisher {change['publisher_id']}: '{change['publisher_name']}'")
                print(f"     {change['old_format']} → {change['new_format']}")
            if len(changes) > 10:
                print(f"   ... и еще {len(changes) - 10} изменений")
            print()
            
            # Update database
            print("5. Обновление базы данных...")
            print()
            
            with engine.connect() as conn:
                for update in updates:
                    update_sql = text(f"""
                        UPDATE {table_name}
                        SET format = :new_format
                        WHERE publisher_id = :publisher_id
                    """)
                    conn.execute(update_sql, {
                        'new_format': update['new_format'],
                        'publisher_id': update['publisher_id']
                    })
                conn.commit()
            
            print(f"   ✓ Обновлено записей: {len(updates)}")
            print()
            
            # Verify
            print("6. Проверка результатов...")
            print()
            
            verify_query = f"""
            SELECT format, COUNT(*) as count
            FROM {table_name}
            GROUP BY format
            ORDER BY format;
            """
            
            verify_df = pd.read_sql(verify_query, engine)
            print("   Распределение по форматам:")
            for _, row in verify_df.iterrows():
                print(f"     {row['format']}: {row['count']} записей")
            print()
        else:
            print("   ✓ Все форматы корректны, изменений не требуется")
            print()
    
    except Exception as e:
        print(f"   ✗ Ошибка при обработке таблицы {table_name}: {e}")
        print()
        continue

print("=" * 80)
print("ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
print("=" * 80)
print()
print("Теперь форматы определены корректно:")
print("  - RealPush-UGW-Banner → BANNER (не PUSH)")
print("  - Pushub-UGW-Video → VIDEO (не PUSH)")
print("  - И другие подобные случаи")
print()

