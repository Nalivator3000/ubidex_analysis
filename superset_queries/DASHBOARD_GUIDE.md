# Руководство по созданию Dashboard в Superset

## Создание отчета "Коэффициенты паблишеров по форматам"

### Шаг 1: Создание SQL Query с параметрами

1. **Откройте Superset**: http://localhost:8088
2. **SQL Lab**: Перейдите в **SQL** → **SQL Lab**
3. **Выберите базу данных**: "Ubidex Events DB"
4. **Откройте SQL-запрос**:
   - Для месячных данных: `publisher_coefficients_by_period.sql`
   - Для дневных данных: `publisher_coefficients_by_day.sql`
5. **Вставьте SQL-запрос** в редактор

### Шаг 2: Настройка параметров запроса

В Superset есть два способа работы с параметрами:

#### Вариант A: Template Variables (в SQL-запросе)

1. В SQL-запросе используйте синтаксис `{{ variable }}`
2. В **Query Settings** (справа) найдите раздел **Template Parameters**
3. Добавьте параметры:
   - `start_date`: `'2025-11-01'` (строка)
   - `end_date`: `'2025-11-30'` (строка)
   - `min_spend`: `50` (число)

#### Вариант B: Фильтры на уровне Dashboard (рекомендуется)

1. Создайте запрос БЕЗ параметров (используйте значения по умолчанию)
2. После создания Chart, добавьте фильтры на Dashboard

### Шаг 3: Выполнение запроса и создание Chart

1. **Выполните запрос**: Нажмите **Run** (или Ctrl+Enter)
2. **Проверьте результаты**: Убедитесь, что данные отображаются корректно
3. **Создайте Chart**: Нажмите кнопку **"Explore"** рядом с результатами

### Шаг 4: Настройка визуализации

#### Для табличного отчета (Table):

1. **Chart Type**: Выберите **"Table"**
2. **Query**:
   - **Columns**: 
     - `publisher_name`
     - `format`
     - `month` (или `date` для дневной разбивки)
     - `coefficient`
     - `current_cpa`
     - `target_cpa_format`
     - `recommendation`
   - **Metrics**:
     - `SUM(spend)` - Общие расходы
     - `SUM(deposits_reported)` - Общее количество депозитов
     - `AVG(coefficient)` - Средний коэффициент
   - **Filters** (опционально):
     - `format IN ('POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE')`
     - `coefficient >= 0.9` - Только эффективные паблишеры
3. **Нажмите "Create chart"**

#### Для Pivot Table (сводная таблица):

1. **Chart Type**: Выберите **"Pivot Table"**
2. **Query**:
   - **Rows**: `format`
   - **Columns**: `month` (или `date`)
   - **Metrics**:
     - `SUM(spend)` - Расходы
     - `AVG(coefficient)` - Средний коэффициент
     - `COUNT(DISTINCT publisher_id)` - Количество паблишеров
3. **Нажмите "Create chart"**

#### Для графика по форматам:

1. **Chart Type**: Выберите **"Bar Chart"** или **"Line Chart"**
2. **Query**:
   - **X Axis**: `format`
   - **Y Axis**: `AVG(coefficient)` или `SUM(spend)`
   - **Series**: `month` (для сравнения месяцев)
3. **Нажмите "Create chart"**

### Шаг 5: Создание Dashboard

1. **Сохраните Chart**: Нажмите **"Save"** → **"Save chart"**
   - Название: "Коэффициенты паблишеров - Ноябрь"
   - Описание: "Анализ коэффициентов по форматам"
   - Добавьте в Dashboard: **"+ Add to new dashboard"** или выберите существующий

2. **Создайте Dashboard**:
   - Название: "Анализ паблишеров"
   - Описание: "Коэффициенты и рекомендации по паблишерам"

3. **Добавьте фильтры на Dashboard**:
   - Нажмите **"Edit Dashboard"**
   - Нажмите **"+ Filter"**
   - Выберите тип фильтра:
     - **Date Range Filter**: для выбора периода (`month` или `date`)
     - **Select Filter**: для выбора формата (`format`)
     - **Numeric Filter**: для минимальных расходов (`min_spend`)

4. **Настройте фильтры**:
   - **Date Range Filter**:
     - Column: `month` (или `date`)
     - Default Value: `Last 30 days` или конкретный период
   - **Select Filter** (Format):
     - Column: `format`
     - Default Value: `All`
   - **Numeric Filter** (Min Spend):
     - Column: `spend`
     - Filter Type: `Greater than or equal`
     - Default Value: `50`

5. **Примените фильтры к Charts**:
   - Выберите Chart
   - В настройках Chart найдите **"Scoping"**
   - Выберите фильтры, которые должны влиять на этот Chart

### Шаг 6: Добавление дополнительных Charts

Создайте несколько Charts для полного анализа:

1. **Сводная таблица по форматам** (Pivot Table)
2. **Топ паблишеров для увеличения ставки** (Table с фильтром `coefficient >= 1.3`)
3. **Топ паблишеров для снижения ставки** (Table с фильтром `coefficient < 0.7`)
4. **График динамики коэффициентов** (Line Chart по дням/месяцам)
5. **Распределение рекомендаций** (Pie Chart по `recommendation`)

### Шаг 7: Настройка Dashboard Layout

1. **Расположите Charts**: Перетащите Charts для удобного расположения
2. **Измените размеры**: Растяните Charts для лучшей видимости
3. **Сохраните Dashboard**: Нажмите **"Save"**

### Полезные SQL-запросы для дополнительных Charts

#### Топ паблишеров для увеличения ставки:

```sql
-- Используйте publisher_coefficients_by_period.sql
-- Добавьте в WHERE: AND coefficient >= 1.3
-- Сортируйте по: ORDER BY coefficient DESC
```

#### Статистика по форматам:

```sql
SELECT 
    format,
    COUNT(DISTINCT publisher_id) as publishers,
    SUM(spend) as total_spend,
    AVG(coefficient) as avg_coefficient,
    AVG(current_cpa) as avg_cpa,
    AVG(target_cpa_format) as avg_target_cpa
FROM (
    -- Ваш основной запрос publisher_coefficients_by_period.sql
) subquery
GROUP BY format
ORDER BY total_spend DESC;
```

## Загрузка данных за другие месяцы

### Через скрипт Python:

```bash
# Скопируйте CSV файл в data/
copy C:\Users\Nalivator3000\Downloads\export_october.csv data\spend_october.csv

# Запустите скрипт загрузки (обновите скрипт для указания месяца)
docker exec -it ubidex_analysis python scripts/load_spend_to_postgresql.py
```

### Вручную через SQL:

```sql
-- Вставьте данные за другой месяц
INSERT INTO publisher_spend (publisher_id, publisher_name, format, month, deposits_reported, spend, current_cpa)
VALUES 
    (123, 'Publisher Name', 'POP', '2025-10', 100, 1000.00, 10.000),
    ...
ON CONFLICT (publisher_id, month) DO UPDATE SET
    spend = EXCLUDED.spend,
    deposits_reported = EXCLUDED.deposits_reported,
    current_cpa = EXCLUDED.current_cpa;
```

## Разбивка по дням

Для дневной разбивки нужно:

1. **Создать таблицу `publisher_spend_daily`**:
   ```sql
   CREATE TABLE publisher_spend_daily (
       id SERIAL PRIMARY KEY,
       publisher_id BIGINT NOT NULL,
       publisher_name VARCHAR(255),
       format VARCHAR(50),
       date DATE NOT NULL,
       deposits_reported INTEGER,
       spend NUMERIC(15, 2),
       current_cpa NUMERIC(10, 3),
       UNIQUE(publisher_id, date)
   );
   ```

2. **Загрузить дневные данные** через скрипт или вручную

3. **Использовать SQL-запрос** `publisher_coefficients_by_day.sql`

## Советы

- Используйте **кэширование** для ускорения Dashboard (в настройках Chart)
- Настройте **автообновление** Dashboard (в настройках Dashboard)
- Добавьте **алерты** для критических изменений коэффициентов
- Экспортируйте Dashboard в PDF для отчетов

