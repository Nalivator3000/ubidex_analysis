#!/usr/bin/env python3
"""
Загрузка дневных данных о расходах (spend) из CSV в PostgreSQL для использования в Superset
Поддерживает несколько CSV файлов и автоматическое определение дат
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
print("ЗАГРУЗКА ДНЕВНЫХ ДАННЫХ О РАСХОДАХ В POSTGRESQL")
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

def parse_date_from_filename(filename):
    """Пытается извлечь дату из имени файла"""
    # Паттерны: 2025-11-01, 20251101, 01-11-2025, etc.
    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # 2025-11-01
        r'(\d{4})(\d{2})(\d{2})',     # 20251101
        r'(\d{2})-(\d{2})-(\d{4})',  # 01-11-2025
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups[0]) == 4:  # YYYY-MM-DD или YYYYMMDD
                year, month, day = groups[0], groups[1], groups[2]
            else:  # DD-MM-YYYY
                day, month, year = groups[0], groups[1], groups[2]
            try:
                return datetime(int(year), int(month), int(day)).date()
            except:
                continue
    return None

def load_csv_file(csv_path, date_override=None):
    """Загружает CSV файл и возвращает DataFrame с датами"""
    print(f"   Загружаю файл: {os.path.basename(csv_path)}")
    
    # Пытаемся определить дату из имени файла
    file_date = date_override or parse_date_from_filename(csv_path)
    
    if file_date:
        print(f"   Определена дата из имени файла: {file_date}")
    else:
        print(f"   ВНИМАНИЕ: Не удалось определить дату из имени файла")
        print(f"   Используйте --date для указания даты")
        return None
    
    # Загружаем CSV
    try:
        # Пробуем разные варианты разделителей и заголовков
        df = pd.read_csv(csv_path, skiprows=1, encoding='utf-8')
    except:
        try:
            df = pd.read_csv(csv_path, skiprows=1, encoding='latin-1')
        except:
            df = pd.read_csv(csv_path, encoding='utf-8')
    
    # Проверяем наличие необходимых колонок
    required_cols = ['Publisher', 'Deposit', 'Spend']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"   ОШИБКА: Отсутствуют колонки: {missing_cols}")
        print(f"   Найденные колонки: {list(df.columns)}")
        return None
    
    # Извлекаем publisher_id и format
    df['publisher_id'] = df['Publisher'].apply(extract_publisher_id)
    df['format'] = df['Publisher'].apply(extract_format)
    
    # Оставляем только нужные колонки
    df = df[['publisher_id', 'Publisher', 'format', 'Deposit', 'Spend']].copy()
    df.columns = ['publisher_id', 'publisher_name', 'format', 'deposits_reported', 'spend']
    
    # Удаляем строки без publisher_id
    df = df.dropna(subset=['publisher_id'])
    
    # Конвертируем в числовые типы
    for col in ['deposits_reported', 'spend']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Рассчитываем CPA
    df['current_cpa'] = (df['spend'] / df['deposits_reported'].replace(0, 1)).round(3)
    
    # Добавляем дату
    df['date'] = file_date
    
    print(f"   Обработано записей: {len(df)}")
    
    return df

# Парсинг аргументов
parser = argparse.ArgumentParser(
    description='Load daily spend data from CSV to PostgreSQL',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Примеры использования:
  # Загрузить один файл с автоматическим определением даты
  python load_daily_spend_to_postgresql.py --csv data/spend_2025-11-01.csv
  
  # Загрузить несколько файлов
  python load_daily_spend_to_postgresql.py --csv data/spend_2025-11-01.csv data/spend_2025-11-02.csv
  
  # Указать дату вручную
  python load_daily_spend_to_postgresql.py --csv data/spend.csv --date 2025-11-01
  
  # Загрузить все CSV из директории
  python load_daily_spend_to_postgresql.py --dir data/spend_daily/
    """
)
parser.add_argument('--csv', type=str, nargs='+', help='Path(s) to CSV file(s)', default=None)
parser.add_argument('--dir', type=str, help='Directory with CSV files', default=None)
parser.add_argument('--date', type=str, help='Date in format YYYY-MM-DD (if not in filename)', default=None)
parser.add_argument('--pattern', type=str, help='File pattern for directory scan (e.g., "spend_*.csv")', default='*.csv')
args = parser.parse_args()

# Определяем список файлов для обработки
csv_files = []

if args.csv:
    csv_files = args.csv
elif args.dir:
    import glob
    pattern = os.path.join(args.dir, args.pattern)
    csv_files = glob.glob(pattern)
    if not csv_files:
        print(f"ERROR: Не найдено файлов по паттерну: {pattern}")
        sys.exit(1)
else:
    print("ERROR: Укажите --csv или --dir")
    parser.print_help()
    sys.exit(1)

if not csv_files:
    print("ERROR: Не найдено файлов для обработки")
    sys.exit(1)

print(f"Найдено файлов для обработки: {len(csv_files)}")
print()

# Парсим дату, если указана вручную
date_override = None
if args.date:
    try:
        date_override = datetime.strptime(args.date, '%Y-%m-%d').date()
        print(f"Используется дата из параметра: {date_override}")
    except:
        print(f"ERROR: Неверный формат даты: {args.date}. Используйте YYYY-MM-DD")
        sys.exit(1)

# Загружаем все CSV файлы
all_data = []
for csv_path in csv_files:
    if not os.path.exists(csv_path):
        print(f"WARNING: Файл не найден: {csv_path}")
        continue
    
    df = load_csv_file(csv_path, date_override)
    if df is not None:
        all_data.append(df)
    print()

if not all_data:
    print("ERROR: Не удалось загрузить данные из файлов")
    sys.exit(1)

# Объединяем все данные
combined_data = pd.concat(all_data, ignore_index=True)
print(f"Всего загружено записей: {len(combined_data)}")
print(f"Период: {combined_data['date'].min()} - {combined_data['date'].max()}")
print()

# Подключение к PostgreSQL
print("2. Подключение к PostgreSQL...")
pg_uri = get_postgres_connection_string()
engine = create_engine(pg_uri)

# Создание таблицы для дневных данных
print("3. Создание/проверка таблицы publisher_spend_daily...")
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

# Загрузка данных в PostgreSQL
print("4. Загрузка данных в PostgreSQL...")

# Подготавливаем данные для загрузки
data_to_load = combined_data[['publisher_id', 'publisher_name', 'format', 'date', 'deposits_reported', 'spend', 'current_cpa']].copy()

# Удаляем дубликаты (если файлы загружались несколько раз)
date_range = (data_to_load['date'].min(), data_to_load['date'].max())
print(f"   Удаление существующих данных за период: {date_range[0]} - {date_range[1]}")

with engine.connect() as conn:
    # Удаляем существующие данные за этот период
    delete_sql = text("""
        DELETE FROM publisher_spend_daily 
        WHERE date >= :start_date AND date <= :end_date
    """)
    conn.execute(delete_sql, {'start_date': date_range[0], 'end_date': date_range[1]})
    conn.commit()
    
    # Вставляем новые данные
    print(f"   Загрузка {len(data_to_load)} записей...")
    data_to_load.to_sql('publisher_spend_daily', engine, if_exists='append', index=False)
    
    # Получаем статистику
    stats_sql = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT date) as days,
            COUNT(DISTINCT publisher_id) as publishers,
            MIN(date) as min_date,
            MAX(date) as max_date,
            SUM(spend) as total_spend
        FROM publisher_spend_daily
        WHERE date >= :start_date AND date <= :end_date
    """)
    result = conn.execute(stats_sql, {'start_date': date_range[0], 'end_date': date_range[1]})
    stats = result.fetchone()
    
    print(f"   Загружено записей: {stats[0]}")
    print(f"   Дней: {stats[1]}")
    print(f"   Паблишеров: {stats[2]}")
    print(f"   Период: {stats[3]} - {stats[4]}")
    print(f"   Общие расходы: ${stats[5]:,.2f}")
    print()

print("=" * 80)
print("ДНЕВНЫЕ ДАННЫЕ О РАСХОДАХ УСПЕШНО ЗАГРУЖЕНЫ В POSTGRESQL!")
print("=" * 80)
print()
print("Таблица: publisher_spend_daily")
print(f"Период: {date_range[0]} - {date_range[1]}")
print()
print("Теперь можно использовать SQL-запрос publisher_coefficients_by_day.sql в Superset")
print()

