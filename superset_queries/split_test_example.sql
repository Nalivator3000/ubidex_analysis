-- Анализ сплит-теста: сравнение контрольной и тестовой групп
-- Настройки:
-- - Позиция символа с конца: 1
-- - Контрольная группа: 0-7 (8 символов)
-- - Тестовая группа: 8-9a-z (28 символов)
-- - Исключить топ 0% самых активных
-- - Исключить низ 0% самых неактивных

WITH 
-- 1. Настройки групп
char_expansion AS (
    SELECT 
        '0,1,2,3,4,5,6,7' as control_chars_expanded,
        '8,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z' as test_chars_expanded,
        1 as char_position
),

-- 2. Получаем все депозиты с определением группы
deposits_with_groups AS (
    SELECT 
        ue.external_user_id as user_id,
        ue.event_date,
        ue.converted_amount as deposit_amount,
        ue.advertiser,
        -- Извлекаем символ на нужной позиции с конца
        CASE 
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
            THEN LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1))
            ELSE NULL
        END as char_at_position,
        -- Определяем группу
        CASE 
            -- Контрольная группа: символ входит в список control_chars
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
                 AND LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1)) = ANY(
                     string_to_array(ce.control_chars_expanded, ',')
                 ) THEN 'Control'
            -- Тестовая группа: символ входит в список test_chars
            WHEN LENGTH(ue.external_user_id) >= ce.char_position 
                 AND LOWER(SUBSTRING(ue.external_user_id FROM LENGTH(ue.external_user_id) - ce.char_position + 1 FOR 1)) = ANY(
                     string_to_array(ce.test_chars_expanded, ',')
                 ) THEN 'Test'
            ELSE 'Unknown'
        END as test_group
    FROM public.user_events ue
    CROSS JOIN char_expansion ce
    WHERE ue.event_type = 'deposit'
      AND ue.converted_amount > 0
      AND ue.external_user_id IS NOT NULL
      AND LENGTH(ue.external_user_id) >= ce.char_position
),

-- 3. Агрегируем по пользователям для расчета активности
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

-- 4. Исключаем выбросы (топ и низ активных игроков)
user_percentiles AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date,
        PERCENT_RANK() OVER (PARTITION BY test_group ORDER BY total_deposits_usd) as activity_percentile
    FROM user_totals
),

-- 5. Фильтруем выбросы
filtered_users AS (
    SELECT 
        user_id,
        test_group,
        deposit_count,
        total_deposits_usd,
        first_deposit_date,
        last_deposit_date
    FROM user_percentiles
    WHERE 
        activity_percentile <= (1.0 - 0 / 100.0)
        AND activity_percentile >= 0 / 100.0
),

-- 6. Возвращаемся к депозитам отфильтрованных пользователей
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

-- 7. Финальная агрегация по группам
group_comparison AS (
    SELECT 
        test_group,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_deposits,
        SUM(deposit_amount) as total_deposits_usd,
        AVG(deposit_amount) as avg_deposit_amount,
        COUNT(*)::NUMERIC / NULLIF(COUNT(DISTINCT user_id), 0) as avg_deposits_per_user,
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
