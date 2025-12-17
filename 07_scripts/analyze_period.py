import pandas as pd
import sys
from db_utils import get_db_connection

if len(sys.argv) < 4:
    print("Usage: python analyze_period.py <name> <start_date> <end_date>")
    print("Example: python analyze_period.py August 2025-08-18 2025-08-23")
    sys.exit(1)

period_name = sys.argv[1]
start_date = sys.argv[2]
end_date = sys.argv[3]

print("=" * 80)
print(f"REACTIVATIONS ANALYSIS: {period_name} ({start_date} to {end_date})")
print("=" * 80)
print()

conn = get_db_connection()

# Get all users who deposited in this period
print("1. Getting depositors...")
query = f'''
SELECT DISTINCT external_user_id as user_id
FROM user_events
WHERE event_type = 'deposit'
  AND event_date >= '{start_date} 00:00:00'
  AND event_date <= '{end_date} 23:59:59'
'''
all_users = pd.read_sql(query, conn)
print(f"   Found: {len(all_users):,} users")
print()

# Find reactivations
print("2. Finding reactivations...")
query = f'''
WITH period_first_deposit AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit
    FROM user_events
    WHERE event_type = 'deposit'
      AND event_date >= '{start_date} 00:00:00'
      AND event_date <= '{end_date} 23:59:59'
    GROUP BY external_user_id
),
prev_deposits AS (
    SELECT
        p.external_user_id,
        p.first_deposit,
        MAX(e.event_date) as prev_deposit_date
    FROM period_first_deposit p
    LEFT JOIN user_events e
        ON p.external_user_id = e.external_user_id
        AND e.event_type = 'deposit'
        AND e.event_date < p.first_deposit
    GROUP BY p.external_user_id, p.first_deposit
)
SELECT
    external_user_id as user_id,
    first_deposit,
    prev_deposit_date,
    CAST((julianday(first_deposit) - julianday(prev_deposit_date)) AS INTEGER) as days_inactive
FROM prev_deposits
WHERE prev_deposit_date IS NOT NULL
'''

reactivations = pd.read_sql(query, conn)
conn.close()

print(f"   Found reactivations: {len(reactivations):,}")
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
print("3. Distribution by inactivity period:")
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
print(f"Total reactivations: {len(reactivations):,}")
print(f"New users (no history): {len(all_users) - len(reactivations):,}")
print()

# Save
filename_base = f"all_{period_name.lower().replace(' ', '_')}_reactivations"
reactivations.to_csv(f'{filename_base}_detail.csv', index=False)
summary.to_csv(f'{filename_base}_summary.csv')

print("=" * 80)
print(f"Saved to:")
print(f"  - {filename_base}_detail.csv")
print(f"  - {filename_base}_summary.csv")
print("=" * 80)
