#!/usr/bin/env python3
"""
Создание Chart и Dashboard для анализа сплит-теста в Superset
"""
import requests
import json
import sys
import io
import os

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SUPERSET_URL = os.environ.get("SUPERSET_URL", "https://superset-railway-production-38aa.up.railway.app")
SUPERSET_USERNAME = os.environ.get("SUPERSET_USERNAME", "admin")
SUPERSET_PASSWORD = os.environ.get("SUPERSET_PASSWORD", "admin12345")

print("=" * 80)
print("СОЗДАНИЕ CHART ДЛЯ АНАЛИЗА СПЛИТ-ТЕСТА")
print("=" * 80)
print()

# Step 1: Login
print("1. Авторизация в Superset...")
session = requests.Session()

login_url = f"{SUPERSET_URL}/api/v1/security/login"
login_payload = {
    "username": SUPERSET_USERNAME,
    "password": SUPERSET_PASSWORD,
    "provider": "db",
    "refresh": True
}

try:
    login_response = session.post(login_url, json=login_payload, timeout=30)
    login_response.raise_for_status()
    access_token = login_response.json()["access_token"]
    
    # Get CSRF token
    csrf_url = f"{SUPERSET_URL}/api/v1/security/csrf_token/"
    csrf_response = session.get(csrf_url, headers={
        "Authorization": f"Bearer {access_token}",
        "Referer": SUPERSET_URL
    }, timeout=30)
    csrf_data = csrf_response.json()
    csrf_token = csrf_data.get("result", {}).get("csrf_token") if isinstance(csrf_data.get("result"), dict) else csrf_data.get("result") or csrf_data.get("csrf_token")
    
    print("   ✓ Авторизация успешна")
except Exception as e:
    print(f"   ✗ Ошибка авторизации: {e}")
    sys.exit(1)

# Headers
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Referer": SUPERSET_URL,
    "X-CSRFToken": csrf_token
}

# Step 2: Get database ID
print("2. Поиск базы данных...")
db_url = f"{SUPERSET_URL}/api/v1/database/"
try:
    db_response = session.get(db_url, headers=headers, timeout=30)
    db_response.raise_for_status()
    databases = db_response.json()["result"]
    
    db_id = None
    for db in databases:
        if db.get("database_name") == "Ubidex Events DB":
            db_id = db["id"]
            break
    
    if not db_id:
        print("   ✗ База данных 'Ubidex Events DB' не найдена")
        sys.exit(1)
    
    print(f"   ✓ База данных найдена (ID: {db_id})")
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    sys.exit(1)

# Step 3: Read SQL query
print("3. Загрузка SQL-запроса...")
sql_file = "superset_queries/split_test_analysis.sql"
if not os.path.exists(sql_file):
    print(f"   ✗ Файл не найден: {sql_file}")
    sys.exit(1)

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_query = f.read()

print("   ✓ SQL-запрос загружен")

# Step 4: Create dataset
print("4. Создание Dataset...")
dataset_name = "Split Test Analysis"

# Check if dataset exists
datasets_url = f"{SUPERSET_URL}/api/v1/dataset/"
datasets_response = session.get(datasets_url, headers=headers, timeout=30, 
                               params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": dataset_name}]})})

dataset_id = None
if datasets_response.status_code == 200:
    existing_datasets = datasets_response.json().get("result", [])
    if existing_datasets:
        dataset_id = existing_datasets[0]["id"]
        print(f"   ✓ Dataset уже существует (ID: {dataset_id})")
    else:
        # Create new dataset
        dataset_payload = {
            "database_id": db_id,
            "schema": "public",
            "table_name": dataset_name,
            "sql": sql_query,
            "is_virtual": True,
            "columns": [
                {"column_name": "Группа", "type": "VARCHAR"},
                {"column_name": "Уникальных пользователей", "type": "INTEGER"},
                {"column_name": "Всего депозитов", "type": "INTEGER"},
                {"column_name": "Сумма депозитов (USD)", "type": "NUMERIC"},
                {"column_name": "Средний депозит (USD)", "type": "NUMERIC"},
                {"column_name": "Среднее депозитов на пользователя", "type": "NUMERIC"},
                {"column_name": "Средняя сумма на пользователя (USD)", "type": "NUMERIC"},
                {"column_name": "Первая дата", "type": "TIMESTAMP"},
                {"column_name": "Последняя дата", "type": "TIMESTAMP"},
            ],
        }
        
        create_dataset_response = session.post(datasets_url, headers=headers, json=dataset_payload, timeout=60)
        if create_dataset_response.status_code == 201:
            dataset_id = create_dataset_response.json()["result"]["id"]
            print(f"   ✓ Dataset создан (ID: {dataset_id})")
        else:
            print(f"   ✗ Ошибка создания dataset: {create_dataset_response.status_code}")
            print(create_dataset_response.text)
            sys.exit(1)

# Step 5: Create Chart
print("5. Создание Chart...")
chart_name = "Split Test Comparison"

# Check if chart exists
charts_url = f"{SUPERSET_URL}/api/v1/chart/"
charts_response = session.get(charts_url, headers=headers, timeout=30,
                             params={"q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": chart_name}]})})

chart_id = None
if charts_response.status_code == 200:
    existing_charts = charts_response.json().get("result", [])
    if existing_charts:
        chart_id = existing_charts[0]["id"]
        print(f"   ✓ Chart уже существует (ID: {chart_id})")
    else:
        # Create new chart
        chart_payload = {
            "slice_name": chart_name,
            "viz_type": "table",
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps({
                "datasource": f"{dataset_id}__table",
                "viz_type": "table",
                "metrics": [
                    {"label": "Уникальных пользователей", "expressionType": "SQL", "sqlExpression": "SUM(\"Уникальных пользователей\")"},
                    {"label": "Всего депозитов", "expressionType": "SQL", "sqlExpression": "SUM(\"Всего депозитов\")"},
                    {"label": "Сумма депозитов (USD)", "expressionType": "SQL", "sqlExpression": "SUM(\"Сумма депозитов (USD)\")"},
                ],
                "groupby": ["Группа"],
                "row_limit": 100,
                "order_desc": False,
            }),
        }
        
        create_chart_response = session.post(charts_url, headers=headers, json=chart_payload, timeout=30)
        if create_chart_response.status_code == 201:
            chart_id = create_chart_response.json()["result"]["id"]
            print(f"   ✓ Chart создан (ID: {chart_id})")
        else:
            print(f"   ✗ Ошибка создания chart: {create_chart_response.status_code}")
            print(create_chart_response.text)
            sys.exit(1)

print()
print("=" * 80)
print("АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ЧЕРЕЗ API НЕ ПОДДЕРЖИВАЕТСЯ")
print("=" * 80)
print()
print("Используйте ручное создание через Superset UI:")
print()
print("ШАГ 1: Создание Dataset")
print("1. Откройте Superset → SQL Lab")
print(f"2. Скопируйте SQL из файла: superset_queries/split_test_analysis.sql")
print("3. Вставьте SQL в SQL Lab и выполните запрос")
print("4. Нажмите 'Save' → 'Save as dataset'")
print(f"5. Название: {dataset_name}")
print("6. Нажмите 'Save'")
print()
print("ШАГ 2: Создание Chart")
print("1. Откройте Superset → Charts → + Chart")
print(f"2. Выберите Dataset: {dataset_name}")
print("3. Chart Type: Table")
print("4. Настройте метрики (см. SPLIT_TEST_SETUP.md)")
print(f"5. Название: {chart_name}")
print("6. Нажмите 'Save'")
print()
print("ШАГ 3: Создание Dashboard")
print("1. Откройте Superset → Dashboards → + Dashboard")
print("2. Название: Split Test Analysis")
print(f"3. Добавьте Chart: {chart_name}")
print("4. Добавьте фильтры (см. SPLIT_TEST_SETUP.md)")
print()
print("Подробная инструкция: superset_queries/SPLIT_TEST_SETUP.md")

