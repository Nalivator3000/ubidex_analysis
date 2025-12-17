-- Упрощенный отчет: Коэффициенты паблишеров за ноябрь в разрезе форматов
-- Работает ТОЛЬКО с данными о расходах (publisher_spend)
-- Не требует миграции user_events

WITH 
-- 1. Получаем данные о расходах за ноябрь
nov_spend AS (
    SELECT 
        publisher_id,
        publisher_name,
        format,
        deposits_reported,
        spend,
        current_cpa
    FROM publisher_spend
    WHERE month = '2025-11'
      AND publisher_id != 0  -- Исключаем органику
      AND spend > 50  -- Только паблишеры со значительными расходами
),

-- 2. Находим PLR/NOR кампании
plr_nor AS (
    SELECT 
        format,
        SUM(spend) as total_spend,
        SUM(deposits_reported) as total_deposits,
        CASE 
            WHEN SUM(deposits_reported) > 0 
            THEN SUM(spend) / SUM(deposits_reported) 
            ELSE 0 
        END as avg_cpa
    FROM nov_spend
    WHERE UPPER(publisher_name) LIKE '%PLR%' 
       OR UPPER(publisher_name) LIKE '%NOR%'
    GROUP BY format
),

-- 3. Рассчитываем целевые CPA по форматам (-30% от PLR/NOR)
target_cpa_by_format AS (
    -- Сначала берем из PLR/NOR
    SELECT 
        format,
        CASE 
            WHEN avg_cpa > 0 THEN avg_cpa * 0.7
            ELSE NULL
        END as target_cpa
    FROM plr_nor
    WHERE avg_cpa > 0
    
    UNION
    
    -- Если нет PLR/NOR для формата, используем среднее по всем кампаниям формата
    SELECT 
        ns.format,
        CASE 
            WHEN SUM(ns.deposits_reported) > 0 
            THEN (SUM(ns.spend) / SUM(ns.deposits_reported)) * 0.7
            ELSE NULL
        END as target_cpa
    FROM nov_spend ns
    WHERE ns.format NOT IN (
        SELECT format FROM plr_nor WHERE avg_cpa > 0
    )
    GROUP BY ns.format
)

-- 4. Рассчитываем коэффициенты для каждого паблишера
SELECT 
    ns.publisher_id,
    ns.publisher_name,
    ns.format,
    COALESCE(tc.target_cpa, 0) as target_cpa_format,
    ns.current_cpa,
    ns.spend,
    ns.deposits_reported,
    -- Коэффициент = Target CPA / Current CPA
    CASE 
        WHEN ns.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0)
        ELSE 1.0
    END as coefficient,
    -- Процент изменения
    CASE 
        WHEN ns.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN ((LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) - 1) * 100)
        ELSE 0
    END as change_pct,
    -- Рекомендация
    CASE 
        WHEN ns.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 THEN
            CASE 
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) >= 1.3 THEN 'УВЕЛИЧИТЬ ставку'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) >= 1.1 THEN 'Увеличить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) >= 0.9 THEN 'Оставить'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) >= 0.7 THEN 'Снизить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ns.current_cpa, 0.1), 3.0) >= 0.4 THEN 'СНИЗИТЬ ставку'
                ELSE 'отключить паблишера'
            END
        ELSE 'Нет данных'
    END as recommendation
FROM nov_spend ns
LEFT JOIN target_cpa_by_format tc
    ON ns.format = tc.format
ORDER BY ns.format, coefficient DESC;

