# Финальное решение проблемы таймаута 60 секунд

## Проблема

Charts на Dashboard таймаутятся через 60 секунд, несмотря на настройки Database.

## Что было сделано

1. ✅ **Database настройки обновлены через API:**
   - `allow_run_async: True` - включено
   - `extra` поле обновлено с таймаутом

2. ✅ **Конфигурация Superset обновлена:**
   - `SQLLAB_TIMEOUT = 600` - для SQL Lab
   - `SQLLAB_ASYNC_TIME_LIMIT_SEC = 600` - для асинхронных запросов
   - `SUPERSET_WEBSERVER_TIMEOUT = 600` - **КРИТИЧЕСКИ ВАЖНО для Dashboard/Charts**

## ⚠️ ВАЖНО: Нужен перезапуск Superset!

После обновления `superset_config.py` **обязательно перезапустите Superset**:

1. **Railway Dashboard** → ваш проект → сервис Superset
2. Нажмите **⋮** (три точки) → **"Restart"** или **"Redeploy"**
3. Дождитесь перезапуска (1-2 минуты)

## Почему проблема может сохраняться

### Причина 1: Superset не перезапущен

`SUPERSET_WEBSERVER_TIMEOUT` применяется только после перезапуска Superset.

**Решение:** Перезапустите Superset на Railway.

### Причина 2: Charts используют синхронные запросы

Несмотря на `allow_run_async: True` в Database, Charts могут использовать синхронные запросы.

**Решение:** 
- Откройте каждый Chart отдельно
- В настройках Chart найдите опцию "Async query" или "Background query"
- Включите её, если доступно

### Причина 3: Таймаут веб-сервера

Даже с асинхронными запросами, веб-сервер Superset может таймаутить HTTP запросы через 60 секунд.

**Решение:** 
- `SUPERSET_WEBSERVER_TIMEOUT = 600` уже добавлен в `superset_config.py`
- **Нужен перезапуск Superset!**

## Проверка после перезапуска

1. **Проверьте логи Railway:**
   - Должна быть строка с `SUPERSET_WEBSERVER_TIMEOUT = 600`

2. **Проверьте Database настройки:**
   - Data → Databases → "Ubidex Events DB"
   - Advanced → "Allow async queries" должно быть ✅

3. **Проверьте Charts:**
   - Откройте Dashboard
   - Charts должны работать дольше 60 секунд

## Альтернативные решения

Если проблема все еще сохраняется после перезапуска:

### Решение 1: Упростить SQL запросы

Добавьте фильтры по дате в SQL запросы Charts:
- Ограничьте диапазон дат
- Используйте агрегацию вместо детальных данных

### Решение 2: Использовать материализованные представления

Создайте материализованные представления для сложных запросов:
```sql
CREATE MATERIALIZED VIEW chart_data_mv AS
-- ваш SQL запрос
;

CREATE INDEX idx_chart_data_date ON chart_data_mv(date_column);
```

Затем используйте материализованное представление в Chart вместо исходного запроса.

### Решение 3: Разделить Dashboard на несколько

Вместо одного Dashboard с тяжелыми Charts, создайте несколько Dashboard:
- Dashboard 1: Быстрые Charts (реальное время)
- Dashboard 2: Медленные Charts (исторические данные)

## Текущий статус

- ✅ Database: `allow_run_async: True`
- ✅ Config: `SUPERSET_WEBSERVER_TIMEOUT = 600`
- ⚠️ **Требуется перезапуск Superset на Railway**

## Следующие шаги

1. **Перезапустите Superset на Railway** (обязательно!)
2. Дождитесь полного запуска (1-2 минуты)
3. Проверьте Charts на Dashboard
4. Если проблема сохраняется - упростите SQL запросы

