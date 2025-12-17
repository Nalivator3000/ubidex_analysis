# Инструкция по сборке проекта

## Предварительные требования

1. **Docker Desktop** должен быть установлен и запущен
2. Минимум **8GB RAM** свободно
3. Минимум **20GB** свободного места на диске

## Шаг 1: Запустить Docker Desktop

Убедитесь, что Docker Desktop запущен:
- Проверьте иконку Docker в системном трее
- Или откройте Docker Desktop вручную

Проверка:
```powershell
docker ps
```
Должно вернуться без ошибок.

## Шаг 2: Создать необходимые директории

```powershell
cd C:\Users\Nalivator3000\Cursor\ubidex_analysis\ubidex_analysis
if (-not (Test-Path data)) { New-Item -ItemType Directory -Path data }
if (-not (Test-Path output)) { New-Item -ItemType Directory -Path output }
```

## Шаг 3: Сборка образов

```powershell
docker-compose build
```

Это займет несколько минут при первом запуске (скачивание базовых образов).

## Шаг 4: Запуск контейнеров

```powershell
docker-compose up -d
```

Это запустит:
- PostgreSQL (база данных)
- Redis (кеширование)
- Superset (веб-интерфейс)
- Analysis (контейнер со скриптами)

## Шаг 5: Проверка статуса

```powershell
docker-compose ps
```

Все сервисы должны быть в статусе "Up" или "healthy".

## Шаг 6: Просмотр логов

```powershell
# Все сервисы
docker-compose logs -f

# Только Superset
docker-compose logs -f superset

# Только PostgreSQL
docker-compose logs -f postgres
```

## Шаг 7: Доступ к Superset

После запуска подождите 1-2 минуты для инициализации, затем откройте:

**http://localhost:8088**

- Логин: `admin`
- Пароль: `admin`

## Миграция данных (если есть SQLite база)

Если у вас есть существующая SQLite база данных:

1. Скопируйте базу в папку `data/`:
   ```powershell
   copy C:\Users\Nalivator3000\superset-data-import\events.db data\events.db
   ```

2. Запустите миграцию:
   ```powershell
   docker exec -it ubidex_analysis python scripts/migrate_to_postgresql.py
   ```

## Решение проблем

### Docker Desktop не запускается

1. Проверьте, что виртуализация включена в BIOS
2. Убедитесь, что Hyper-V включен (Windows)
3. Перезапустите компьютер

### Ошибка "port already in use"

Если порт 8088 занят:
1. Найдите процесс: `netstat -ano | findstr :8088`
2. Остановите процесс или измените порт в `docker-compose.yml`

### Нехватка памяти

Если контейнеры падают:
1. Увеличьте память для Docker Desktop (Settings → Resources → Memory)
2. Закройте другие приложения

### Ошибки при сборке

```powershell
# Очистить кеш и пересобрать
docker-compose build --no-cache
```

## Полезные команды

```powershell
# Остановить все контейнеры
docker-compose down

# Остановить и удалить volumes (ОСТОРОЖНО: удалит данные!)
docker-compose down -v

# Перезапустить контейнер
docker-compose restart superset

# Войти в контейнер анализа
docker exec -it ubidex_analysis bash

# Выполнить скрипт анализа
docker exec -it ubidex_analysis python scripts/calculate_bid_coefficients.py
```

## Следующие шаги

После успешной сборки:
1. См. [QUICKSTART.md](QUICKSTART.md) для быстрого старта
2. См. [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) для миграции данных
3. См. [DOCKER_SETUP.md](DOCKER_SETUP.md) для подробной настройки

