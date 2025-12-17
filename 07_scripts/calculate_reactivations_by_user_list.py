#!/usr/bin/env python3
"""
Скрипт для расчета реактиваций по списку пользователей
Принимает список ID пользователей и период реактивации,
рассчитывает количество реактиваций в разрезе периода неактивности
"""
import pandas as pd
import sys
import io
import argparse
from datetime import datetime
from db_utils import get_db_engine, get_db_type

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("РАСЧЕТ РЕАКТИВАЦИЙ ПО СПИСКУ ПОЛЬЗОВАТЕЛЕЙ")
print("=" * 80)
print()

# Parse arguments
parser = argparse.ArgumentParser(description='Calculate reactivations for a list of users')
parser.add_argument('--users', type=str, help='Comma-separated list of user IDs or path to CSV file with user_id column')
parser.add_argument('--start-date', type=str, required=True, help='Start date of reactivation period (YYYY-MM-DD)')
parser.add_argument('--end-date', type=str, required=True, help='End date of reactivation period (YYYY-MM-DD)')
parser.add_argument('--output', type=str, default='reactivations_by_user_list', help='Output file prefix (default: reactivations_by_user_list)')
args = parser.parse_args()

# Validate dates
try:
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    if start_date > end_date:
        print("ERROR: start_date must be before end_date")
        sys.exit(1)
except ValueError as e:
    print(f"ERROR: Invalid date format. Use YYYY-MM-DD. Error: {e}")
    sys.exit(1)

# Load user list
print("1. Загрузка списка пользователей...")
print()

user_ids = []
if args.users:
    # Check if it's a file path
    import os
    if os.path.exists(args.users):
        # Load from CSV file
        try:
            users_df = pd.read_csv(args.users)
            if 'user_id' in users_df.columns:
                user_ids = users_df['user_id'].tolist()
            elif 'external_user_id' in users_df.columns:
                user_ids = users_df['external_user_id'].tolist()
            else:
                print(f"ERROR: CSV file must contain 'user_id' or 'external_user_id' column")
                print(f"Available columns: {', '.join(users_df.columns)}")
                sys.exit(1)
            print(f"   Загружено {len(user_ids)} пользователей из файла: {args.users}")
        except Exception as e:
            print(f"ERROR: Failed to read CSV file: {e}")
            sys.exit(1)
    else:
        # Comma-separated list
        user_ids = [uid.strip() for uid in args.users.split(',')]
        print(f"   Загружено {len(user_ids)} пользователей из аргумента")
else:
    print("ERROR: --users is required")
    sys.exit(1)

if not user_ids:
    print("ERROR: No users found")
    sys.exit(1)

print(f"   Всего пользователей для анализа: {len(user_ids):,}")
print()

# Connect to database
print("2. Подключение к базе данных...")
db_type = get_db_type()
engine = get_db_engine()
print(f"   Тип БД: {db_type}")
print()

# Build SQL query based on database type
print("3. Расчет реактиваций...")
print()

if db_type == 'postgresql':
    # PostgreSQL query
    # Convert user_ids list to SQL IN clause
    user_ids_str = "', '".join(str(uid) for uid in user_ids)
    
    query = f'''
    WITH period_first_deposit AS (
        SELECT
            external_user_id,
            MIN(event_date) as first_deposit
        FROM user_events
        WHERE event_type = 'deposit'
          AND external_user_id IN ('{user_ids_str}')
          AND event_date >= '{args.start_date} 00:00:00'
          AND event_date <= '{args.end_date} 23:59:59'
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
        CASE 
            WHEN prev_deposit_date IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400
            ELSE NULL
        END as days_inactive
    FROM prev_deposits
    WHERE prev_deposit_date IS NOT NULL
    ORDER BY days_inactive
    '''
else:
    # SQLite query
    user_ids_str = "', '".join(str(uid) for uid in user_ids)
    
    query = f'''
    WITH period_first_deposit AS (
        SELECT
            external_user_id,
            MIN(event_date) as first_deposit
        FROM user_events
        WHERE event_type = 'deposit'
          AND external_user_id IN ('{user_ids_str}')
          AND event_date >= '{args.start_date} 00:00:00'
          AND event_date <= '{args.end_date} 23:59:59'
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
    ORDER BY days_inactive
    '''

# Execute query
with engine.connect() as conn:
    reactivations = pd.read_sql(query, conn)

print(f"   Найдено реактиваций: {len(reactivations):,}")
print()

# Categorize by inactivity period
def categorize(days):
    if pd.isna(days):
        return 'Нет данных'
    days = int(days)
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

if len(reactivations) > 0:
    reactivations['days_inactive'] = reactivations['days_inactive'].astype(float)
    reactivations['period'] = reactivations['days_inactive'].apply(categorize)
    
    # Summary by period
    print("4. Распределение по периодам неактивности:")
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
    
    # Total statistics
    total_users_analyzed = len(user_ids)
    total_reactivations = len(reactivations)
    new_users = total_users_analyzed - total_reactivations
    
    print(f"ИТОГО:")
    print(f"  Пользователей в списке: {total_users_analyzed:,}")
    print(f"  Реактиваций найдено: {total_reactivations:,}")
    print(f"  Новых пользователей (без истории): {new_users:,}")
    print(f"  Процент реактиваций: {(total_reactivations / total_users_analyzed * 100):.1f}%")
    print()
    
    # Save results
    print("5. Сохранение результатов...")
    print()
    
    detail_filename = f'{args.output}_detail.csv'
    summary_filename = f'{args.output}_summary.csv'
    
    reactivations.to_csv(detail_filename, index=False, encoding='utf-8-sig')
    summary.to_csv(summary_filename, encoding='utf-8-sig')
    
    print(f"   Сохранено:")
    print(f"     - {detail_filename}")
    print(f"     - {summary_filename}")
    print()
else:
    print("   Реактиваций не найдено")
    print()

print("=" * 80)
print("РАСЧЕТ ЗАВЕРШЕН!")
print("=" * 80)

