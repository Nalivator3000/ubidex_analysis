-- Отчет: Коэффициенты паблишеров за ноябрь в разрезе форматов
-- Этот запрос повторяет логику из calculate_bid_coefficients.py

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
    SELECT 
        format,
        CASE 
            WHEN avg_cpa > 0 THEN avg_cpa * 0.7
            ELSE NULL
        END as target_cpa
    FROM plr_nor
    
    UNION ALL
    
    -- Если нет PLR/NOR для формата, используем среднее по всем кампаниям формата
    SELECT 
        ns.format,
        CASE 
            WHEN SUM(ns.deposits_reported) > 0 
            THEN (SUM(ns.spend) / SUM(ns.deposits_reported)) * 0.7
            ELSE NULL
        END as target_cpa
    FROM nov_spend ns
    WHERE ns.format NOT IN (SELECT format FROM plr_nor WHERE avg_cpa > 0)
    GROUP BY ns.format
),

-- 4. Получаем статистику депозитов из базы данных за ноябрь
user_first_deposit_ever AS (
    SELECT
        external_user_id,
        MIN(event_date) as first_deposit_ever
    FROM user_events
    WHERE event_type = 'deposit'
    GROUP BY external_user_id
),
nov_deposits AS (
    SELECT
        e.external_user_id,
        e.publisher_id,
        e.event_date,
        f.first_deposit_ever
    FROM user_events e
    LEFT JOIN user_first_deposit_ever f
        ON e.external_user_id = f.external_user_id
    WHERE e.event_type = 'deposit'
      AND e.event_date >= '2025-11-01 00:00:00'
      AND e.event_date <= '2025-11-30 23:59:59'
),
nov_db_stats AS (
    SELECT
        publisher_id,
        COUNT(*) as total_deps,
        SUM(CASE WHEN event_date = first_deposit_ever THEN 1 ELSE 0 END) as ftd_db,
        SUM(CASE WHEN event_date != first_deposit_ever THEN 1 ELSE 0 END) as rd_db
    FROM nov_deposits
    GROUP BY publisher_id
),

-- 5. Объединяем данные о расходах и депозитах
merged_data AS (
    SELECT 
        COALESCE(ns.publisher_id, nds.publisher_id) as publisher_id,
        ns.publisher_name,
        COALESCE(ns.format, 'OTHER') as format,
        COALESCE(ns.spend, 0) as spend,
        COALESCE(ns.current_cpa, 0) as current_cpa,
        COALESCE(nds.total_deps, 0) as total_deps,
        COALESCE(nds.ftd_db, 0) as ftd_db,
        COALESCE(nds.rd_db, 0) as rd_db,
        COALESCE(tc.target_cpa, 0) as target_cpa_format
    FROM nov_spend ns
    FULL OUTER JOIN nov_db_stats nds
        ON ns.publisher_id = nds.publisher_id
    LEFT JOIN target_cpa_by_format tc
        ON COALESCE(ns.format, 'OTHER') = tc.format
    WHERE COALESCE(ns.spend, 0) > 50  -- Только паблишеры со значительными расходами
      AND COALESCE(ns.publisher_id, nds.publisher_id) != 0  -- Исключаем органику
)

-- 6. Рассчитываем коэффициенты
SELECT 
    publisher_id,
    publisher_name,
    format,
    target_cpa_format,
    current_cpa,
    spend,
    total_deps,
    ftd_db,
    rd_db,
    -- Коэффициент = Target CPA / Current CPA
    CASE 
        WHEN current_cpa > 0 AND target_cpa_format > 0 
        THEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0)
        ELSE 1.0
    END as coefficient,
    -- Процент изменения
    CASE 
        WHEN current_cpa > 0 AND target_cpa_format > 0 
        THEN ((LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) - 1) * 100)
        ELSE 0
    END as change_pct,
    -- Рекомендация
    CASE 
        WHEN current_cpa > 0 AND target_cpa_format > 0 THEN
            CASE 
                WHEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) >= 1.3 THEN 'УВЕЛИЧИТЬ ставку'
                WHEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) >= 1.1 THEN 'Увеличить немного'
                WHEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) >= 0.9 THEN 'Оставить'
                WHEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) >= 0.7 THEN 'Снизить немного'
                WHEN LEAST(GREATEST(target_cpa_format / current_cpa, 0.1), 3.0) >= 0.4 THEN 'СНИЗИТЬ ставку'
                ELSE 'отключить паблишера'
            END
        ELSE 'Нет данных'
    END as recommendation
FROM merged_data
ORDER BY format, coefficient DESC;

