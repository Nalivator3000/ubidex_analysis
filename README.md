# Ubidex Analysis

Система анализа эффективности рекламных кампаний и паблишеров для гемблинг-платформы.

## Описание

Проект содержит скрипты для анализа:
- Реактивации пользователей по временным сегментам (0-7, 7-14, 14-30, 30-90, 90+ дней)
- Эффективности паблишеров по метрикам FTD (First Time Deposit) и RD (Repeat Deposit)
- CPA (Cost Per Acquisition) по форматам рекламы
- Расчета коэффициентов для оптимизации ставок

## Структура проекта

```
superset-data-import/
├── 01_raw_data/              # Исходные данные (events.db)
├── 02_control_periods/       # Контрольные периоды (авг, сен, окт)
├── 03_campaign_period/       # Период кампании (ноябрь)
├── 04_comparison_analysis/   # Сравнительный анализ
├── 05_publisher_analysis/    # Анализ паблишеров
├── 06_kadam_analysis/        # Анализ Kadam
├── 07_scripts/               # Скрипты
└── 08_reports/               # Итоговые отчеты
```

## Основные скрипты

### Импорт и подготовка данных
- `import_to_sqlite.py` - импорт CSV данных в SQLite

### Анализ периодов
- `analyze_period.py` - универсальный анализ любого периода
- `analyze_all_oct_reactivations.py` - анализ октября
- `analyze_all_nov_reactivations.py` - анализ ноября
- `create_full_comparison_with_percentages.py` - сравнение периодов
- `analyze_segment_changes.py` - анализ изменений по сегментам

### Анализ паблишеров
- `analyze_publishers_performance.py` - анализ по реактивациям
- `analyze_publishers_by_deposit_cost.py` - анализ FTD/RD
- `analyze_publishers_full_months.py` - полный анализ месяцев
- `integrate_spend_with_ftd_rd.py` - интеграция данных расходов
- `analyze_publishers_by_format.py` - анализ по форматам (POP, PUSH, VIDEO, BANNER, NATIVE)
- **`calculate_bid_coefficients.py`** - расчет коэффициентов для изменения ставок

## Быстрый старт

### Установка зависимостей
```bash
pip install pandas sqlite3
```

### Импорт данных
```bash
python 07_scripts/import_to_sqlite.py
```

### Анализ периода
```bash
python 07_scripts/analyze_period.py "Period_Name" "2025-11-18" "2025-11-23"
```

### Расчет коэффициентов ставок
```bash
python 07_scripts/calculate_bid_coefficients.py
```

## Методология расчета коэффициентов ставок

1. **Определение формата** - каждый паблишер классифицируется по типу рекламы (POP, PUSH, VIDEO, BANNER, NATIVE)

2. **Целевая CPA** - для каждого формата:
   - Находим PLR/NOR кампании
   - Вычисляем среднюю CPA
   - Отнимаем 30% для получения целевого значения

3. **Коэффициент** = Целевая CPA / Текущая CPA

4. **Применение**:
   - Новая ставка = Текущая ставка × Коэффициент

### Интерпретация коэффициентов:
- **> 1.3**: УВЕЛИЧИТЬ ставку на 30%+
- **1.1-1.3**: Увеличить на 10-30%
- **0.9-1.1**: Оставить без изменений
- **0.7-0.9**: Снизить на 10-30%
- **< 0.7**: СНИЗИТЬ ставку на 30%+

## Форматы рекламы

### Эффективность по CPA (ноябрь 2025):
1. **BANNER**: $0.007 (самый эффективный)
2. **PUSH**: $0.023
3. **VIDEO**: $0.075
4. **NATIVE**: $0.137
5. **POP**: $0.140 (самый дорогой)

## Ключевые метрики

- **FTD** - First Time Deposit (первый депозит пользователя)
- **RD** - Repeat Deposit (повторный депозит)
- **CPA** - Cost Per Acquisition (стоимость привлечения)
- **RD Rate** - процент повторных депозитов (~97.5%)

## База данных

Основная БД: `events.db` (SQLite)
- Размер: ~6.9 GB
- Записей: ~21.5M
- Период: март - декабрь 2025
- Таблица: `user_events` (external_user_id, event_type, event_date, publisher_id)

## Требования

- Python 3.8+
- pandas
- sqlite3

## Автор

Проект для анализа эффективности рекламных кампаний Ubidex

## Лицензия

Private
