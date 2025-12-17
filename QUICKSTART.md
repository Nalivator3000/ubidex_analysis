# Быстрый старт Docker

## Шаг 1: Подготовка базы данных

### Вариант A: Миграция из SQLite (если есть существующая база)

Скопируйте базу данных в папку `data/` для миграции:

```bash
# Windows PowerShell
mkdir data
copy C:\Users\Nalivator3000\superset-data-import\events.db data\events.db

# Linux/Mac
mkdir -p data
cp /path/to/events.db data/events.db
```

### Вариант B: Использование PostgreSQL напрямую

Если база данных уже в PostgreSQL, просто запустите контейнеры.

## Шаг 2: Запуск

```bash
docker-compose up -d
```

Подождите 1-2 минуты, пока PostgreSQL и Superset инициализируются.

### Если мигрируете из SQLite:

```bash
# После запуска контейнеров, выполните миграцию
docker exec -it ubidex_analysis python scripts/migrate_to_postgresql.py
```

Это займет 30-60 минут для базы ~7GB. См. [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) для подробностей.

## Шаг 3: Доступ

Откройте браузер: **http://localhost:8088**

- **Логин**: `admin`
- **Пароль**: `admin`

## Шаг 4: Запуск скриптов анализа

```bash
# Войти в контейнер
docker exec -it ubidex_analysis bash

# Или запустить напрямую
docker exec -it ubidex_analysis python scripts/calculate_bid_coefficients.py
```

## Остановка

```bash
docker-compose down
```

## Просмотр логов

```bash
docker-compose logs -f superset
```

Подробная документация: см. [DOCKER_SETUP.md](DOCKER_SETUP.md)

