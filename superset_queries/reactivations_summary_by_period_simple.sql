-- Отчет: Сводка реактиваций по периодам неактивности
-- Использует материализованное представление для быстрой работы
-- Обрабатывает ВСЕ данные (максимальный период)
-- Фильтрация по дате выполняется через Dashboard фильтры
-- 
-- ВАЖНО: Перед использованием создайте материализованное представление:
--   docker exec -it ubidex_analysis python scripts/create_reactivations_materialized_view.py
-- 
-- Для использования:
-- 1. Создайте Chart на основе этого запроса
-- 2. В Chart Builder используйте режим "Aggregate" и Group by: inactivity_period
-- 3. На Dashboard добавьте Date Range Filter для колонки first_deposit
-- 4. Настройте Scoping, чтобы фильтр применялся к Chart
--
-- Визуализации:
-- - Bar Chart: для графика количества реактиваций по периодам
-- - Pie Chart: для распределения по периодам
-- - Table: для табличного представления

-- Используем материализованное представление для быстрого доступа ко всем реактивациям
-- Фильтрация по дате будет применяться через Dashboard фильтры
SELECT
    user_id,
    inactivity_period,  -- Категория периода неактивности (7-14 days, 14-30 days, и т.д.)
    first_deposit,  -- ДАТА РЕАКТИВАЦИИ - используйте эту колонку для фильтрации по дате
    days_inactive
FROM reactivations_materialized
ORDER BY first_deposit, inactivity_period;

