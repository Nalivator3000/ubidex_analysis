#!/usr/bin/env python3
"""
Создание материализованного представления для реактиваций
Это позволит быстро фильтровать по дате в Dashboard без пересчета всех данных
"""
import sys
import io
from sqlalchemy import create_engine, text
from db_utils import get_postgres_connection_string

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("СОЗДАНИЕ МАТЕРИАЛИЗОВАННОГО ПРЕДСТАВЛЕНИЯ ДЛЯ РЕАКТИВАЦИЙ")
print("=" * 80)
print()

engine = create_engine(get_postgres_connection_string())

print("1. Создание материализованного представления...")
print("   Это может занять несколько минут (обработка ~8 млн депозитов)...")
print()

# SQL для создания материализованного представления
create_view_sql = """
-- Удаляем существующее представление, если есть
DROP MATERIALIZED VIEW IF EXISTS reactivations_materialized CASCADE;

-- Создаем материализованное представление
CREATE MATERIALIZED VIEW reactivations_materialized AS
WITH 
-- 1. Получаем все депозиты, отсортированные по пользователю и дате
all_deposits_ordered AS (
    SELECT
        external_user_id,
        event_date as deposit_date,
        LAG(event_date) OVER (PARTITION BY external_user_id ORDER BY event_date) as prev_deposit_date
    FROM public.user_events
    WHERE event_type = 'deposit'
),
-- 2. Рассчитываем дни неактивности и категоризируем
reactivations_with_period AS (
    SELECT
        external_user_id as user_id,
        deposit_date as first_deposit,
        prev_deposit_date,
        CASE 
            WHEN prev_deposit_date IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (deposit_date - prev_deposit_date)) / 86400
            ELSE NULL
        END as days_inactive,
        CASE 
            WHEN prev_deposit_date IS NULL THEN 'Новый пользователь'
            WHEN EXTRACT(EPOCH FROM (deposit_date - prev_deposit_date)) / 86400 < 14 THEN '7-14 days'
            WHEN EXTRACT(EPOCH FROM (deposit_date - prev_deposit_date)) / 86400 < 30 THEN '14-30 days'
            WHEN EXTRACT(EPOCH FROM (deposit_date - prev_deposit_date)) / 86400 < 90 THEN '30-90 days'
            ELSE '90+ days'
        END as inactivity_period
    FROM all_deposits_ordered
)
SELECT
    user_id,
    inactivity_period,
    first_deposit,  -- Дата реактивации для фильтрации
    days_inactive
FROM reactivations_with_period
WHERE prev_deposit_date IS NOT NULL  -- Только реактивации
  AND days_inactive >= 7;  -- Исключаем реактивации менее 7 дней

-- Создаем индексы для быстрой фильтрации
CREATE INDEX idx_reactivations_first_deposit ON reactivations_materialized(first_deposit);
CREATE INDEX idx_reactivations_period ON reactivations_materialized(inactivity_period);
CREATE INDEX idx_reactivations_user ON reactivations_materialized(user_id);
"""

try:
    with engine.connect() as conn:
        print("   Выполняю запрос...")
        conn.execute(text(create_view_sql))
        conn.commit()
        print("   ✓ Материализованное представление создано")
        print()
        
        # Проверяем количество записей
        count_query = "SELECT COUNT(*) as total FROM reactivations_materialized;"
        result = conn.execute(text(count_query))
        total = result.fetchone()[0]
        print(f"2. Проверка данных:")
        print(f"   Всего реактиваций в представлении: {total:,}")
        print()
        
        # Проверяем индексы
        indexes_query = """
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'reactivations_materialized' 
        AND schemaname = 'public';
        """
        indexes_result = conn.execute(text(indexes_query))
        indexes = [row[0] for row in indexes_result]
        print(f"3. Созданные индексы:")
        for idx in indexes:
            print(f"   - {idx}")
        print()
        
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("МАТЕРИАЛИЗОВАННОЕ ПРЕДСТАВЛЕНИЕ УСПЕШНО СОЗДАНО!")
print("=" * 80)
print()
print("Теперь можно использовать быстрый запрос:")
print("  SELECT * FROM reactivations_materialized WHERE first_deposit >= '2025-08-23' AND first_deposit <= '2025-08-25';")
print()
print("Для обновления данных (если добавились новые депозиты):")
print("  REFRESH MATERIALIZED VIEW reactivations_materialized;")
print()

