# Руководство по анализу реактиваций

Это руководство поможет вам создать Dashboard в Superset для анализа реактиваций пользователей.

## Что такое реактивация?

Реактивация - это когда пользователь, который ранее делал депозиты, возвращается и делает новый депозит после периода неактивности.

Периоды неактивности:
- **7-14 days**: Реактивация через 1-2 недели
- **14-30 days**: Реактивация через 2-4 недели
- **30-90 days**: Реактивация через 1-3 месяца
- **90+ days**: Реактивация через 3+ месяца

## 1. Создание Chart для сводки реактиваций

### Шаг 1: SQL Lab

1. Откройте Superset: http://localhost:8088
2. Перейдите в **SQL** → **SQL Lab**
3. Выберите базу данных: **"Ubidex Events DB"**
4. Откройте файл `reactivations_summary_by_period_simple.sql`
5. Скопируйте весь SQL-запрос и вставьте в редактор
6. Нажмите **"Run"**

### Шаг 2: Создание Chart

1. Нажмите **"Explore"** рядом с результатами
2. Настройте визуализацию:

   **Для Bar Chart (график):**
   - **Visualization type**: `Bar Chart`
   - **Time column**: Не требуется
   - **Group by**: `inactivity_period`
   - **Metrics**: `SUM(reactivations_count)`
   - Нажмите **"Run"** для предпросмотра

   **Для Pie Chart (круговая диаграмма):**
   - **Visualization type**: `Pie Chart`
   - **Group by**: `inactivity_period`
   - **Metrics**: `SUM(reactivations_count)`
   - Нажмите **"Run"** для предпросмотра

   **Для Table (таблица):**
   - **Visualization type**: `Table`
   - **Group by**: `inactivity_period`
   - **Metrics**: 
     - `SUM(reactivations_count)`
     - `AVG(avg_days_inactive)`
     - `AVG(percentage_of_reactivations)`
   - Нажмите **"Run"** для предпросмотра

3. Нажмите **"SAVE"** (вверху справа)
4. **Chart name**: "Реактивации по периодам"
5. **Add to new dashboard**: Создайте новый Dashboard "Анализ реактиваций"
6. Нажмите **"SAVE & GO TO DASHBOARD"**

## 2. Создание Chart для детальной таблицы

1. Вернитесь в **SQL Lab**
2. Откройте файл `reactivations_by_period_simple.sql`
3. Скопируйте SQL-запрос и выполните его
4. Нажмите **"Explore"**
5. Настройте:
   - **Visualization type**: `Table`
   - **Time column**: `first_deposit`
   - **Group by**: Не требуется (детальная таблица)
   - **Metrics**: Не требуется
   - **Columns**: Выберите нужные колонки (user_id, first_deposit, days_inactive, inactivity_period)
6. Нажмите **"SAVE"**
7. **Chart name**: "Детальная таблица реактиваций"
8. **Add to existing dashboard**: Выберите "Анализ реактиваций"
9. Нажмите **"SAVE & GO TO DASHBOARD"**

## 3. Настройка Dashboard с фильтрами

1. На Dashboard нажмите **"Edit dashboard"**
2. Нажмите **"+ ADD FILTER"**

### Фильтр по дате реактивации:

1. **Filter type**: `Time range`
2. **Filter name**: "Период реактивации"
3. **Dataset**: Выберите Dataset на основе `reactivations_by_period_simple.sql` (если создан) или используйте Dataset из `user_events`
4. **Time column**: `first_deposit` (или `event_date` если используете Dataset из user_events)
5. **Default value**: Установите нужный диапазон (например, "Last 30 days")
6. Нажмите **"SAVE"**

### Настройка Scoping:

1. После создания фильтра, нажмите на него в режиме редактирования
2. В разделе **"Scoping"** выберите:
   - **Chart**: "Реактивации по периодам"
   - **Chart**: "Детальная таблица реактиваций"
3. Убедитесь, что фильтр применяется к обоим Chart
4. Нажмите **"SAVE"**

## 4. Использование скрипта для расчета по списку пользователей

Если у вас есть конкретный список пользователей, для которых нужно рассчитать реактивации:

### Подготовка CSV файла:

Создайте CSV файл с колонкой `user_id` или `external_user_id`:

```csv
user_id
user123
user456
user789
```

### Запуск скрипта:

```bash
# Из CSV файла
docker exec -it ubidex_analysis python scripts/calculate_reactivations_by_user_list.py \
  --users data/user_list.csv \
  --start-date 2025-11-01 \
  --end-date 2025-11-30

# Из списка ID (через запятую)
docker exec -it ubidex_analysis python scripts/calculate_reactivations_by_user_list.py \
  --users "user1,user2,user3" \
  --start-date 2025-11-01 \
  --end-date 2025-11-30 \
  --output my_reactivations
```

### Результаты:

Скрипт создаст два файла:
- `*_detail.csv` - детальная информация по каждой реактивации:
  - user_id
  - first_deposit
  - prev_deposit_date
  - days_inactive
  - period

- `*_summary.csv` - сводка по периодам неактивности:
  - period
  - count (количество реактиваций)
  - avg_days (средние дни неактивности)
  - percentage (процент от всех реактиваций)

## 5. Примеры использования

### Пример 1: Анализ реактиваций за ноябрь

1. Создайте Chart на основе `reactivations_summary_by_period_simple.sql`
2. Добавьте фильтр по дате: `first_deposit` от 2025-11-01 до 2025-11-30
3. Получите распределение реактиваций по периодам неактивности

### Пример 2: Сравнение реактиваций по месяцам

1. Создайте несколько Chart для разных месяцев
2. Добавьте их на один Dashboard
3. Сравните распределение реактиваций по периодам

### Пример 3: Анализ конкретной группы пользователей

1. Подготовьте CSV файл со списком user_id
2. Запустите скрипт `calculate_reactivations_by_user_list.py`
3. Проанализируйте результаты в CSV файлах

## Требования

- Таблица `user_events` должна быть мигрирована в PostgreSQL
- Для работы фильтров по дате нужен Dataset на основе `user_events` или SQL-запроса

## Полезные SQL-запросы

Все SQL-запросы находятся в директории `superset_queries/`:
- `reactivations_by_period_simple.sql` - детальная таблица (без параметров)
- `reactivations_summary_by_period_simple.sql` - сводка (без параметров)
- `reactivations_by_period.sql` - детальная таблица (с параметрами)
- `reactivations_summary_by_period.sql` - сводка (с параметрами)

