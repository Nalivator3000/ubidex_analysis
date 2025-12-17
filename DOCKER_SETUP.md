# Docker Setup для Ubidex Analysis

Этот проект упакован в Docker контейнеры для удобного развертывания локально и на сервере.

## Структура

- **Superset** - веб-интерфейс для визуализации данных
- **PostgreSQL** - база данных для метаданных Superset
- **Redis** - кеширование для Superset
- **Analysis** - контейнер со скриптами анализа

## Быстрый старт

### 1. Подготовка базы данных

Скопируйте базу данных `events.db` в папку `./data/`:

```bash
# Windows
mkdir data
copy C:\Users\Nalivator3000\superset-data-import\events.db data\events.db

# Linux/Mac
mkdir -p data
cp /path/to/events.db data/events.db
```

### 2. Запуск всех сервисов

```bash
docker-compose up -d
```

### 3. Доступ к Superset

Откройте браузер: http://localhost:8088

- **Логин**: admin
- **Пароль**: admin

### 4. Запуск скриптов анализа

```bash
# Войти в контейнер
docker exec -it ubidex_analysis bash

# Запустить скрипт
python scripts/calculate_bid_coefficients.py
```

Или запустить напрямую:

```bash
docker exec -it ubidex_analysis python scripts/calculate_bid_coefficients.py
```

## Структура директорий

```
.
├── data/              # База данных SQLite (events.db)
├── output/            # Результаты анализа (CSV файлы)
├── 07_scripts/        # Скрипты анализа
├── docker-compose.yml # Конфигурация Docker Compose
├── Dockerfile         # Образ для приложения анализа
└── superset_config.py # Конфигурация Superset
```

## Настройка для продакшена

### 1. Изменить секретный ключ

В `docker-compose.yml` измените:
```yaml
SUPERSET_SECRET_KEY: 'your-secret-key-change-in-production'
```

Или используйте `.env` файл:
```bash
cp .env.example .env
# Отредактируйте .env и измените SUPERSET_SECRET_KEY
```

### 2. Изменить пароль администратора

В `docker-compose.yml` измените команду создания админа:
```yaml
superset fab create-admin --username admin --password YOUR_SECURE_PASSWORD
```

### 3. Настроить порты

Измените маппинг портов в `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8088"
```

## Подключение базы данных в Superset

После первого запуска база данных `Ubidex Events DB` будет автоматически добавлена в Superset.

Если нужно добавить вручную:

1. Зайдите в Superset → Settings → Database Connections
2. Нажмите "+ Database"
3. Выберите "SQLite"
4. Введите URI: `sqlite:////data/events.db`
5. Нажмите "Test Connection" и "Save"

## Полезные команды

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только Superset
docker-compose logs -f superset

# Только анализ
docker-compose logs -f analysis
```

### Остановка сервисов
```bash
docker-compose down
```

### Остановка с удалением данных
```bash
docker-compose down -v
```

### Пересборка образов
```bash
docker-compose build --no-cache
```

### Выполнение скрипта анализа
```bash
docker exec -it ubidex_analysis python scripts/analyze_period.py "Period_Name" "2025-11-18" "2025-11-23"
```

## Развертывание на сервере

### 1. Скопируйте проект на сервер

```bash
scp -r . user@server:/path/to/ubidex_analysis/
```

### 2. На сервере

```bash
cd /path/to/ubidex_analysis
docker-compose up -d
```

### 3. Настройте reverse proxy (nginx)

Пример конфигурации nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Решение проблем

### Superset не запускается

Проверьте логи:
```bash
docker-compose logs superset
```

Убедитесь, что PostgreSQL и Redis запущены:
```bash
docker-compose ps
```

### База данных не найдена

Проверьте, что файл `events.db` находится в `./data/`:
```bash
ls -lh data/events.db
```

### Проблемы с правами доступа

На Linux/Mac может потребоваться изменить права:
```bash
chmod -R 755 data/
chmod -R 755 output/
```

## Обновление

```bash
# Остановить контейнеры
docker-compose down

# Обновить код
git pull

# Пересобрать и запустить
docker-compose build --no-cache
docker-compose up -d
```

