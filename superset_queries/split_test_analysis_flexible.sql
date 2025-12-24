-- Анализ сплит-теста: сравнение контрольной и тестовой групп (ГИБКАЯ ВЕРСИЯ)
-- 
-- Параметры для настройки групп:
-- - char_position: позиция символа с конца (1 = последний, 2 = предпоследний, и т.д.)
-- - control_chars: символы для контрольной группы (например: '0,1,2,3,4,5,6,7' или '0-7')
-- - test_chars: символы для тестовой группы (например: '8,9,a-z' или '8-9a-z')
--
-- Примеры использования:
-- 1. Последний символ, Control: 0-7, Test: 8-9a-z (по умолчанию)
--    char_position = 1, control_chars = '0,1,2,3,4,5,6,7', test_chars = '8,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z'
--
-- 2. Предпоследний символ, Control: 0-3, Test: 4-9a-z
--    char_position = 2, control_chars = '0,1,2,3', test_chars = '4,5,6,7,8,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z'
--
-- 3. Третий с конца, Control: четные 0-9, Test: нечетные 0-9 + a-z
--    char_position = 3, control_chars = '0,2,4,6,8', test_chars = '1,3,5,7,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z'
--
-- Для использования:
-- 1. Создайте Dataset на основе этого запроса
-- 2. В SQL замените параметры на нужные значения
-- 3. Или используйте параметры Superset (если поддерживаются)
-- 4. Добавьте фильтры на Dashboard для дат

WITH 
-- 1. Функция для расширения диапазонов символов (например, '0-7' -> '0,1,2,3,4,5,6,7')
-- В PostgreSQL можно использовать регулярные выражения или простую логику
char_expansion AS (
    SELECT 
        -- Расширяем диапазоны для контрольной группы
        -- Пример: '0-7' -> '0,1,2,3,4,5,6,7'
        -- Для простоты будем использовать прямой список символов
        '0,1,2,3,4,5,6,7' as control_chars_expanded,
        '8,9,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z' as test_chars_expanded,
        1 as char_position  -- Позиция символа с конца (1 = последний)
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
      AND LENGTH(ue.external_user_id) >= ce.char_position  -- Проверяем, что user_id достаточно длинный
      -- Фильтрация по дате применяется через Dashboard фильтры (Time Range Filter)
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
        -- Процентиль активности внутри группы (по сумме депозитов)
        PERCENT_RANK() OVER (PARTITION BY test_group ORDER BY total_deposits_usd) as activity_percentile
    FROM user_totals
),

-- 5. Фильтруем выбросы (если указаны параметры)
-- Для исключения выбросов измените значения ниже:
-- exclude_top_percent = 5 означает исключить топ 5% самых активных
-- exclude_bottom_percent = 5 означает исключить низ 5% самых неактивных
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
        -- Измените 0.0 на нужное значение (например, 0.05 для 5%)
        activity_percentile <= (1.0 - 0.0)
        -- Исключаем низ M% самых неактивных (по умолчанию 0 = не исключаем)
        -- Измените 0.0 на нужное значение (например, 0.05 для 5%)
        AND activity_percentile >= 0.0
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

