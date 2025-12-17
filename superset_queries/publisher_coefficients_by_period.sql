-- Отчет: Коэффициенты паблишеров в разрезе форматов с выбором периода
-- Поддерживает выбор месяца и разбивку по дням
-- 
-- Параметры Superset (установите в Query Settings -> Parameters):
--   - start_date: Дата начала периода (формат: 'YYYY-MM-DD', по умолчанию: '2025-11-01')
--   - end_date: Дата окончания периода (формат: 'YYYY-MM-DD', по умолчанию: '2025-11-30')
--   - min_spend: Минимальная сумма расходов для фильтрации (по умолчанию: 50)
--
-- Или используйте фильтры Dashboard для динамического выбора периода

WITH 
-- 1. Получаем данные о расходах за выбранный период
period_spend AS (
    SELECT 
        publisher_id,
        publisher_name,
        format,
        month,
        deposits_reported,
        spend,
        current_cpa
    FROM publisher_spend
    WHERE month >= COALESCE(SUBSTRING('{{ start_date }}'::text, 1, 7), '2025-11')  -- Извлекаем YYYY-MM из даты
      AND month <= COALESCE(SUBSTRING('{{ end_date }}'::text, 1, 7), '2025-11')
      AND publisher_id != 0  -- Исключаем органику
      AND spend >= COALESCE(CAST('{{ min_spend }}' AS NUMERIC), 50)  -- Минимальные расходы
),

-- 2. Находим PLR/NOR кампании за период
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
    FROM period_spend
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

-- 4. Рассчитываем коэффициенты для каждого паблишера
SELECT 
    ps.publisher_id,
    ps.publisher_name,
    ps.format,
    ps.month,
    COALESCE(tc.target_cpa, 0) as target_cpa_format,
    ps.current_cpa,
    ps.spend,
    ps.deposits_reported,
    -- Коэффициент = Target CPA / Current CPA
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0)
        ELSE 1.0
    END as coefficient,
    -- Процент изменения
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN ((LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) - 1) * 100)
        ELSE 0
    END as change_pct,
    -- Рекомендация
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 THEN
            CASE 
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 1.3 THEN 'УВЕЛИЧИТЬ ставку'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 1.1 THEN 'Увеличить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.9 THEN 'Оставить'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.7 THEN 'Снизить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.4 THEN 'СНИЗИТЬ ставку'
                ELSE 'отключить паблишера'
            END
        ELSE 'Нет данных'
    END as recommendation
FROM period_spend ps
LEFT JOIN target_cpa_by_format tc
    ON ps.format = tc.format
ORDER BY ps.format, ps.month, coefficient DESC;

