# Быстрое создание Dashboard (5 минут)

## Минимальные шаги для создания Dashboard:

### 1. SQL Lab → Выполните запрос (1 мин)
- Откройте: http://localhost:8088
- SQL → SQL Lab
- База: "Ubidex Events DB"
- Вставьте SQL из `publisher_coefficients_by_period_simple.sql`
- Run

### 2. Создайте Chart (2 мин)
- Нажмите **"Explore"**
- Chart Type: **"Table"**
- Columns: publisher_name, format, month, coefficient, recommendation
- Metrics: SUM(spend), AVG(coefficient)
- **Save** → "+ Add to new dashboard" → "Анализ паблишеров"

### 3. Добавьте фильтры (2 мин)
- Откройте Dashboard → **Edit**
- **"+ Filter"** → **"Select"** → Column: `format`
- **"+ Filter"** → **"Date Range"** → Column: `month`
- Примените фильтры к Chart (Scoping)

### Готово! 🎉

**Подробная инструкция**: См. [CREATE_DASHBOARD_STEP_BY_STEP.md](CREATE_DASHBOARD_STEP_BY_STEP.md)

