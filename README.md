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
ubidex_analysis/
├── 05_publisher_analysis/    # Анализ паблишеров
├── 07_scripts/               # Скрипты анализа
├── data/                     # База данных (PostgreSQL или SQLite)
├── output/                   # Результаты анализа
├── docker-compose.yml        # Docker конфигурация
├── Dockerfile                # Образ приложения
└── requirements.txt          # Зависимости Python
```

## Основные скрипты

### Импорт и подготовка данных
- `import_to_sqlite.py` - импорт CSV данных в SQLite (legacy)
- `migrate_to_postgresql.py` - миграция из SQLite в PostgreSQL

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

### Docker (рекомендуется)

См. [QUICKSTART.md](QUICKSTART.md) для быстрого старта с Docker.

```bash
# 1. Запустить контейнеры
docker-compose up -d

# 2. Мигрировать данные (если нужно)
docker exec -it ubidex_analysis python scripts/migrate_to_postgresql.py

# 3. Открыть Superset
# http://localhost:8088 (admin/admin)
```

### Локальный запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export DB_TYPE=postgresql  # или sqlite
export POSTGRES_HOST=localhost
export POSTGRES_USER=ubidex
export POSTGRES_PASSWORD=ubidex
export POSTGRES_DB=ubidex

# Запуск скрипта
python 07_scripts/calculate_bid_coefficients.py
```

## База данных

### PostgreSQL (рекомендуется для больших объемов)

Проект использует PostgreSQL для хранения данных. Это обеспечивает:
- Масштабируемость до 1+ TB
- Лучшую производительность на больших данных
- Параллельную обработку запросов
- Расширенные возможности (партиционирование, индексы)

**Миграция из SQLite**: см. [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

### SQLite (legacy)

Поддерживается для обратной совместимости, но не рекомендуется для больших объемов (>100GB).

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

## Требования

### Для Docker (рекомендуется):
- Docker 20.10+
- Docker Compose 2.0+
- Минимум 8GB RAM (рекомендуется 16GB для больших данных)

### Для локального запуска:
- Python 3.8+
- PostgreSQL 15+ (или SQLite для небольших объемов)
- pandas, sqlalchemy, psycopg2-binary

## Docker развертывание

Проект полностью упакован в Docker контейнеры:
- **Superset** - веб-интерфейс для визуализации данных (порт 8088)
- **PostgreSQL** - база данных для данных и метаданных Superset
- **Redis** - кеширование для Superset
- **Analysis** - контейнер со скриптами анализа

Подробная документация:
- [QUICKSTART.md](QUICKSTART.md) - быстрый старт
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - подробная инструкция
- [DEPLOY.md](DEPLOY.md) - развертывание на сервере
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - миграция на PostgreSQL

## Автор

Проект для анализа эффективности рекламных кампаний Ubidex

## Лицензия

Private
