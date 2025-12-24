-- Проверка диапазона дат в базе данных
-- Показывает минимальную и максимальную даты, количество записей по типам событий

SELECT 
    'Общая информация' as info_type,
    MIN(event_date)::date as min_date,
    MAX(event_date)::date as max_date,
    COUNT(*) as total_events,
    COUNT(DISTINCT external_user_id) as unique_users,
    COUNT(DISTINCT DATE(event_date)) as unique_days
FROM public.user_events;

-- Детальная информация по типам событий
SELECT 
    'По типам событий' as info_type,
    event_type,
    MIN(event_date)::date as min_date,
    MAX(event_date)::date as max_date,
    COUNT(*) as total_events,
    COUNT(DISTINCT external_user_id) as unique_users
FROM public.user_events
GROUP BY event_type
ORDER BY event_type;

-- Распределение по месяцам
SELECT 
    'По месяцам' as info_type,
    DATE_TRUNC('month', event_date)::date as month,
    COUNT(*) as total_events,
    COUNT(DISTINCT external_user_id) as unique_users
FROM public.user_events
GROUP BY DATE_TRUNC('month', event_date)
ORDER BY month DESC;

