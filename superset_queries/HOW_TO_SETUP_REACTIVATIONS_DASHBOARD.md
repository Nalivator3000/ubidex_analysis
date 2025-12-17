# Настройка Dashboard с фильтром по дате для реактиваций

Это руководство поможет настроить Dashboard, где пользователи смогут выбирать период через фильтр, а данные будут автоматически агрегироваться по периодам неактивности.

## Шаг 1: Создание Chart

1. Откройте **SQL Lab** в Superset
2. Выберите базу данных: **"Ubidex Events DB"**
3. Откройте файл `reactivations_summary_by_period_simple.sql`
4. Скопируйте SQL-запрос и вставьте в редактор
5. Нажмите **"Run"** для проверки

## Шаг 2: Создание Dataset

**ВАЖНО**: Для работы фильтров Dashboard нужно создать Dataset на основе SQL-запроса.

1. После выполнения запроса нажмите **"Save"** (вверху справа)
2. Выберите **"Save as dataset"**
3. Дайте имя Dataset: **"Реактивации по периодам"**
4. Убедитесь, что колонка `first_deposit` имеет тип **Date/Time** или **Temporal**
5. Нажмите **"Save"**

## Шаг 3: Создание Chart на основе Dataset

1. Перейдите в **Data** → **Charts** → **+ CHART**
2. Выберите созданный Dataset: **"Реактивации по периодам"**
3. Настройте визуализацию:

   **Для Bar Chart:**
   - **Visualization type**: `Bar Chart`
   - **Query mode**: `Aggregate`
   - **Group by**: `inactivity_period`
   - **Metrics**: `SUM(reactivations_count)`
   - Нажмите **"Run"**

   **Для Table:**
   - **Visualization type**: `Table`
   - **Query mode**: `Aggregate`
   - **Group by**: `inactivity_period`
   - **Metrics**: 
     - `SUM(reactivations_count)`
     - `AVG(avg_days_inactive)`
     - `AVG(percentage_of_reactivations)`
   - Нажмите **"Run"**

4. Нажмите **"SAVE"**
5. **Chart name**: "Реактивации по периодам"
6. **Add to new dashboard**: Создайте новый Dashboard "Анализ реактиваций"
7. Нажмите **"SAVE & GO TO DASHBOARD"**

## Шаг 4: Добавление фильтра по дате на Dashboard

1. На Dashboard нажмите **"Edit dashboard"**
2. Нажмите **"+ ADD FILTER"**
3. Выберите **"Date Range Filter"**
4. Настройте фильтр:
   - **Filter name**: "Период реактивации"
   - **Dataset**: Выберите **"Реактивации по периодам"**
   - **Time column**: `first_deposit`
   - **Default value**: Установите нужный диапазон (например, "Last 30 days" или "Custom...")
   - Нажмите **"SAVE"**

## Шаг 5: Настройка Scoping (связывание фильтра с Chart)

1. В режиме редактирования Dashboard нажмите на созданный фильтр
2. В разделе **"Scoping"** выберите:
   - **Chart**: "Реактивации по периодам"
3. Убедитесь, что фильтр применяется к Chart
4. Нажмите **"SAVE"**

## Шаг 6: Настройка агрегации в Chart

**ВАЖНО**: Фильтр Dashboard будет применяться к исходным данным (до агрегации), но Chart должен агрегировать данные по периодам.

1. Откройте Chart для редактирования
2. Убедитесь, что:
   - **Query mode**: `Aggregate` (не "Raw records")
   - **Group by**: `inactivity_period`
   - **Metrics**: `SUM(reactivations_count)`, `AVG(avg_days_inactive)`, и т.д.
3. Сохраните Chart

## Как это работает:

1. **SQL-запрос** обрабатывает ВСЕ данные (максимальный период)
2. **Dataset** содержит все записи с колонкой `first_deposit`
3. **Фильтр Dashboard** применяется к Dataset, фильтруя записи по `first_deposit`
4. **Chart** агрегирует отфильтрованные данные по `inactivity_period`
5. Пользователь видит только выбранный период, но данные правильно агрегированы по периодам неактивности

## Альтернативный способ (если фильтры Dashboard не работают):

Если фильтры Dashboard не применяются правильно:

1. Используйте **Custom SQL Filter** в Chart:
   - В Chart Builder перейдите в раздел **"Filters"**
   - Добавьте фильтр с Custom SQL:
     ```sql
     first_deposit >= '{{ start_date }}' AND first_deposit <= '{{ end_date }}'
     ```
   - Настройте параметры `start_date` и `end_date` в Query Settings

2. Или создайте несколько Chart для разных периодов и используйте фильтры на уровне Dashboard для переключения между ними.

## Проверка:

1. Откройте Dashboard
2. Измените период в фильтре "Период реактивации"
3. Chart должен автоматически обновиться, показывая данные только за выбранный период
4. Данные должны быть агрегированы по периодам неактивности (7-14 days, 14-30 days, и т.д.)

