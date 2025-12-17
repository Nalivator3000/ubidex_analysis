import pandas as pd
import sqlite3

print("=" * 80)
print("ВСЕ РЕАКТИВАЦИИ: Октябрь 18-23, 2025 (КОНТРОЛЬНЫЙ ПЕРИОД)")
print("=" * 80)
print()

from db_utils import get_db_connection
conn = get_db_connection()

# Step 1: Get all users who deposited in Oct 18-23
print("1. Получаем всех депозитных юзеров октября 18-23...")
query = '''
SELECT DISTINCT external_user_id as user_id
FROM user_events
WHERE event_type = 'deposit'
  AND event_date >= '2025-10-18 00:00:00'
  AND event_date <= '2025-10-23 23:59:59'
'''
all_oct_users = pd.read_sql(query, conn)
print(f"   Найдено: {len(all_oct_users):,} пользователей")
print()

# Step 2: Find reactivations using optimized SQL
print("2. Ищем реактивации (юзеры с предыдущими депозитами)...")
print("   Используем оптимизированный SQL запрос...")

query = '''
WITH oct_first_deposit AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_oct_deposit
    FROM user_events
    WHERE event_type = 'deposit'
      AND event_date >= '2025-10-18 00:00:00'
      AND event_date <= '2025-10-23 23:59:59'
    GROUP BY external_user_id
),
prev_deposits AS (
    SELECT
        o.external_user_id,
        o.first_oct_deposit,
        MAX(e.event_date) as prev_deposit_date
    FROM oct_first_deposit o
    LEFT JOIN user_events e
        ON o.external_user_id = e.external_user_id
        AND e.event_type = 'deposit'
        AND e.event_date < o.first_oct_deposit
    GROUP BY o.external_user_id, o.first_oct_deposit
)
SELECT
    external_user_id as user_id,
    first_oct_deposit,
    prev_deposit_date,
    CAST((julianday(first_oct_deposit) - julianday(prev_deposit_date)) AS INTEGER) as days_inactive
FROM prev_deposits
WHERE prev_deposit_date IS NOT NULL
'''

reactivations = pd.read_sql(query, conn)
conn.close()

print(f"   Найдено реактиваций: {len(reactivations):,}")
print()

# Categorize
def categorize(days):
    if days < 7:
        return '0-7 days'
    elif days < 14:
        return '7-14 days'
    elif days < 30:
        return '14-30 days'
    elif days < 90:
        return '30-90 days'
    else:
        return '90+ days'

reactivations['period'] = reactivations['days_inactive'].apply(categorize)

# Summary
print("3. Распределение по периодам неактивности:")
print()
summary = reactivations.groupby('period').agg({
    'user_id': 'count',
    'days_inactive': 'mean'
}).round(1)
summary.columns = ['count', 'avg_days']
summary['percentage'] = (summary['count'] / summary['count'].sum() * 100).round(1)

# Reorder
desired_order = ['0-7 days', '7-14 days', '14-30 days', '30-90 days', '90+ days']
summary = summary.reindex([p for p in desired_order if p in summary.index])

print(summary)
print()
print(f"ИТОГО реактиваций: {len(reactivations):,}")
print(f"Новых пользователей (без истории): {len(all_oct_users) - len(reactivations):,}")
print()

# Save
reactivations.to_csv('all_oct18-23_reactivations_detail.csv', index=False)
summary.to_csv('all_oct18-23_reactivations_summary.csv')

print("=" * 80)
print("Сохранено:")
print("  - all_oct18-23_reactivations_detail.csv")
print("  - all_oct18-23_reactivations_summary.csv")
print("=" * 80)
