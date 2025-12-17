-- Отчет: Сводка реактиваций по периодам неактивности
-- БЕЗ параметров - показывает данные за последний месяц (ноябрь 2025)
-- Для изменения периода измените даты в WHERE clause
-- 
-- Визуализации:
-- - Bar Chart: для графика количества реактиваций по периодам
-- - Pie Chart: для распределения по периодам
-- - Table: для табличного представления

WITH 
-- 1. Получаем первый депозит каждого пользователя в заданном периоде
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
    LEFT JOIN public.user_events e
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
),

-- 4. Подсчитываем общее количество пользователей
total_users AS (
    SELECT COUNT(DISTINCT user_id) as total
    FROM reactivations_with_period
)

-- 5. Итоговая сводка по периодам неактивности
SELECT
    r.inactivity_period,
    COUNT(DISTINCT r.user_id) as reactivations_count,
    ROUND(AVG(r.days_inactive), 1) as avg_days_inactive,
    ROUND(MIN(r.days_inactive), 1) as min_days_inactive,
    ROUND(MAX(r.days_inactive), 1) as max_days_inactive,
    -- Процент от всех реактиваций
    ROUND(
        COUNT(DISTINCT r.user_id) * 100.0 / 
        NULLIF((SELECT COUNT(DISTINCT user_id) FROM reactivations_with_period WHERE prev_deposit_date IS NOT NULL), 0),
        1
    ) as percentage_of_reactivations,
    -- Процент от всех пользователей (включая новых)
    ROUND(
        COUNT(DISTINCT r.user_id) * 100.0 / 
        NULLIF((SELECT total FROM total_users), 0),
        1
    ) as percentage_of_all_users
FROM reactivations_with_period r
WHERE r.prev_deposit_date IS NOT NULL  -- Только реактивации (исключаем новых пользователей)
  AND r.days_inactive >= 7  -- Исключаем реактивации менее 7 дней
GROUP BY r.inactivity_period
ORDER BY 
    CASE r.inactivity_period
        WHEN '7-14 days' THEN 1
        WHEN '14-30 days' THEN 2
        WHEN '30-90 days' THEN 3
        WHEN '90+ days' THEN 4
        ELSE 5
    END;

