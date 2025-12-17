#!/usr/bin/env python3
"""
Создание Chart и Dashboard в Superset через API
"""
import requests
import json
import sys
import io
import time

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://superset:8088")  # Use service name in Docker
# For external access, use: http://localhost:8088
SUPERSET_USERNAME = "admin"
SUPERSET_PASSWORD = "admin"

print("=" * 80)
print("СОЗДАНИЕ CHART И DASHBOARD В SUPERSET")
print("=" * 80)
print()

# Step 1: Login and get access token + CSRF token
print("1. Авторизация в Superset...")
print()

# Create session to maintain cookies (for CSRF token)
session = requests.Session()

login_url = f"{SUPERSET_URL}/api/v1/security/login"
login_payload = {
    "username": SUPERSET_USERNAME,
    "password": SUPERSET_PASSWORD,
    "provider": "db",
    "refresh": True
}

try:
    login_response = session.post(login_url, json=login_payload, timeout=10)
    login_response.raise_for_status()
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]
    
    # Get CSRF token from cookies or headers
    csrf_token = session.cookies.get('csrf_access_token') or session.cookies.get('csrf')
    
    print("   ✓ Авторизация успешна")
    if csrf_token:
        print(f"   ✓ CSRF токен получен")
except Exception as e:
    print(f"   ✗ Ошибка авторизации: {e}")
    print()
    print("   Убедитесь, что Superset запущен: http://localhost:8088")
    sys.exit(1)

# Headers for API requests
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Add CSRF token if available
if csrf_token:
    headers["X-CSRFToken"] = csrf_token
    headers["Referer"] = SUPERSET_URL

# Step 2: Get database ID
print("2. Поиск базы данных 'Ubidex Events DB'...")
print()

db_url = f"{SUPERSET_URL}/api/v1/database/"
try:
    db_response = requests.get(db_url, headers=headers, timeout=10)
    db_response.raise_for_status()
    databases = db_response.json()["result"]
    
    db_id = None
    for db in databases:
        if db.get("database_name") == "Ubidex Events DB":
            db_id = db["id"]
            break
    
    if not db_id:
        print("   ✗ База данных 'Ubidex Events DB' не найдена")
        print("   Доступные базы данных:")
        for db in databases:
            print(f"     - {db.get('database_name')} (ID: {db.get('id')})")
        sys.exit(1)
    
    print(f"   ✓ База данных найдена (ID: {db_id})")
except Exception as e:
    print(f"   ✗ Ошибка при поиске базы данных: {e}")
    sys.exit(1)

# Step 3: Read SQL query
print("3. Загрузка SQL-запроса...")
print()

# SQL query embedded directly (simpler approach)
sql_query = """
WITH 
period_spend AS (
    SELECT 
        publisher_id,
        publisher_name,
        format,
        month,
        deposits_reported,
        spend,
        current_cpa
    FROM publisher_spend
    WHERE publisher_id != 0
      AND spend >= 50
),
plr_nor AS (
    SELECT 
        format,
        SUM(spend) as total_spend,
        SUM(deposits_reported) as total_deposits,
        CASE 
            WHEN SUM(deposits_reported) > 0 
            THEN SUM(spend) / SUM(deposits_reported) 
            ELSE 0 
        END as avg_cpa
    FROM period_spend
    WHERE UPPER(publisher_name) LIKE '%PLR%' 
       OR UPPER(publisher_name) LIKE '%NOR%'
    GROUP BY format
),
target_cpa_by_format AS (
    SELECT 
        format,
        CASE 
            WHEN avg_cpa > 0 THEN avg_cpa * 0.7
            ELSE NULL
        END as target_cpa
    FROM plr_nor
    WHERE avg_cpa > 0
    
    UNION
    
    SELECT 
        ps.format,
        CASE 
            WHEN SUM(ps.deposits_reported) > 0 
            THEN (SUM(ps.spend) / SUM(ps.deposits_reported)) * 0.7
            ELSE NULL
        END as target_cpa
    FROM period_spend ps
    WHERE ps.format NOT IN (
        SELECT format FROM plr_nor WHERE avg_cpa > 0
    )
    GROUP BY ps.format
)
SELECT 
    ps.publisher_id,
    ps.publisher_name,
    ps.format,
    ps.month,
    COALESCE(tc.target_cpa, 0) as target_cpa_format,
    ps.current_cpa,
    ps.spend,
    ps.deposits_reported,
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0)
        ELSE 1.0
    END as coefficient,
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 
        THEN ((LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) - 1) * 100)
        ELSE 0
    END as change_pct,
    CASE 
        WHEN ps.current_cpa > 0 AND COALESCE(tc.target_cpa, 0) > 0 THEN
            CASE 
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 1.3 THEN 'УВЕЛИЧИТЬ ставку'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 1.1 THEN 'Увеличить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.9 THEN 'Оставить'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.7 THEN 'Снизить немного'
                WHEN LEAST(GREATEST(COALESCE(tc.target_cpa, 0) / ps.current_cpa, 0.1), 3.0) >= 0.4 THEN 'СНИЗИТЬ ставку'
                ELSE 'отключить паблишера'
            END
        ELSE 'Нет данных'
    END as recommendation
FROM period_spend ps
LEFT JOIN target_cpa_by_format tc
    ON ps.format = tc.format
ORDER BY ps.format, ps.month, coefficient DESC;
"""

print("   ✓ SQL-запрос готов")

# Step 4: Create dataset (virtual table)
print("4. Создание Dataset (виртуальная таблица)...")
print()

dataset_name = "Publisher Coefficients by Period"
dataset_payload = {
    "database_id": db_id,
    "schema": "public",
    "table_name": dataset_name,
    "sql": sql_query,
    "is_virtual": True,
    "columns": [
        {"column_name": "publisher_id", "type": "INTEGER"},
        {"column_name": "publisher_name", "type": "VARCHAR"},
        {"column_name": "format", "type": "VARCHAR"},
        {"column_name": "month", "type": "VARCHAR"},
        {"column_name": "target_cpa_format", "type": "NUMERIC"},
        {"column_name": "current_cpa", "type": "NUMERIC"},
        {"column_name": "spend", "type": "NUMERIC"},
        {"column_name": "deposits_reported", "type": "INTEGER"},
        {"column_name": "coefficient", "type": "NUMERIC"},
        {"column_name": "change_pct", "type": "NUMERIC"},
        {"column_name": "recommendation", "type": "VARCHAR"}
    ],
    "metrics": [
        {
            "metric_name": "total_spend",
            "expression": "SUM(spend)",
            "metric_type": "sum"
        },
        {
            "metric_name": "avg_coefficient",
            "expression": "AVG(coefficient)",
            "metric_type": "avg"
        },
        {
            "metric_name": "avg_cpa",
            "expression": "AVG(current_cpa)",
            "metric_type": "avg"
        }
    ]
}

try:
    # Check if dataset already exists
    datasets_url = f"{SUPERSET_URL}/api/v1/dataset/"
    datasets_response = session.get(datasets_url, headers=headers, params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": dataset_name}]})}, timeout=10)
    
    if datasets_response.status_code == 200:
        existing_datasets = datasets_response.json().get("result", [])
        if existing_datasets:
            dataset_id = existing_datasets[0]["id"]
            print(f"   ✓ Dataset уже существует (ID: {dataset_id})")
        else:
            # Create new dataset
            create_dataset_url = f"{SUPERSET_URL}/api/v1/dataset/"
            create_response = session.post(create_dataset_url, headers=headers, json=dataset_payload, timeout=30)
            create_response.raise_for_status()
            dataset_id = create_response.json()["result"]["id"]
            print(f"   ✓ Dataset создан (ID: {dataset_id})")
    else:
        print(f"   ⚠ Не удалось проверить существующие datasets, попробуем создать новый")
        create_dataset_url = f"{SUPERSET_URL}/api/v1/dataset/"
        create_response = session.post(create_dataset_url, headers=headers, json=dataset_payload, timeout=30)
        create_response.raise_for_status()
        dataset_id = create_response.json()["result"]["id"]
        print(f"   ✓ Dataset создан (ID: {dataset_id})")
except Exception as e:
    print(f"   ✗ Ошибка создания dataset: {e}")
    print(f"   Ответ сервера: {create_response.text if 'create_response' in locals() else 'N/A'}")
    print()
    print("   ВНИМАНИЕ: Создание dataset через API может не работать в вашей версии Superset.")
    print("   Попробуем альтернативный подход - создание через SQL Lab...")
    print()
    
    # Alternative: Create chart directly from SQL Lab query
    print("   Альтернативный подход: создание Chart через SQL Lab...")
    print("   (Этот метод требует ручного создания через веб-интерфейс)")
    print()
    print("   Инструкция:")
    print("   1. Откройте http://localhost:8088")
    print("   2. SQL → SQL Lab")
    print("   3. Выберите 'Ubidex Events DB'")
    print("   4. Вставьте SQL-запрос и выполните")
    print("   5. Нажмите 'Explore' → создайте Chart")
    print("   6. Сохраните Chart и добавьте в Dashboard")
    print()
    sys.exit(1)

# Step 5: Create Chart - Table
print("5. Создание Chart (Table)...")
print()

chart_name = "Коэффициенты паблишеров - Таблица"
chart_payload = {
    "datasource_id": dataset_id,
    "datasource_type": "table",
    "viz_type": "table",
    "slice_name": chart_name,
    "params": json.dumps({
        "adhoc_filters": [],
        "all_columns": [
            "publisher_name",
            "format",
            "month",
            "coefficient",
            "current_cpa",
            "target_cpa_format",
            "spend",
            "recommendation"
        ],
        "row_limit": 1000,
        "table_timestamp_format": "smart_date",
        "include_search": True,
        "page_length": 50
    })
}

try:
    chart_url = f"{SUPERSET_URL}/api/v1/chart/"
    chart_response = session.post(chart_url, headers=headers, json=chart_payload, timeout=30)
    chart_response.raise_for_status()
    chart_id = chart_response.json()["result"]["id"]
    print(f"   ✓ Chart создан (ID: {chart_id})")
except Exception as e:
    print(f"   ✗ Ошибка создания chart: {e}")
    print(f"   Ответ сервера: {chart_response.text if 'chart_response' in locals() else 'N/A'}")
    print()
    print("   Создайте chart вручную через веб-интерфейс:")
    print("   1. SQL Lab → выполните SQL-запрос")
    print("   2. Нажмите 'Explore'")
    print("   3. Выберите тип 'Table'")
    print("   4. Настройте колонки и метрики")
    print("   5. Сохраните chart")
    sys.exit(1)

# Step 6: Create Dashboard
print("6. Создание Dashboard...")
print()

dashboard_name = "Анализ паблишеров - Коэффициенты"
dashboard_payload = {
    "dashboard_title": dashboard_name,
    "slug": "publisher-coefficients-analysis",
    "published": True,
    "css": "",
    "json_metadata": json.dumps({
        "filter_scopes": {},
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "refresh_frequency": 0,
        "default_filters": json.dumps({}),
        "chart_configuration": {}
    }),
    "position_json": json.dumps({
        "CHART-SLICE-ID": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 20
        }
    }),
    "owners": [1]  # Admin user ID (usually 1)
}

try:
    dashboard_url = f"{SUPERSET_URL}/api/v1/dashboard/"
    
    # Check if dashboard already exists
    dashboards_response = session.get(dashboard_url, headers=headers, params={"q": json.dumps({"filters": [{"col": "dashboard_title", "opr": "eq", "value": dashboard_name}]})}, timeout=10)
    
    if dashboards_response.status_code == 200:
        existing_dashboards = dashboards_response.json().get("result", [])
        if existing_dashboards:
            dashboard_id = existing_dashboards[0]["id"]
            print(f"   ✓ Dashboard уже существует (ID: {dashboard_id})")
        else:
            create_dashboard_response = session.post(dashboard_url, headers=headers, json=dashboard_payload, timeout=30)
            create_dashboard_response.raise_for_status()
            dashboard_id = create_dashboard_response.json()["result"]["id"]
            print(f"   ✓ Dashboard создан (ID: {dashboard_id})")
    else:
        create_dashboard_response = session.post(dashboard_url, headers=headers, json=dashboard_payload, timeout=30)
        create_dashboard_response.raise_for_status()
        dashboard_id = create_dashboard_response.json()["result"]["id"]
        print(f"   ✓ Dashboard создан (ID: {dashboard_id})")
    
    # Add chart to dashboard
    print("7. Добавление Chart в Dashboard...")
    print()
    
    add_chart_url = f"{SUPERSET_URL}/api/v1/dashboard/{dashboard_id}/"
    get_dashboard_response = session.get(add_chart_url, headers=headers, timeout=10)
    get_dashboard_response.raise_for_status()
    dashboard_data = get_dashboard_response.json()["result"]
    
    # Update position_json to include the chart
    position_json = json.loads(dashboard_data.get("position_json", "{}"))
    position_json[f"CHART-{chart_id}"] = {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 20
    }
    
    # Update slices (charts in dashboard)
    slices = dashboard_data.get("slices", [])
    if chart_id not in [s["id"] for s in slices]:
        slices.append({"id": chart_id})
    
    update_payload = {
        "position_json": json.dumps(position_json),
        "slices": slices
    }
    
    update_response = session.put(add_chart_url, headers=headers, json=update_payload, timeout=30)
    update_response.raise_for_status()
    print(f"   ✓ Chart добавлен в Dashboard")
    
except Exception as e:
    print(f"   ✗ Ошибка создания dashboard: {e}")
    print(f"   Ответ сервера: {update_response.text if 'update_response' in locals() else create_dashboard_response.text if 'create_dashboard_response' in locals() else 'N/A'}")
    print()
    print("   Создайте dashboard вручную через веб-интерфейс:")
    print("   1. Dashboards → + Dashboard")
    print("   2. Добавьте созданный chart на dashboard")
    print("   3. Сохраните dashboard")
    sys.exit(1)

print()
print("=" * 80)
print("ГОТОВО!")
print("=" * 80)
print()
print(f"Dashboard создан: {dashboard_name}")
print(f"URL: {SUPERSET_URL}/superset/dashboard/{dashboard_id}/")
print()
print("Chart создан: {chart_name}")
print(f"URL: {SUPERSET_URL}/superset/explore/?slice_id={chart_id}")
print()
print("Теперь вы можете:")
print("1. Открыть Dashboard и настроить фильтры")
print("2. Добавить дополнительные charts")
print("3. Настроить layout и визуализации")
print()

