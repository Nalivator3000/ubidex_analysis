# Настройка Chart для анализа сплит-теста

## Описание

Chart для сравнения контрольной и тестовой групп пользователей по депозитам.

**Гибкие настройки:**
- Позиция символа с конца: 1 (последний), 2 (предпоследний), 3 (третий), и т.д.
- Диапазон символов для контрольной группы (настраивается)
- Диапазон символов для тестовой группы (настраивается)

**Стандартные группы (по умолчанию):**
- **Control (25%)**: последний символ 0-7
- **Test (75%)**: последний символ 8-9a-z

## Шаг 1: Выбор варианта SQL запроса

### Вариант A: Стандартный (последний символ, Control: 0-7, Test: 8-9a-z)
- Используйте: `split_test_analysis.sql`

### Вариант B: Гибкий (настраиваемые параметры)
- Используйте: `split_test_analysis_flexible.sql`
- Отредактируйте CTE `char_expansion` для изменения параметров

### Вариант C: Генерация через скрипт
```bash
python 07_scripts/generate_split_test_variant.py \
  --position 1 \
  --control "0-7" \
  --test "8-9a-z" \
  --exclude-top 5 \
  --exclude-bottom 5 \
  --output superset_queries/split_test_custom.sql
```

**Примеры команд:**
```bash
# Предпоследний символ, Control: 0-3, Test: 4-9a-z
python 07_scripts/generate_split_test_variant.py --position 2 --control "0-3" --test "4-9a-z" -o split_test_pos2.sql

# Третий с конца, Control: четные 0-8, Test: нечетные 1-9 + a-z
python 07_scripts/generate_split_test_variant.py --position 3 --control "0,2,4,6,8" --test "1,3,5,7,9,a-z" -o split_test_pos3.sql

# С исключением выбросов (топ 5% и низ 5%)
python 07_scripts/generate_split_test_variant.py --position 1 --control "0-7" --test "8-9a-z" --exclude-top 5 --exclude-bottom 5 -o split_test_no_outliers.sql
```

## Шаг 2: Создание Dataset

1. Откройте Superset → **SQL Lab**
2. Скопируйте SQL из выбранного файла
3. Выполните запрос (проверьте, что он работает)
4. Нажмите **"Save"** → **"Save as dataset"**
5. Название: `Split Test Analysis` (или другое, если используете несколько вариантов)
6. Нажмите **"Save"**

## Шаг 3: Создание Chart

### Вариант A: Автоматическое создание через скрипт

```bash
python 07_scripts/create_split_test_chart.py
```

Скрипт автоматически:
- Создаст Dataset (если не существует)
- Создаст Chart типа Table
- Настроит базовые метрики

### Вариант B: Ручное создание

1. Откройте Superset → **Charts** → **+ Chart**
2. Выберите Dataset: **"Split Test Analysis"**
3. Выберите Chart Type: **"Table"**
4. Настройте метрики:
   - **Уникальных пользователей**: `SUM("Уникальных пользователей")`
   - **Всего депозитов**: `SUM("Всего депозитов")`
   - **Сумма депозитов (USD)**: `SUM("Сумма депозитов (USD)")`
   - **Средний депозит (USD)**: `AVG("Средний депозит (USD)")`
   - **Среднее депозитов на пользователя**: `AVG("Среднее депозитов на пользователя")`
   - **Средняя сумма на пользователя (USD)**: `AVG("Средняя сумма на пользователя (USD)")`
5. Group by: **"Группа"**
6. Нажмите **"Run Query"** для проверки
7. Нажмите **"Save"**
8. Название: `Split Test Comparison`

## Шаг 4: Создание Dashboard

1. Откройте Superset → **Dashboards** → **+ Dashboard**
2. Название: `Split Test Analysis`
3. Добавьте Chart: **"Split Test Comparison"**
4. Нажмите **"Save"**

## Шаг 5: Добавление фильтров

### Фильтр 1: Time Range (даты)

1. На Dashboard нажмите **"Edit Dashboard"**
2. Нажмите **"+ Add Filter"**
3. Выберите тип: **"Time Range"**
4. Настройки:
   - **Column**: `event_date` (если доступно) или используйте фильтр на уровне Dataset
   - **Default Value**: Последние 30 дней (или нужный период)
5. **Scoping**: Примените к Chart "Split Test Comparison"
6. Нажмите **"Save"**

### Фильтр 2: Исключение выбросов (опционально)

**Важно:** Текущая версия SQL не поддерживает параметры для исключения выбросов через фильтры Dashboard. 

Для исключения выбросов нужно:

#### Вариант A: Изменить SQL запрос вручную

Отредактируйте Dataset → SQL и замените строки в `filtered_users`:

```sql
-- Исключить топ 5% самых активных:
activity_percentile <= 0.95

-- Исключить низ 5% самых неактивных:
AND activity_percentile >= 0.05
```

#### Вариант B: Создать отдельные Dataset для разных вариантов

Создайте несколько Dataset:
- `Split Test Analysis (no outliers)` - без выбросов
- `Split Test Analysis (exclude top 5%)` - исключить топ 5%
- `Split Test Analysis (exclude bottom 5%)` - исключить низ 5%

## Шаг 5: Дополнительные метрики (опционально)

Можно добавить дополнительные Charts для визуализации:

### Chart 2: Bar Chart - Сравнение по группам

1. Создайте новый Chart
2. Dataset: `Split Test Analysis`
3. Chart Type: **"Bar Chart"**
4. Metrics:
   - `SUM("Сумма депозитов (USD)")`
   - `SUM("Всего депозитов")`
5. Group by: **"Группа"**
6. Название: `Split Test - Revenue Comparison`

### Chart 3: Line Chart - Тренд по датам

Для этого нужно изменить SQL запрос, чтобы группировать по датам:

```sql
-- Добавьте в group_comparison:
DATE_TRUNC('day', event_date) as deposit_date,

-- И в GROUP BY:
GROUP BY test_group, DATE_TRUNC('day', event_date)
```

## Метрики в Chart

### Основные метрики:

1. **Уникальных пользователей** - количество уникальных пользователей в группе
2. **Всего депозитов** - общее количество депозитов
3. **Сумма депозитов (USD)** - общая сумма всех депозитов в USD
4. **Средний депозит (USD)** - средний размер одного депозита
5. **Среднее депозитов на пользователя** - среднее количество депозитов на пользователя
6. **Средняя сумма на пользователя (USD)** - средняя сумма депозитов на пользователя (ARPPU)

### Расчет разницы между группами:

Для расчета разницы можно добавить вычисляемую метрику в Chart:

```sql
-- Разница в процентах (Test vs Control):
((SUM("Сумма депозитов (USD)") FILTER (WHERE "Группа" = 'Test') - 
  SUM("Сумма депозитов (USD)") FILTER (WHERE "Группа" = 'Control')) / 
  SUM("Сумма депозитов (USD)") FILTER (WHERE "Группа" = 'Control')) * 100
```

## Проверка данных

Перед использованием проверьте:

1. **Распределение групп:**
   ```sql
   SELECT 
       test_group,
       COUNT(DISTINCT user_id) as users,
       COUNT(*) as deposits
   FROM (
       -- Ваш SQL запрос
   ) 
   GROUP BY test_group;
   ```
   
   Ожидаемое распределение:
   - Control: ~25% пользователей
   - Test: ~75% пользователей

2. **Проверка user_id:**
   ```sql
   SELECT 
       RIGHT(LOWER(external_user_id), 1) as last_char,
       COUNT(DISTINCT external_user_id) as users
   FROM public.user_events
   WHERE event_type = 'deposit'
   GROUP BY RIGHT(LOWER(external_user_id), 1)
   ORDER BY last_char;
   ```

## Устранение неполадок

### Проблема: Chart показывает "No data"

**Решение:**
1. Проверьте, что в базе данных есть депозиты
2. Проверьте фильтры по датам
3. Убедитесь, что `external_user_id` не NULL

### Проблема: Неправильное распределение групп

**Решение:**
1. Проверьте формат `external_user_id` (должен быть строкой)
2. Убедитесь, что используется `LOWER()` для приведения к нижнему регистру
3. Проверьте логику определения групп в SQL

### Проблема: Медленный запрос

**Решение:**
1. Добавьте фильтр по датам в SQL запрос
2. Создайте индексы:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_user_events_external_user_id_event_date 
   ON public.user_events(external_user_id, event_date) 
   WHERE event_type = 'deposit';
   ```
3. Используйте материализованное представление для предрасчета

## Дополнительные улучшения

### Исключение выбросов через параметры

Для полноценной поддержки параметров исключения выбросов через Dashboard фильтры, нужно использовать другой подход:

1. Создайте отдельные SQL запросы для разных вариантов
2. Или используйте условную логику в SQL с параметрами Superset
3. Или создайте отдельные Dataset для каждого варианта

### Группировка по периодам

Для анализа трендов можно добавить группировку по дням/неделям/месяцам:

```sql
-- В group_comparison добавьте:
DATE_TRUNC('day', event_date) as period_date,

-- И в GROUP BY:
GROUP BY test_group, DATE_TRUNC('day', event_date)
```

Затем в Chart используйте `period_date` как X-axis для Line Chart.

