# Railway Environment Variables

Этот файл содержит шаблон переменных окружения для Railway.
**НЕ КОММИТЬТЕ РЕАЛЬНЫЕ ПАРОЛИ В GIT!**

## PostgreSQL Database (Railway)

```
DATABASE_URL="${{Postgres.DATABASE_URL}}"
POSTGRES_DB="railway"
POSTGRES_HOST="postgres.railway.internal"
POSTGRES_PASSWORD="your_postgres_password"
POSTGRES_PORT="5432"
POSTGRES_USER="postgres"
```

## Superset Configuration

```
SUPERSET_SECRET_KEY="your-secret-key-change-in-production"
SUPERSET_URL="https://superset-railway-production-38aa.up.railway.app"
SUPERSET_USERNAME="admin"
SUPERSET_PASSWORD="your_admin_password"
```

## Redis (Railway)

```
REDIS_HOST="redis.railway.internal"
REDIS_PORT="6379"
REDIS_PASSWORD="${{Redis.REDIS_PASSWORD}}"
```

## Superset Admin User

```
ADMIN_USERNAME="admin"
ADMIN_FIRSTNAME="Admin"
ADMIN_LASTNAME="User"
ADMIN_EMAIL="admin@ubidex.com"
ADMIN_PASSWORD="your_admin_password"
```

## Использование

Эти переменные нужно установить в Railway Dashboard:
1. Railway Dashboard → ваш проект → Variables
2. Добавьте каждую переменную
3. Для паролей используйте Railway secrets или переменные из других сервисов

## Для локального запуска скриптов

Создайте файл `.env` (не коммитьте его!) с реальными значениями:

```bash
SUPERSET_URL="https://superset-railway-production-38aa.up.railway.app"
SUPERSET_USERNAME="admin"
SUPERSET_PASSWORD="your_actual_password"
```

Затем загрузите переменные:
```bash
# Windows PowerShell
Get-Content .env | ForEach-Object { $line = $_; if ($line -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }

# Linux/Mac
export $(cat .env | xargs)
```

