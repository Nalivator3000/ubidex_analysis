-- СТАРАЯ ВЕРСИЯ (медленная) - используйте reactivations_summary_by_period_simple.sql
-- Этот файл сохранен для справки

-- Отчет: Сводка реактиваций по периодам неактивности
-- Обрабатывает ВСЕ данные (максимальный период)
-- Фильтрация по дате выполняется через Dashboard фильтры
-- 
-- ВНИМАНИЕ: Этот запрос очень медленный (~4 дня выполнения для всех данных)
-- Используйте версию с материализованным представлением!

WITH 
-- 1. Получаем ВСЕ депозиты, отсортированные по пользователю и дате
-- Используем оконные функции для оптимизации (намного быстрее, чем JOIN)
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
    r.user_id,
    r.inactivity_period,
    r.first_deposit,
    r.days_inactive
FROM reactivations_with_period r
WHERE r.prev_deposit_date IS NOT NULL
  AND r.days_inactive >= 7
ORDER BY r.first_deposit, r.inactivity_period;

