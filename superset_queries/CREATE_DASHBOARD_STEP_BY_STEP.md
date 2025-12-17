# Пошаговая инструкция: Создание Chart и Dashboard в Superset

## Шаг 1: Создание SQL Query

1. **Откройте Superset**: http://localhost:8088
   - Логин: `admin`
   - Пароль: `admin`

2. **Перейдите в SQL Lab**:
   - В верхнем меню нажмите **SQL** → **SQL Lab**

3. **Выберите базу данных**:
   - В выпадающем списке выберите **"Ubidex Events DB"**

4. **Вставьте SQL-запрос**:
   - Откройте файл `superset_queries/publisher_coefficients_by_period_simple.sql`
   - Скопируйте весь SQL-запрос
   - Вставьте в редактор SQL Lab

5. **Выполните запрос**:
   - Нажмите кнопку **"Run"** (или Ctrl+Enter)
   - Дождитесь результатов
   - Проверьте, что данные отображаются корректно

## Шаг 2: Создание Chart (Table)

1. **Создайте Chart из результатов**:
   - Нажмите кнопку **"Explore"** рядом с результатами запроса

2. **Настройте визуализацию**:
   - **Chart Type**: Выберите **"Table"**
   
   - **Query**:
     - **Columns** (Group by):
       - `publisher_name`
       - `format`
       - `month`
       - `coefficient`
       - `current_cpa`
       - `target_cpa_format`
       - `spend`
       - `deposits_reported`
       - `recommendation`
     
     - **Metrics** (добавьте через "+"):
       - `SUM(spend)` - Общие расходы
       - `SUM(deposits_reported)` - Общее количество депозитов
       - `AVG(coefficient)` - Средний коэффициент
       - `AVG(current_cpa)` - Средний CPA
     
     - **Filters** (опционально):
       - `format IN ('POP', 'PUSH', 'VIDEO', 'BANNER', 'NATIVE')`
       - `spend >= 50`
   
   - **Options**:
     - **Page Length**: 50
     - **Include Search**: ✓ (включено)
     - **Show Cell Bars**: ✓ (опционально)

3. **Сохраните Chart**:
   - Нажмите **"Save"** → **"Save chart"**
   - **Name**: "Коэффициенты паблишеров - Таблица"
   - **Description**: "Анализ коэффициентов по форматам с выбором периода"
   - **Add to Dashboard**: Выберите **"+ Add to new dashboard"**
   - **Dashboard name**: "Анализ паблишеров"
   - Нажмите **"Save"**

## Шаг 3: Создание дополнительных Charts

### Chart 2: Pivot Table (сводная таблица)

1. **Вернитесь в SQL Lab** и выполните тот же запрос
2. **Нажмите "Explore"**
3. **Chart Type**: Выберите **"Pivot Table"**
4. **Query**:
   - **Rows**: `format`
   - **Columns**: `month`
   - **Metrics**: 
     - `SUM(spend)`
     - `AVG(coefficient)`
     - `COUNT(DISTINCT publisher_id)`
5. **Сохраните** и добавьте в тот же Dashboard

### Chart 3: Bar Chart (график по форматам)

1. **SQL Lab** → выполните запрос → **"Explore"**
2. **Chart Type**: Выберите **"Bar Chart"**
3. **Query**:
   - **X Axis**: `format`
   - **Y Axis**: `AVG(coefficient)`
   - **Series**: `month` (для сравнения месяцев)
4. **Сохраните** и добавьте в Dashboard

### Chart 4: Line Chart (динамика по дням)

1. **SQL Lab** → используйте запрос `publisher_coefficients_by_day_simple.sql`
2. **Chart Type**: Выберите **"Line Chart"**
3. **Query**:
   - **X Axis**: `date`
   - **Y Axis**: `AVG(coefficient)`
   - **Series**: `format`
4. **Сохраните** и добавьте в Dashboard

## Шаг 4: Настройка Dashboard

1. **Откройте Dashboard**:
   - **Dashboards** → "Анализ паблишеров"
   - Нажмите **"Edit Dashboard"**

2. **Добавьте фильтры**:
   - Нажмите **"+ Filter"** (в правом верхнем углу)
   
   - **Filter 1: Date Range (для month)**:
     - **Filter Type**: "Date Range"
     - **Column**: `month`
     - **Default Value**: Выберите период (например, "Last 30 days" или конкретные месяцы)
     - **Name**: "Период"
   
   - **Filter 2: Select (для format)**:
     - **Filter Type**: "Select"
     - **Column**: `format`
     - **Default Value**: "All"
     - **Name**: "Формат"
   
   - **Filter 3: Numeric (для минимальных расходов)**:
     - **Filter Type**: "Numeric"
     - **Column**: `spend`
     - **Filter Type**: "Greater than or equal"
     - **Default Value**: `50`
     - **Name**: "Мин. расходы"

3. **Примените фильтры к Charts**:
   - Выберите каждый Chart
   - В настройках Chart найдите **"Scoping"**
   - Выберите фильтры, которые должны влиять на этот Chart:
     - Для Table: все фильтры
     - Для Pivot Table: все фильтры
     - Для Bar Chart: все фильтры
     - Для Line Chart: только Date Range и Format

4. **Настройте Layout**:
   - Перетащите Charts для удобного расположения
   - Измените размеры Charts (растяните/сожмите)
   - Рекомендуемый layout:
     - Фильтры вверху (1 строка)
     - Table внизу (полная ширина)
     - Pivot Table и Bar Chart рядом (по 2 колонки)
     - Line Chart внизу (полная ширина)

5. **Сохраните Dashboard**:
   - Нажмите **"Save"**

## Шаг 5: Настройка автообновления (опционально)

1. **В режиме редактирования Dashboard**:
   - Нажмите на иконку настроек (⚙️)
   - **Auto-refresh**: Выберите интервал (например, "5 minutes")
   - **Save**

## Готово!

Теперь у вас есть Dashboard с:
- ✅ Таблицей коэффициентов
- ✅ Сводной таблицей по форматам
- ✅ Графиком сравнения форматов
- ✅ Графиком динамики по дням
- ✅ Фильтрами для выбора периода и формата

**URL Dashboard**: http://localhost:8088/superset/dashboard/[ID]/

## Дополнительные советы

- **Экспорт данных**: В Table chart можно экспортировать данные в CSV
- **Алерты**: Настройте алерты для критических изменений коэффициентов
- **Публикация**: Dashboard можно опубликовать для общего доступа
- **Кэширование**: Настройте кэширование для ускорения загрузки

