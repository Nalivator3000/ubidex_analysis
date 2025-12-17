# Развертывание на сервере

## Подготовка

### 1. Требования на сервере

- Docker (версия 20.10+)
- Docker Compose (версия 2.0+)
- Минимум 8GB RAM (рекомендуется 16GB)
- Минимум 20GB свободного места на диске
- Порты: 8088 (Superset), 5432 (PostgreSQL, опционально)

### 2. Копирование проекта

```bash
# На локальной машине - создать архив
tar -czf ubidex_analysis.tar.gz \
  --exclude='data/*.db' \
  --exclude='output/*' \
  --exclude='.git' \
  --exclude='__pycache__' \
  .

# Или использовать git
git clone <repository-url>
cd ubidex_analysis
```

### 3. Копирование базы данных

```bash
# На сервере создать директорию
mkdir -p /opt/ubidex_analysis/data

# Скопировать базу данных (используйте scp, rsync или другой метод)
scp events.db user@server:/opt/ubidex_analysis/data/
```

## Развертывание

### 1. На сервере

```bash
cd /opt/ubidex_analysis

# Скопировать базу данных в data/
cp /path/to/events.db data/events.db

# Запустить контейнеры
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотреть логи
docker-compose logs -f
```

### 2. Настройка для продакшена

#### Изменить секретный ключ

Отредактируйте `docker-compose.yml`:

```yaml
environment:
  SUPERSET_SECRET_KEY: 'your-very-secure-secret-key-here'
```

Или используйте `.env` файл:

```bash
cp .env.example .env
# Отредактируйте .env и установите SUPERSET_SECRET_KEY
```

#### Изменить пароль администратора

В `docker-compose.yml` измените команду:

```yaml
command: >
  sh -c "
  superset db upgrade &&
  superset fab create-admin --username admin --password YOUR_SECURE_PASSWORD --email admin@ubidex.com &&
  ...
  "
```

#### Настроить порты

Если нужно изменить порт Superset:

```yaml
ports:
  - "YOUR_PORT:8088"
```

### 3. Настройка Nginx (reverse proxy)

Создайте конфигурацию `/etc/nginx/sites-available/ubidex`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS (опционально)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/ubidex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Настройка SSL (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 5. Автозапуск при перезагрузке

Docker Compose автоматически запускает контейнеры при перезагрузке, если они были запущены с флагом `-d`.

Для гарантии создайте systemd service:

```bash
sudo nano /etc/systemd/system/ubidex.service
```

Содержимое:

```ini
[Unit]
Description=Ubidex Analysis Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ubidex_analysis
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активируйте:

```bash
sudo systemctl enable ubidex
sudo systemctl start ubidex
```

## Мониторинг

### Проверка статуса

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Логи
docker-compose logs -f superset
docker-compose logs -f analysis
```

### Резервное копирование

#### База данных PostgreSQL (метаданные Superset)

```bash
# Создать бэкап
docker exec ubidex_postgres pg_dump -U superset superset > backup_$(date +%Y%m%d).sql

# Восстановить
docker exec -i ubidex_postgres psql -U superset superset < backup_20250101.sql
```

#### База данных SQLite (events.db)

```bash
# Просто скопировать файл
cp data/events.db data/events.db.backup_$(date +%Y%m%d)
```

#### Volumes Docker

```bash
# Бэкап volumes
docker run --rm -v ubidex_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Обновление

```bash
cd /opt/ubidex_analysis

# Остановить контейнеры
docker-compose down

# Обновить код (если используется git)
git pull

# Пересобрать образы
docker-compose build --no-cache

# Запустить
docker-compose up -d
```

## Решение проблем

### Контейнеры не запускаются

```bash
# Проверить логи
docker-compose logs

# Проверить использование диска
df -h

# Проверить использование памяти
free -h
```

### Superset не доступен

```bash
# Проверить, что контейнер запущен
docker-compose ps

# Проверить логи Superset
docker-compose logs superset

# Проверить подключение к PostgreSQL
docker exec ubidex_postgres psql -U superset -d superset -c "SELECT 1;"
```

### Проблемы с базой данных

```bash
# Проверить права доступа
ls -la data/events.db

# Проверить размер файла
du -h data/events.db

# Проверить целостность SQLite
docker exec ubidex_analysis sqlite3 /data/events.db "PRAGMA integrity_check;"
```

## Безопасность

### Рекомендации

1. **Измените пароли по умолчанию** - особенно для администратора Superset
2. **Используйте HTTPS** - настройте SSL сертификат
3. **Ограничьте доступ** - используйте firewall для ограничения доступа к портам
4. **Регулярные обновления** - обновляйте Docker образы и систему
5. **Мониторинг** - настройте логирование и мониторинг
6. **Резервное копирование** - регулярно создавайте бэкапы

### Firewall

```bash
# Разрешить только необходимые порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Производительность

### Оптимизация для больших данных

В `docker-compose.yml` можно добавить ограничения ресурсов:

```yaml
services:
  superset:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Настройка PostgreSQL

Создайте файл `postgresql.conf` для оптимизации:

```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
```

И смонтируйте его в `docker-compose.yml`:

```yaml
volumes:
  - ./postgresql.conf:/etc/postgresql/postgresql.conf
```

