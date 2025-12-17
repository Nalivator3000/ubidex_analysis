-- Отчет: Коэффициенты паблишеров в разрезе форматов с разбивкой по дням
-- 
-- Параметры Superset (опционально, можно использовать фильтры Dashboard):
--   - start_date: Дата начала периода (формат: 'YYYY-MM-DD')
--   - end_date: Дата окончания периода (формат: 'YYYY-MM-DD')
--   - min_spend: Минимальная сумма расходов для фильтрации
--
-- ВАЖНО: Для работы этого запроса нужна таблица publisher_spend_daily
-- Создайте её через скрипт load_daily_spend_to_postgresql.py

WITH 
-- 1. Получаем данные о расходах за выбранный период (по дням)
daily_spend AS (
    SELECT 
        publisher_id,
        publisher_name,
        format,
        date,
        deposits_reported,
        spend,
        current_cpa
    FROM publisher_spend_daily
    WHERE date >= COALESCE('{{ start_date }}'::date, (SELECT MIN(date) FROM publisher_spend_daily))
      AND date <= COALESCE('{{ end_date }}'::date, (SELECT MAX(date) FROM publisher_spend_daily))
      AND publisher_id != 0  -- Исключаем органику
      AND spend >= COALESCE(CAST('{{ min_spend }}' AS NUMERIC), 50)  -- Минимальные расходы
),

-- 2. Агрегируем данные по форматам за весь период для расчета целевых CPA
period_spend AS (
    SELECT 
        format,
        SUM(spend) as total_spend,
        SUM(deposits_reported) as total_deposits
    FROM daily_spend
    GROUP BY format
),

-- 3. Находим PLR/NOR кампании за период
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
    FROM daily_spend
    WHERE UPPER(publisher_name) LIKE '%PLR%' 
       OR UPPER(publisher_name) LIKE '%NOR%'
    GROUP BY format
),

-- 4. Рассчитываем целевые CPA по форматам (-30% от PLR/NOR)
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
        ps.format,
        CASE 
            WHEN SUM(ps.deposits_reported) > 0 
            THEN (SUM(ps.spend) / SUM(ps.deposits_reported)) * 0.7
            ELSE NULL
        END as target_cpa
    FROM period_spend ps
    WHERE ps.format NOT IN (
        SELECT format FROM plr_nor WHERE avg_cpa > 0
    )
    GROUP BY ps.format
)

-- 5. Рассчитываем коэффициенты для каждого паблишера по дням
SELECT 
    ds.date,
    ds.publisher_id,
    ds.publisher_name,
    ds.format,
    COALESCE(tc.target_cpa, 0) as target_cpa_format,
    ds.current_cpa,
    ds.spend,
    ds.deposits_reported,
    -- Коэффициент = Target CPA / Current CPA
    CASE 
        WHEN ds.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0)
        ELSE 1.0
    END as coefficient,
    -- Процент изменения
    CASE 
        WHEN ds.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN ((LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) - 1) * 100)
        ELSE 0
    END as change_pct,
    -- Рекомендация
    CASE 
        WHEN ds.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 THEN
            CASE 
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) >= 1.3 THEN 'УВЕЛИЧИТЬ ставку'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) >= 1.1 THEN 'Увеличить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) >= 0.9 THEN 'Оставить'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) >= 0.7 THEN 'Снизить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ds.current_cpa, 0.1), 3.0) >= 0.4 THEN 'СНИЗИТЬ ставку'
                ELSE 'отключить паблишера'
            END
        ELSE 'Нет данных'
    END as recommendation
FROM daily_spend ds
LEFT JOIN target_cpa_by_format tc
    ON ds.format = tc.format
ORDER BY ds.date, ds.format, coefficient DESC;

