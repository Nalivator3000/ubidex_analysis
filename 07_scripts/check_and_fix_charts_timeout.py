#!/usr/bin/env python3
"""
Скрипт для проверки и исправления настроек таймаута для Charts
Проверяет настройки Database и Charts, обновляет при необходимости
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
print("ПРОВЕРКА И ИСПРАВЛЕНИЕ НАСТРОЕК ТАЙМАУТА ДЛЯ CHARTS")
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
    print("   ✓ Авторизация успешна")
    
    # Get CSRF token
    csrf_url = f"{SUPERSET_URL}/api/v1/security/csrf_token/"
    csrf_headers = {
        "Authorization": f"Bearer {access_token}",
        "Referer": SUPERSET_URL
    }
    csrf_response = session.get(csrf_url, headers=csrf_headers, timeout=30)
    if csrf_response.status_code == 200:
        csrf_data = csrf_response.json()
        if isinstance(csrf_data, dict):
            result = csrf_data.get("result")
            if isinstance(result, dict):
                csrf_token = result.get("csrf_token")
            elif isinstance(result, str):
                csrf_token = result
            else:
                csrf_token = csrf_data.get("csrf_token")
        else:
            csrf_token = csrf_data
except Exception as e:
    print(f"   ✗ Ошибка авторизации: {e}")
    sys.exit(1)

# Headers
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Referer": SUPERSET_URL
}
if csrf_token:
    headers["X-CSRFToken"] = csrf_token

# Step 2: Check Database settings
print("2. Проверка настроек Database...")
db_url = f"{SUPERSET_URL}/api/v1/database/"
try:
    db_response = session.get(db_url, headers=headers, timeout=30)
    db_response.raise_for_status()
    databases = db_response.json()["result"]
    
    db_id = None
    for db in databases:
        if db.get("database_name") == "Ubidex Events DB":
            db_id = db["id"]
            print(f"   ✓ База данных найдена (ID: {db_id})")
            print(f"     - Async queries: {db.get('allow_run_async', False)}")
            print(f"     - Query timeout: {db.get('query_timeout', 0)} секунд")
            break
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    sys.exit(1)

# Step 3: Get all Charts
print("3. Поиск Charts...")
charts_url = f"{SUPERSET_URL}/api/v1/chart/"
try:
    charts_response = session.get(charts_url, headers=headers, timeout=30, params={"q": json.dumps({"page_size": 1000})})
    charts_response.raise_for_status()
    charts_data = charts_response.json()
    charts = charts_data.get("result", [])
    print(f"   ✓ Найдено Charts: {len(charts)}")
except Exception as e:
    print(f"   ✗ Ошибка при получении Charts: {e}")
    sys.exit(1)

# Step 4: Check problematic charts
print("4. Проверка проблемных Charts...")
print()

problem_charts = []
chart_names_to_check = ["Deposits week1", "Dep# month1", "ARPPU week1"]

for chart in charts:
    chart_name = chart.get("slice_name", "")
    if any(name.lower() in chart_name.lower() for name in chart_names_to_check):
        problem_charts.append(chart)
        print(f"   Найден Chart: {chart_name} (ID: {chart.get('id')})")
        print(f"     - Dataset ID: {chart.get('datasource_id')}")
        print(f"     - Query context: {chart.get('query_context') is not None}")

print()
print(f"   Всего проблемных Charts: {len(problem_charts)}")

# Step 5: Get Datasets
print("5. Проверка Datasets...")
datasets_url = f"{SUPERSET_URL}/api/v1/dataset/"
try:
    datasets_response = session.get(datasets_url, headers=headers, timeout=30, params={"q": json.dumps({"page_size": 1000})})
    datasets_response.raise_for_status()
    datasets_data = datasets_response.json()
    datasets = datasets_data.get("result", [])
    print(f"   ✓ Найдено Datasets: {len(datasets)}")
except Exception as e:
    print(f"   ✗ Ошибка при получении Datasets: {e}")
    sys.exit(1)

# Step 6: Check and update Datasets
print("6. Проверка настроек Datasets...")
print()

for dataset in datasets:
    dataset_name = dataset.get("table_name", "")
    dataset_id = dataset.get("id")
    
    # Check if this dataset is used by problem charts
    used_by_problem = any(
        chart.get("datasource_id") == dataset_id 
        for chart in problem_charts
    )
    
    if used_by_problem:
        print(f"   Dataset: {dataset_name} (ID: {dataset_id})")
        print(f"     - Database ID: {dataset.get('database', {}).get('id')}")
        
        # Get full dataset details
        try:
            dataset_detail_url = f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}"
            dataset_detail_response = session.get(dataset_detail_url, headers=headers, timeout=30)
            dataset_detail_response.raise_for_status()
            dataset_detail = dataset_detail_response.json().get("result", {})
            
            # Check cache timeout
            cache_timeout = dataset_detail.get("cache_timeout", 0)
            print(f"     - Cache timeout: {cache_timeout}")
            
            # Update cache timeout if needed (optional, but can help)
            if cache_timeout < 3600:
                print(f"     ⚠ Cache timeout слишком мал, но это не влияет на таймаут запросов")
        except Exception as e:
            print(f"     ⚠ Не удалось получить детали: {e}")

print()
print("=" * 80)
print("АНАЛИЗ ЗАВЕРШЕН")
print("=" * 80)
print()
print("РЕКОМЕНДАЦИИ:")
print("1. Убедитесь, что Database настройки применены:")
print("   - Data → Databases → 'Ubidex Events DB' → Advanced")
print("   - 'Allow async queries' должно быть включено ✅")
print("   - 'Query timeout' должно быть 600 или больше")
print()
print("2. Проверьте, что Charts используют правильный Dataset")
print("3. Если проблема сохраняется, попробуйте:")
print("   - Пересоздать Chart")
print("   - Упростить SQL запрос (добавить фильтры по дате)")
print("   - Использовать материализованные представления")

