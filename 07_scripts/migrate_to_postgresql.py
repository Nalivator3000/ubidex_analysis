"""
Миграция данных из SQLite в PostgreSQL
"""
import os
import sys
import sqlite3
import argparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
import pandas as pd
from tqdm import tqdm
from db_utils import get_sqlite_path, get_postgres_connection_string

# Parse arguments
parser = argparse.ArgumentParser(description='Migrate data from SQLite to PostgreSQL')
parser.add_argument('--yes', '-y', action='store_true', help='Automatically answer yes to all prompts')
args = parser.parse_args()

print("=" * 80)
print("МИГРАЦИЯ ДАННЫХ ИЗ SQLITE В POSTGRESQL")
print("=" * 80)
print()

# Get SQLite database path
sqlite_path = get_sqlite_path()
if not os.path.exists(sqlite_path):
    print(f"ОШИБКА: SQLite база данных не найдена: {sqlite_path}")
    sys.exit(1)

print(f"SQLite база: {sqlite_path}")
print(f"Размер файла: {os.path.getsize(sqlite_path) / (1024**3):.2f} GB")
print()

# Connect to SQLite
print("Подключение к SQLite...")
sqlite_conn = sqlite3.connect(sqlite_path)
print("✓ Подключено")
print()

# Get PostgreSQL connection
print("Подключение к PostgreSQL...")
postgres_uri = get_postgres_connection_string()
postgres_engine = create_engine(postgres_uri, pool_pre_ping=True)

try:
    with postgres_engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✓ Подключено к PostgreSQL: {version}")
except Exception as e:
    print(f"✗ Ошибка подключения к PostgreSQL: {e}")
    print(f"  URI: {postgres_uri.replace(postgres_uri.split('@')[0].split('://')[1], '***')}")
    sys.exit(1)

print()

# Get table schema from SQLite
print("Анализ структуры таблиц...")
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in sqlite_cursor.fetchall()]

if 'user_events' not in tables:
    print("ОШИБКА: Таблица 'user_events' не найдена в SQLite")
    sys.exit(1)

print(f"Найдено таблиц: {len(tables)}")
print(f"Основная таблица: user_events")
print()

# Get table info
sqlite_cursor.execute("PRAGMA table_info(user_events)")
columns_info = sqlite_cursor.fetchall()

print("Структура таблицы user_events:")
for col in columns_info:
    print(f"  - {col[1]} ({col[2]})")
print()

# Count rows
print("Подсчет записей...")
sqlite_cursor.execute("SELECT COUNT(*) FROM user_events")
total_rows = sqlite_cursor.fetchone()[0]
print(f"Всего записей: {total_rows:,}")
print()

# Create table in PostgreSQL
print("Создание таблицы в PostgreSQL...")
# В PostgreSQL не будем задавать PRIMARY KEY по event_id, чтобы избежать
# ошибок при возможных дубликатах идентификаторов событий. Для аналитики
# нам важнее полнота данных и корректная агрегация по пользователям/датам.
create_table_sql = """
CREATE TABLE IF NOT EXISTS user_events (
    event_id TEXT,
    external_user_id TEXT,
    ubidex_id TEXT,
    event_type TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL,
    publisher_id INTEGER,
    campaign_id INTEGER,
    sub_id TEXT,
    affiliate_id TEXT,
    deposit_amount REAL,
    currency TEXT,
    converted_amount REAL,
    converted_currency TEXT,
    website TEXT,
    country TEXT,
    transaction_id TEXT
);
"""

# Индексы для ускорения аналитических запросов
create_indexes_sql = [
    "CREATE INDEX IF NOT EXISTS idx_event_id ON user_events(event_id);",
    "CREATE INDEX IF NOT EXISTS idx_external_user_id ON user_events(external_user_id);",
    "CREATE INDEX IF NOT EXISTS idx_event_type ON user_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_event_date ON user_events(event_date);",
    "CREATE INDEX IF NOT EXISTS idx_publisher_id ON user_events(publisher_id);",
    "CREATE INDEX IF NOT EXISTS idx_event_type_date ON user_events(event_type, event_date);",
]

with postgres_engine.connect() as conn:
    # Drop table if exists (optional, for clean migration)
    if args.yes:
        # Check if table exists
        inspector = inspect(postgres_engine)
        if 'user_events' in inspector.get_table_names():
            conn.execute(text("DROP TABLE IF EXISTS user_events CASCADE;"))
            conn.commit()
            print("✓ Старая таблица удалена")
    else:
        drop_existing = input("Удалить существующую таблицу user_events в PostgreSQL? (y/N): ")
        if drop_existing.lower() == 'y':
            conn.execute(text("DROP TABLE IF EXISTS user_events CASCADE;"))
            conn.commit()
            print("✓ Старая таблица удалена")
    
    # Create table
    conn.execute(text(create_table_sql))
    conn.commit()
    print("✓ Таблица создана")
    
    # Create indexes (will be created after data import for better performance)
    print("  (Индексы будут созданы после импорта данных)")

print()

# Migrate data in chunks
CHUNK_SIZE = 100000
print(f"Начало миграции данных (чанки по {CHUNK_SIZE:,} записей)...")
print()

total_migrated = 0
offset = 0

# Check if table already has data
with postgres_engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM user_events"))
    existing_count = result.fetchone()[0]
    if existing_count > 0:
        print(f"В PostgreSQL уже есть {existing_count:,} записей")
        resume = input("Продолжить миграцию? (y/N): ")
        if resume.lower() != 'y':
            print("Миграция отменена")
            sys.exit(0)
        offset = existing_count

# Use pandas for efficient chunking
query = "SELECT * FROM user_events ORDER BY event_date LIMIT ? OFFSET ?"

print("Импорт данных...")
with tqdm(total=total_rows, initial=offset, unit="rows", unit_scale=True) as pbar:
    while offset < total_rows:
        # Read chunk from SQLite
        chunk_query = f"SELECT * FROM user_events ORDER BY event_date LIMIT {CHUNK_SIZE} OFFSET {offset}"
        chunk_df = pd.read_sql_query(chunk_query, sqlite_conn)
        
        if len(chunk_df) == 0:
            break
        
        # Write to PostgreSQL
        chunk_df.to_sql(
            'user_events',
            postgres_engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=10000
        )
        
        total_migrated += len(chunk_df)
        offset += CHUNK_SIZE
        pbar.update(len(chunk_df))

print()
print("✓ Импорт данных завершен")
print()

# Create indexes
print("Создание индексов...")
with postgres_engine.connect() as conn:
    for index_sql in create_indexes_sql:
        try:
            conn.execute(text(index_sql))
            conn.commit()
            print(f"✓ {index_sql.split('ON')[0].strip()}")
        except Exception as e:
            print(f"  (Индекс уже существует или ошибка: {e})")

print()

# Verify migration
print("Проверка миграции...")
with postgres_engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM user_events"))
    postgres_count = result.fetchone()[0]
    
    result = conn.execute(text("SELECT MIN(event_date), MAX(event_date) FROM user_events"))
    date_range = result.fetchone()
    
    print(f"SQLite записей:   {total_rows:,}")
    print(f"PostgreSQL записей: {postgres_count:,}")
    print(f"Диапазон дат:     {date_range[0]} - {date_range[1]}")

if postgres_count == total_rows:
    print()
    print("=" * 80)
    print("✓ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("=" * 80)
else:
    print()
    print("⚠ ВНИМАНИЕ: Количество записей не совпадает!")
    print(f"  Разница: {abs(total_rows - postgres_count):,} записей")

# Close connections
sqlite_conn.close()
postgres_engine.dispose()

print()
print("Следующие шаги:")
print("1. Установите переменную окружения DB_TYPE=postgresql")
print("2. Перезапустите контейнеры: docker-compose restart")
print("3. Обновите подключение в Superset")

