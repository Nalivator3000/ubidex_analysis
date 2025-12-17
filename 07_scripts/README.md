# Скрипты для анализа

## Импорт данных:
- `import_to_sqlite.py` - импорт CSV в SQLite

## Анализ периодов:
- `analyze_period.py` - универсальный скрипт для анализа любого периода
- `analyze_all_oct_reactivations.py` - октябрь
- `analyze_all_nov_reactivations.py` - ноябрь
- `analyze_control_optimized.py` - оптимизированный анализ контроля

## Сравнение:
- `create_full_comparison_with_percentages.py` - создание сравнительной таблицы
- `analyze_segment_changes.py` - анализ изменений по сегментам

## Паблишеры:
- `analyze_publishers_performance.py` - анализ по реактивациям
- `analyze_publishers_by_deposit_cost.py` - анализ FTD/RD
- `analyze_publishers_full_months.py` - анализ полных месяцев (Oct vs Nov)
- `integrate_spend_with_ftd_rd.py` - интеграция данных по расходам с FTD/RD
- `analyze_publishers_by_format.py` - анализ паблишеров отдельно по каждому формату
- `calculate_bid_coefficients.py` - расчет коэффициентов для изменения ставок

## Использование:

### Анализ периода:
```bash
python analyze_period.py "Period_Name" "2025-08-18" "2025-08-23"
```

### Анализ паблишеров за полные месяцы:
```bash
python analyze_publishers_full_months.py
```

### Интеграция spend данных:
```bash
python integrate_spend_with_ftd_rd.py
```

## Последние добавления:

### analyze_publishers_full_months.py
Анализирует FTD/RD статистику по всем паблишерам за полный октябрь и ноябрь.
Выдает рекомендации на основе изменения объемов и RD rate.

### integrate_spend_with_ftd_rd.py
Интегрирует данные по расходам из CSV файлов с FTD/RD статистикой из базы.
Рассчитывает CPA для FTD и RD отдельно, дает рекомендации по эффективности.

Выходные файлы:
- `publishers_nov_spend_ftd_rd.csv`
- `publishers_oct_spend_ftd_rd.csv`
- `publishers_oct_vs_nov_spend_comparison.csv`
- `publishers_spend_based_recommendations.csv`

### analyze_publishers_by_format.py
Анализирует паблишеров отдельно внутри каждого формата (POP, PUSH, VIDEO, BANNER, NATIVE).
Сравнивает эффективность паблишеров с средними показателями их формата.

Использование:
```bash
python analyze_publishers_by_format.py
```

Выходные файлы:
- `publishers_by_format_with_spend.csv`
- `publishers_recommendations_by_format.csv`

### calculate_bid_coefficients.py (НОВЫЙ!)
Рассчитывает коэффициенты для изменения ставок на основе целевой CPA по каждому формату.

Методология:
1. Находит PLR/NOR кампании внутри каждого формата
2. Вычисляет среднюю CPA для этих кампаний
3. Отнимает 30% для получения целевой CPA
4. Рассчитывает коэффициент = Целевая CPA / Текущая CPA

Использование:
```bash
python calculate_bid_coefficients.py
```

Выходные файлы:
- `publishers_bid_coefficients.csv`

Пример применения:
- Текущая ставка: $1.00
- Коэффициент: 1.50 (паблишер эффективнее целевого)
- Новая ставка: $1.00 × 1.50 = $1.50 (увеличить на 50%)

Рекомендации:
- Коэф > 1.3: УВЕЛИЧИТЬ ставку на 30%+
- Коэф 1.1-1.3: Увеличить на 10-30%
- Коэф 0.9-1.1: Оставить без изменений
- Коэф 0.7-0.9: Снизить на 10-30%
- Коэф < 0.7: СНИЗИТЬ ставку на 30%+
