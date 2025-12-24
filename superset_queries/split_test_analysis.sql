-- Анализ сплит-теста: сравнение контрольной и тестовой групп
-- Группы определяются по последнему символу user_id:
-- - Контрольная группа (25%): заканчивается на 0-7
-- - Тестовая группа (75%): заканчивается на 8-9a-z
--
-- Параметры:
-- - exclude_top_percent: исключить N% самых активных игроков (по сумме депозитов)
-- - exclude_bottom_percent: исключить M% самых неактивных игроков (по сумме депозитов)
-- - start_date: начальная дата (фильтр через Dashboard)
-- - end_date: конечная дата (фильтр через Dashboard)
--
-- Для использования:
-- 1. Создайте Dataset на основе этого запроса
-- 2. Добавьте фильтры на Dashboard:
--    - Time Range фильтр для event_date
--    - Numeric фильтр для exclude_top_percent (0-50, по умолчанию 0)
--    - Numeric фильтр для exclude_bottom_percent (0-50, по умолчанию 0)
-- 3. Создайте Chart типа Table для детального сравнения

WITH 
-- 1. Получаем все депозиты с определением группы
deposits_with_groups AS (
    SELECT 
        ue.external_user_id as user_id,
        ue.event_date,
        ue.converted_amount as deposit_amount,
        ue.advertiser,
        -- Определяем группу по последнему символу user_id
        CASE 
            -- Контрольная группа: последний символ 0-7 (25%)
            WHEN RIGHT(LOWER(ue.external_user_id), 1) IN ('0', '1', '2', '3', '4', '5', '6', '7') THEN 'Control'
            -- Тестовая группа: последний символ 8-9a-z (75%)
            WHEN RIGHT(LOWER(ue.external_user_id), 1) IN ('8', '9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z') THEN 'Test'
            ELSE 'Unknown'
        END as test_group
    FROM public.user_events ue
    WHERE ue.event_type = 'deposit'
      AND ue.converted_amount > 0
      AND ue.external_user_id IS NOT NULL
      -- Фильтрация по дате применяется через Dashboard фильтры (Time Range Filter)
),

-- 2. Агрегируем по пользователям для расчета активности
user_totals AS (
    SELECT 
        user_id,
        test_group,
        COUNT(*) as deposit_count,
        SUM(deposit_amount) as total_deposits_usd,
        MIN(event_date) as first_deposit_date,
        MAX(event_date) as last_deposit_date
    FROM deposits_with_groups
    WHERE test_group IN ('Control', 'Test')
    GROUP BY user_id, test_group
),

-- 3. Исключаем выбросы (топ и низ активных игроков)
-- Для этого нужно определить процентили по группам
user_percentiles AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date,
        -- Процентиль активности внутри группы (по сумме депозитов)
        PERCENT_RANK() OVER (PARTITION BY test_group ORDER BY total_deposits_usd) as activity_percentile
    FROM user_totals
),

-- 4. Фильтруем выбросы (если указаны параметры)
-- Параметры exclude_top_percent и exclude_bottom_percent можно добавить через фильтры Dashboard
-- Для начала используем значения по умолчанию (0 = не исключаем)
filtered_users AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date,
        activity_percentile
    FROM user_percentiles
    WHERE 
        -- Исключаем топ N% самых активных (по умолчанию 0 = не исключаем)
        -- Для использования параметра: activity_percentile <= (1.0 - COALESCE({{ exclude_top_percent }}, 0) / 100.0)
        activity_percentile <= 1.0
        -- Исключаем низ M% самых неактивных (по умолчанию 0 = не исключаем)
        -- Для использования параметра: activity_percentile >= COALESCE({{ exclude_bottom_percent }}, 0) / 100.0
        AND activity_percentile >= 0.0
),

-- 5. Возвращаемся к депозитам отфильтрованных пользователей
filtered_deposits AS (
    SELECT 
        d.user_id,
        d.test_group,
        d.event_date,
        d.deposit_amount,
        d.advertiser
    FROM deposits_with_groups d
    INNER JOIN filtered_users fu ON d.user_id = fu.user_id AND d.test_group = fu.test_group
),

-- 6. Финальная агрегация по группам
group_comparison AS (
    SELECT 
        test_group,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_deposits,
        SUM(deposit_amount) as total_deposits_usd,
        AVG(deposit_amount) as avg_deposit_amount,
        -- Среднее количество депозитов на пользователя
        COUNT(*)::NUMERIC / NULLIF(COUNT(DISTINCT user_id), 0) as avg_deposits_per_user,
        -- Средняя сумма депозитов на пользователя
        SUM(deposit_amount)::NUMERIC / NULLIF(COUNT(DISTINCT user_id), 0) as avg_total_per_user,
        MIN(event_date) as min_date,
        MAX(event_date) as max_date
    FROM filtered_deposits
    GROUP BY test_group
)

-- Итоговый результат
SELECT 
    test_group as "Группа",
    unique_users as "Уникальных пользователей",
    total_deposits as "Всего депозитов",
    ROUND(total_deposits_usd::NUMERIC, 2) as "Сумма депозитов (USD)",
    ROUND(avg_deposit_amount::NUMERIC, 2) as "Средний депозит (USD)",
    ROUND(avg_deposits_per_user::NUMERIC, 2) as "Среднее депозитов на пользователя",
    ROUND(avg_total_per_user::NUMERIC, 2) as "Средняя сумма на пользователя (USD)",
    min_date as "Первая дата",
    max_date as "Последняя дата"
FROM group_comparison
ORDER BY test_group;

