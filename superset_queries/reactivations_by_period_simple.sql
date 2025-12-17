-- Упрощенный отчет: Реактивации пользователей за период
-- БЕЗ параметров - показывает данные за ноябрь 2025
-- Для изменения периода измените даты в строках 20-21
-- 
-- Для использования:
-- 1. Создайте Chart на основе этого запроса
-- 2. Для изменения периода измените даты '2025-11-01' и '2025-11-30' в запросе
-- 3. Добавьте фильтры на Dashboard (Date Range Filter для first_deposit)
--
-- Визуализации:
-- - Table: для детальной таблицы реактиваций
-- - Bar Chart: для графика по периодам неактивности
-- - Pie Chart: для распределения по периодам

WITH 
-- 1. Получаем первый депозит каждого пользователя в заданном периоде
-- ИЗМЕНИТЕ ДАТЫ ЗДЕСЬ для выбора другого периода:
period_first_deposit AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit
    FROM public.user_events
    WHERE event_type = 'deposit'
      AND event_date >= '2025-11-01'::date
      AND event_date <= '2025-11-30'::date
    GROUP BY external_user_id
),

-- 2. Находим предыдущий депозит для каждого пользователя
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
),

-- 3. Рассчитываем дни неактивности и категоризируем
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
            WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 14 THEN '7-14 days'
            WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 30 THEN '14-30 days'
            WHEN EXTRACT(EPOCH FROM (first_deposit - prev_deposit_date)) / 86400 < 90 THEN '30-90 days'
            ELSE '90+ days'
        END as inactivity_period
    FROM prev_deposits
)

-- 4. Итоговый результат: детальная информация о реактивациях
SELECT
    user_id,
    first_deposit,
    prev_deposit_date,
    days_inactive,
    inactivity_period,
    -- Дополнительная информация для анализа
    DATE_TRUNC('day', first_deposit) as reactivation_date,
    DATE_TRUNC('week', first_deposit) as reactivation_week,
    DATE_TRUNC('month', first_deposit) as reactivation_month
FROM reactivations_with_period
WHERE prev_deposit_date IS NOT NULL  -- Только реактивации (исключаем новых пользователей)
  AND days_inactive >= 7  -- Исключаем реактивации менее 7 дней
ORDER BY first_deposit, days_inactive;

