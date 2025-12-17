#!/usr/bin/env python3
"""
Агрегация дневных данных в месячные для использования в месячных отчетах
"""
import pandas as pd
from sqlalchemy import create_engine, text
from db_utils import get_postgres_connection_string
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("АГРЕГАЦИЯ ДНЕВНЫХ ДАННЫХ В МЕСЯЧНЫЕ")
print("=" * 80)
print()

# Connect to PostgreSQL
pg_uri = get_postgres_connection_string()
engine = create_engine(pg_uri)

# Get monthly aggregated data from daily table
print("1. Агрегирую дневные данные по месяцам...")
print()

query = """
SELECT 
    publisher_id,
    publisher_name,
    format,
    TO_CHAR(date, 'YYYY-MM') as month,
    SUM(deposits_reported) as deposits_reported,
    SUM(spend) as spend,
    CASE 
        WHEN SUM(deposits_reported) > 0 
        THEN SUM(spend) / SUM(deposits_reported)
        ELSE 0
    END as current_cpa
FROM publisher_spend_daily
WHERE publisher_id != 0
GROUP BY publisher_id, publisher_name, format, TO_CHAR(date, 'YYYY-MM')
ORDER BY month, publisher_id;
"""

monthly_data = pd.read_sql(query, engine)

print(f"   Найдено записей: {len(monthly_data)}")
if len(monthly_data) > 0:
    print(f"   Месяцы: {sorted(monthly_data['month'].unique())}")
print()

# Insert/update monthly data
print("2. Загрузка агрегированных данных в publisher_spend...")
print()

with engine.connect() as conn:
    for month in monthly_data['month'].unique():
        month_data = monthly_data[monthly_data['month'] == month]
        
        # Delete existing data for this month
        delete_sql = text("DELETE FROM publisher_spend WHERE month = :month")
        conn.execute(delete_sql, {'month': month})
        conn.commit()
        
        # Insert new aggregated data
        month_data_db = month_data[['publisher_id', 'publisher_name', 'format', 'month', 'deposits_reported', 'spend', 'current_cpa']].copy()
        month_data_db.to_sql('publisher_spend', engine, if_exists='append', index=False)
        
        print(f"   Месяц {month}: {len(month_data)} записей")

print()

# Get statistics
print("3. Статистика по месяцам:")
print()

stats_query = """
SELECT 
    month,
    COUNT(DISTINCT publisher_id) as publishers,
    SUM(spend) as total_spend,
    SUM(deposits_reported) as total_deposits
FROM publisher_spend
GROUP BY month
ORDER BY month;
"""

stats = pd.read_sql(stats_query, engine)
print(stats.to_string(index=False))
print()

print("=" * 80)
print("АГРЕГАЦИЯ ЗАВЕРШЕНА!")
print("=" * 80)
print()
print("Теперь можно использовать месячные отчеты для всех загруженных месяцев.")
print()

