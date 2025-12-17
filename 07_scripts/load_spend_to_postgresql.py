#!/usr/bin/env python3
"""
Загрузка данных о расходах (spend) из CSV в PostgreSQL для использования в Superset
"""
import pandas as pd
import sys
import io
import re
import os
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from db_utils import get_postgres_connection_string

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("ЗАГРУЗКА ДАННЫХ О РАСХОДАХ В POSTGRESQL")
print("=" * 80)
print()

# Function to extract publisher_id and format
def extract_publisher_id(publisher_str):
    match = re.match(r'\((\d+)\)', str(publisher_str))
    if match:
        return int(match.group(1))
    return None

def extract_format(publisher_str):
    """Extract ad format from publisher name with improved logic"""
    name_upper = str(publisher_str).upper()
    
    # Используем регулярные выражения для более точного определения формата
    # Ищем формат после дефиса или в конце названия (например, "-PUSH", "PUSH-Premium", "UGW-VIDEO")
    
    # Используем более строгие паттерны - формат должен быть отдельным словом
    # после дефиса, перед дефисом, или в конце, но НЕ внутри другого слова
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

# Load spend data
print("1. Загружаю данные по расходам...")
print()

# Get month from command line argument or use default
parser = argparse.ArgumentParser(description='Load spend data to PostgreSQL')
parser.add_argument('--csv', type=str, help='Path to CSV file', default=None)
parser.add_argument('--month', type=str, help='Month in format YYYY-MM (e.g., 2025-11)', default=None)
parser.add_argument('--daily', action='store_true', help='Load daily data instead of monthly')
args = parser.parse_args()

# Try multiple paths
if args.csv:
    csv_paths = [args.csv]
else:
    csv_paths = [
        '/data/spend_november.csv',  # Docker path
        'data/spend_november.csv',   # Relative path
        'C:/Users/Nalivator3000/Downloads/export (1).csv'  # Windows local path
    ]

csv_path = None
for path in csv_paths:
    if os.path.exists(path):
        csv_path = path
        break

if csv_path is None:
    print(f"ERROR: CSV файл не найден. Проверьте следующие пути:")
    for path in csv_paths:
        print(f"  - {path}")
    print()
    print("Использование:")
    print("  python load_spend_to_postgresql.py --csv path/to/file.csv --month 2025-11")
    print("  python load_spend_to_postgresql.py --csv path/to/file.csv --month 2025-10 --daily")
    sys.exit(1)

spend_data = pd.read_csv(csv_path, skiprows=1)
spend_data['publisher_id'] = spend_data['Publisher'].apply(extract_publisher_id)
spend_data['format'] = spend_data['Publisher'].apply(extract_format)

# Keep only relevant columns
spend_data = spend_data[['publisher_id', 'Publisher', 'format', 'Deposit', 'Spend']].copy()
spend_data.columns = ['publisher_id', 'publisher_name', 'format', 'deposits_reported', 'spend']

# Remove rows with missing publisher_id
spend_data = spend_data.dropna(subset=['publisher_id'])

# Convert to numeric
for col in ['deposits_reported', 'spend']:
    spend_data[col] = pd.to_numeric(spend_data[col], errors='coerce').fillna(0)

# Calculate CPA
spend_data['current_cpa'] = (spend_data['spend'] / spend_data['deposits_reported'].replace(0, 1)).round(3)

# Determine month from argument or filename or default
if args.month:
    month = args.month
elif 'november' in csv_path.lower() or 'nov' in csv_path.lower():
    month = '2025-11'
elif 'october' in csv_path.lower() or 'oct' in csv_path.lower():
    month = '2025-10'
else:
    month = '2025-11'  # Default

spend_data['month'] = month

print(f"   Загружено: {len(spend_data)} записей")
print(f"   Месяц: {month}")
print()

# Connect to PostgreSQL
print("2. Подключение к PostgreSQL...")
pg_uri = get_postgres_connection_string()
engine = create_engine(pg_uri)

if args.daily:
    # Create table for daily spend data
    print("3. Создание таблицы publisher_spend_daily...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS publisher_spend_daily (
        id SERIAL PRIMARY KEY,
        publisher_id BIGINT NOT NULL,
        publisher_name VARCHAR(255),
        format VARCHAR(50),
        date DATE NOT NULL,
        deposits_reported INTEGER,
        spend NUMERIC(15, 2),
        current_cpa NUMERIC(10, 3),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(publisher_id, date)
    );

    CREATE INDEX IF NOT EXISTS idx_publisher_spend_daily_publisher_id ON publisher_spend_daily(publisher_id);
    CREATE INDEX IF NOT EXISTS idx_publisher_spend_daily_format ON publisher_spend_daily(format);
    CREATE INDEX IF NOT EXISTS idx_publisher_spend_daily_date ON publisher_spend_daily(date);
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("   Таблица создана/обновлена")
    print()
    
    # For daily data, you need to have date column in CSV or split monthly data
    # This is a placeholder - you'll need to adapt based on your CSV structure
    print("   ВНИМАНИЕ: Для дневных данных нужна колонка 'date' в CSV или разделение данных по дням")
    print("   Пока загружаем как месячные данные...")
    print()
    
    # Convert month to date range (first day of month)
    month_date = datetime.strptime(month, '%Y-%m')
    spend_data['date'] = month_date.date()
    
    # Load data to PostgreSQL
    print("4. Загрузка дневных данных в PostgreSQL...")
    spend_data_db = spend_data[['publisher_id', 'publisher_name', 'format', 'date', 'deposits_reported', 'spend', 'current_cpa']].copy()
    
    with engine.connect() as conn:
        # Delete existing data for this month
        conn.execute(text(f"DELETE FROM publisher_spend_daily WHERE date >= '{month}-01' AND date < '{month}-01'::date + INTERVAL '1 month'"))
        conn.commit()
        
        # Insert new data
        spend_data_db.to_sql('publisher_spend_daily', engine, if_exists='append', index=False)
        
        # Get count
        result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM publisher_spend_daily WHERE date >= '{month}-01' AND date < '{month}-01'::date + INTERVAL '1 month'"))
        count = result.fetchone()[0]
    
    print(f"   Загружено записей: {count}")
    print()
    print("=" * 80)
    print("ДАННЫЕ О РАСХОДАХ УСПЕШНО ЗАГРУЖЕНЫ В POSTGRESQL!")
    print("=" * 80)
    print()
    print("Таблица: publisher_spend_daily")
    print(f"Месяц: {month}")
    print()
else:
    # Create table for monthly spend data
    print("3. Создание таблицы publisher_spend...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS publisher_spend (
        id SERIAL PRIMARY KEY,
        publisher_id BIGINT NOT NULL,
        publisher_name VARCHAR(255),
        format VARCHAR(50),
        month VARCHAR(7),
        deposits_reported INTEGER,
        spend NUMERIC(15, 2),
        current_cpa NUMERIC(10, 3),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(publisher_id, month)
    );

    CREATE INDEX IF NOT EXISTS idx_publisher_spend_publisher_id ON publisher_spend(publisher_id);
    CREATE INDEX IF NOT EXISTS idx_publisher_spend_format ON publisher_spend(format);
    CREATE INDEX IF NOT EXISTS idx_publisher_spend_month ON publisher_spend(month);
    """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

    print("   Таблица создана/обновлена")
    print()

    # Load data to PostgreSQL
    print("4. Загрузка данных в PostgreSQL...")
    spend_data_db = spend_data[['publisher_id', 'publisher_name', 'format', 'month', 'deposits_reported', 'spend', 'current_cpa']].copy()

    # Replace existing data for the specified month
    with engine.connect() as conn:
        # Delete existing data for this month
        conn.execute(text(f"DELETE FROM publisher_spend WHERE month = '{month}'"))
        conn.commit()
        
        # Insert new data
        spend_data_db.to_sql('publisher_spend', engine, if_exists='append', index=False)
        
        # Get count
        result = conn.execute(text(f"SELECT COUNT(*) as cnt FROM publisher_spend WHERE month = '{month}'"))
        count = result.fetchone()[0]

    print(f"   Загружено записей: {count}")
    print()

    print("=" * 80)
    print("ДАННЫЕ О РАСХОДАХ УСПЕШНО ЗАГРУЖЕНЫ В POSTGRESQL!")
    print("=" * 80)
    print()
    print("Таблица: publisher_spend")
    print(f"Месяц: {month}")
    print()
    print("Теперь можно создавать отчеты в Superset на основе этих данных.")
    print()

