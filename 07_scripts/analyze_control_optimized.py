import pandas as pd
import sqlite3
from datetime import datetime

print("=" * 80)
print("Control Period Analysis: October 18-23, 2025 (NO ADS)")
print("=" * 80)
print()

from db_utils import get_db_connection
conn = get_db_connection()

# Optimized: Get all data in one query using window functions
print("1. Analyzing October depositors with SQL...")
query = '''
WITH oct_deposits AS (
    SELECT
        external_user_id,
        event_date,
        ROW_NUMBER() OVER (PARTITION BY external_user_id ORDER BY event_date) as deposit_num
    FROM user_events
    WHERE event_type = 'deposit'
      AND external_user_id IN (
          SELECT DISTINCT external_user_id
          FROM user_events
          WHERE event_type = 'deposit'
            AND event_date >= '2025-10-18 00:00:00'
            AND event_date <= '2025-10-23 23:59:59'
      )
),
first_oct AS (
    SELECT external_user_id, MIN(event_date) as first_oct_deposit
    FROM user_events
    WHERE event_type = 'deposit'
      AND event_date >= '2025-10-18 00:00:00'
      AND event_date <= '2025-10-23 23:59:59'
    GROUP BY external_user_id
),
prev_deposit AS (
    SELECT
        o.external_user_id,
        o.first_oct_deposit,
        MAX(d.event_date) as prev_deposit_date
    FROM first_oct o
    LEFT JOIN oct_deposits d
        ON o.external_user_id = d.external_user_id
        AND d.event_date < o.first_oct_deposit
    GROUP BY o.external_user_id, o.first_oct_deposit
)
SELECT
    external_user_id as user_id,
    first_oct_deposit as reactivation_date,
    prev_deposit_date,
    CAST((julianday(first_oct_deposit) - julianday(prev_deposit_date)) AS INTEGER) as days_inactive
FROM prev_deposit
WHERE prev_deposit_date IS NOT NULL
'''

print("   Running query...")
results_df = pd.read_sql(query, conn)
conn.close()

print(f"   Found {len(results_df):,} reactivations")
print()

# Categorize
def categorize_period(days):
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

results_df['period'] = results_df['days_inactive'].apply(categorize_period)

print("2. Distribution by inactivity period:")
print()

summary = results_df.groupby('period').agg({
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
print(f"Total reactivations: {summary['count'].sum():,.0f}")
print()

# Save
results_df.to_csv('control_period_oct18-23_detail.csv', index=False)
summary.to_csv('control_period_oct18-23_summary.csv')

print("=" * 80)
print("Saved to:")
print("  - control_period_oct18-23_detail.csv")
print("  - control_period_oct18-23_summary.csv")
print("=" * 80)
