# Руководство по миграции на PostgreSQL

## Зачем мигрировать?

- **Масштабируемость**: PostgreSQL лучше работает с большими объемами данных (1+ TB)
- **Производительность**: Лучшая оптимизация запросов и индексов
- **Параллелизм**: Поддержка множественных одновременных запросов
- **Расширяемость**: Возможность использования расширений (PostGIS, TimescaleDB и др.)

## Подготовка

### 1. Обновить Docker Compose

Убедитесь, что используете последнюю версию `docker-compose.yml` с настройками PostgreSQL.

### 2. Запустить контейнеры

```bash
docker-compose up -d
```

Подождите, пока PostgreSQL полностью запустится (проверьте логи).

## Миграция данных

### Вариант 1: Автоматическая миграция (рекомендуется)

```bash
# Войти в контейнер анализа
docker exec -it ubidex_analysis bash

# Запустить скрипт миграции
python scripts/migrate_to_postgresql.py
```

Скрипт:
- Подключится к SQLite базе
- Подключится к PostgreSQL
- Создаст таблицу и индексы
- Перенесет данные порциями по 100,000 записей
- Покажет прогресс

**Время миграции**: 
- Для 6.9 GB (~21.5M записей): примерно 30-60 минут
- Для 1 TB: несколько часов (зависит от производительности диска)

### Вариант 2: Ручная миграция через pg_dump/pg_restore

Если у вас очень большая база данных, можно использовать специализированные инструменты:

```bash
# Экспорт из SQLite в CSV
sqlite3 events.db <<EOF
.headers on
.mode csv
.output events_export.csv
SELECT * FROM user_events;
EOF

# Импорт в PostgreSQL
psql -h localhost -U ubidex -d ubidex <<EOF
\copy user_events FROM 'events_export.csv' WITH CSV HEADER;
EOF
```

## Проверка миграции

После миграции проверьте:

```bash
# Войти в контейнер PostgreSQL
docker exec -it ubidex_postgres psql -U ubidex -d ubidex

# Проверить количество записей
SELECT COUNT(*) FROM user_events;

# Проверить диапазон дат
SELECT MIN(event_date), MAX(event_date) FROM user_events;

# Проверить индексы
\di user_events*
```

## Обновление приложения

### 1. Установить переменную окружения

В `docker-compose.yml` уже установлено:
```yaml
environment:
  - DB_TYPE=postgresql
```

Или в `.env` файле:
```
DB_TYPE=postgresql
```

### 2. Перезапустить контейнеры

```bash
docker-compose restart analysis
```

### 3. Проверить подключение

```bash
docker exec -it ubidex_analysis python -c "from scripts.db_utils import test_connection; test_connection()"
```

## Обновление Superset

Superset автоматически подключится к PostgreSQL при следующем запуске благодаря `superset_init.py`.

Или вручную:

1. Зайдите в Superset → Settings → Database Connections
2. Найдите "Ubidex Events DB"
3. Проверьте URI: `postgresql://ubidex:***@postgres:5432/ubidex`
4. Нажмите "Test Connection"

## Оптимизация PostgreSQL для больших данных

### Настройки в docker-compose.yml

Уже включены базовые оптимизации:
- `shared_buffers=256MB`
- `effective_cache_size=1GB`
- `maintenance_work_mem=128MB`
- `max_wal_size=4GB`

### Дополнительные настройки для 1TB+

Создайте файл `postgresql.conf`:

```ini
# Память
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 32MB

# WAL
min_wal_size = 2GB
max_wal_size = 8GB
wal_buffers = 32MB

# Checkpoints
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min

# Запросы
max_connections = 100
random_page_cost = 1.1
effective_io_concurrency = 200

# Автовакуум (важно для больших таблиц)
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 30s
```

И смонтируйте в `docker-compose.yml`:

```yaml
volumes:
  - ./postgresql.conf:/etc/postgresql/postgresql.conf
command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

### Создание партиций (опционально)

Для очень больших таблиц можно использовать партиционирование по датам:

```sql
-- Создать партиционированную таблицу
CREATE TABLE user_events_partitioned (
    LIKE user_events INCLUDING ALL
) PARTITION BY RANGE (event_date);

-- Создать партиции по месяцам
CREATE TABLE user_events_2025_03 PARTITION OF user_events_partitioned
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
-- ... и так далее
```

## Откат на SQLite (если нужно)

Если нужно вернуться к SQLite:

1. В `docker-compose.yml` установите:
   ```yaml
   environment:
     - DB_TYPE=sqlite
     - DB_PATH=/data/events.db
   ```

2. Перезапустите:
   ```bash
   docker-compose restart analysis
   ```

## Мониторинг производительности

### Проверка размера базы данных

```sql
SELECT 
    pg_size_pretty(pg_database_size('ubidex')) as database_size,
    pg_size_pretty(pg_total_relation_size('user_events')) as table_size;
```

### Медленные запросы

Включите логирование медленных запросов в `postgresql.conf`:

```ini
log_min_duration_statement = 1000  # Логировать запросы > 1 секунды
```

### Статистика использования индексов

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'user_events'
ORDER BY idx_scan DESC;
```

## Резервное копирование

### Создание бэкапа

```bash
docker exec ubidex_postgres pg_dump -U ubidex -d ubidex -F c -f /tmp/ubidex_backup.dump
docker cp ubidex_postgres:/tmp/ubidex_backup.dump ./backups/
```

### Восстановление

```bash
docker cp ./backups/ubidex_backup.dump ubidex_postgres:/tmp/
docker exec ubidex_postgres pg_restore -U ubidex -d ubidex -c /tmp/ubidex_backup.dump
```

## Решение проблем

### Ошибка подключения

```bash
# Проверить, что PostgreSQL запущен
docker-compose ps postgres

# Проверить логи
docker-compose logs postgres

# Проверить подключение
docker exec ubidex_postgres psql -U ubidex -d ubidex -c "SELECT 1;"
```

### Нехватка места на диске

```bash
# Проверить использование
docker system df

# Очистить неиспользуемые данные
docker system prune
```

### Медленная миграция

- Увеличьте `CHUNK_SIZE` в `migrate_to_postgresql.py`
- Отключите индексы до завершения миграции
- Используйте `COPY` вместо `INSERT` для больших объемов

## Дополнительные ресурсы

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [TimescaleDB](https://www.timescale.com/) - расширение для временных рядов (опционально)

