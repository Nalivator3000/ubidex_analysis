#!/usr/bin/env python3
"""
Тестовый скрипт для проверки запроса реактиваций
"""
import pandas as pd
from db_utils import get_db_engine
from sqlalchemy import text

print("=" * 80)
print("ТЕСТИРОВАНИЕ ЗАПРОСА РЕАКТИВАЦИЙ")
print("=" * 80)
print()

engine = get_db_engine()

# Проверка 1: Общая статистика по депозитам
print("1. Общая статистика по депозитам:")
print()
with engine.connect() as conn:
    query = """
    SELECT 
        COUNT(DISTINCT external_user_id) as total_users,
        COUNT(*) as total_deposits,
        MIN(event_date) as first_deposit,
        MAX(event_date) as last_deposit
    FROM public.user_events
    WHERE event_type = 'deposit';
    """
    result = pd.read_sql(text(query), conn)
    print(result)
    print()

# Проверка 2: Проверка наличия реактиваций (упрощенный запрос)
print("2. Проверка наличия реактиваций (первые 10):")
print()
with engine.connect() as conn:
    query = """
    WITH period_first_deposit AS (
        SELECT
            external_user_id,
            MIN(event_date) as first_deposit
        FROM public.user_events
        WHERE event_type = 'deposit'
          AND event_date >= '2025-11-01'
          AND event_date <= '2025-11-30'
        GROUP BY external_user_id
        LIMIT 100
    ),
    prev_deposits AS (
        SELECT
            p.external_user_id,
            p.first_deposit,
            MAX(e.event_date) as prev_deposit_date
        FROM period_first_deposit p
        LEFT JOIN public.user_events e
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
    LIMIT 10;
    """
    result = pd.read_sql(text(query), conn)
    print(f"Найдено реактиваций: {len(result)}")
    if len(result) > 0:
        print(result)
    else:
        print("Реактиваций не найдено!")
    print()

# Проверка 3: Статистика по периодам
print("3. Статистика по периодам неактивности (ноябрь 2025):")
print()
with engine.connect() as conn:
    query = """
    WITH period_first_deposit AS (
        SELECT
            external_user_id,
            MIN(event_date) as first_deposit
        FROM public.user_events
        WHERE event_type = 'deposit'
          AND event_date >= '2025-11-01'
          AND event_date <= '2025-11-30'
        GROUP BY external_user_id
    ),
    prev_deposits AS (
        SELECT
            p.external_user_id,
            p.first_deposit,
            MAX(e.event_date) as prev_deposit_date
        FROM period_first_deposit p
        LEFT JOIN public.user_events e
            ON p.external_user_id = e.external_user_id
            AND e.event_type = 'deposit'
            AND e.event_date < p.first_deposit
        GROUP BY p.external_user_id, p.first_deposit
    ),
    reactivations_with_period AS (
        SELECT
            external_user_id as user_id,
            first_deposit,
            prev_deposit_date,
            CASE 
                WHEN prev_deposit_date IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400
                ELSE NULL
            END as days_inactive,
            CASE 
                WHEN prev_deposit_date IS NULL THEN 'Новый пользователь'
                WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 7 THEN '0-7 days'
                WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 14 THEN '7-14 days'
                WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 30 THEN '14-30 days'
                WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 90 THEN '30-90 days'
                ELSE '90+ days'
            END as inactivity_period
        FROM prev_deposits
    )
    SELECT
        inactivity_period,
        COUNT(DISTINCT user_id) as reactivations_count
    FROM reactivations_with_period
    WHERE prev_deposit_date IS NOT NULL
    GROUP BY inactivity_period
    ORDER BY 
        CASE inactivity_period
            WHEN '0-7 days' THEN 1
            WHEN '7-14 days' THEN 2
            WHEN '14-30 days' THEN 3
            WHEN '30-90 days' THEN 4
            WHEN '90+ days' THEN 5
            ELSE 6
        END;
    """
    result = pd.read_sql(text(query), conn)
    print(f"Найдено периодов: {len(result)}")
    if len(result) > 0:
        print(result)
    else:
        print("Данных нет!")
    print()

print("=" * 80)
print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 80)

