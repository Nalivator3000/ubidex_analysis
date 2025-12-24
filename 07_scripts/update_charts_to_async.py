#!/usr/bin/env python3
"""
Обновление Charts для использования асинхронных запросов
"""
import requests
import json
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SUPERSET_URL = os.environ.get("SUPERSET_URL", "https://superset-railway-production-38aa.up.railway.app")
SUPERSET_USERNAME = os.environ.get("SUPERSET_USERNAME", "admin")
SUPERSET_PASSWORD = os.environ.get("SUPERSET_PASSWORD", "admin12345")

# Login
session = requests.Session()
login_response = session.post(f"{SUPERSET_URL}/api/v1/security/login", json={
    "username": SUPERSET_USERNAME,
    "password": SUPERSET_PASSWORD,
    "provider": "db",
    "refresh": True
}, timeout=30)
access_token = login_response.json()["access_token"]

# Get CSRF
csrf_response = session.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/", headers={
    "Authorization": f"Bearer {access_token}",
    "Referer": SUPERSET_URL
}, timeout=30)
csrf_data = csrf_response.json()
csrf_token = csrf_data.get("result", {}).get("csrf_token") if isinstance(csrf_data.get("result"), dict) else csrf_data.get("result") or csrf_data.get("csrf_token")

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Referer": SUPERSET_URL,
    "X-CSRFToken": csrf_token
}

# Get problematic charts
chart_names = ["Deposits week1", "Dep# month1", "ARPPU week1"]
charts_response = session.get(f"{SUPERSET_URL}/api/v1/chart/", headers=headers, timeout=30, 
                             params={"q": json.dumps({"page_size": 1000})})
charts = charts_response.json()["result"]

print("=" * 80)
print("ОБНОВЛЕНИЕ CHARTS ДЛЯ АСИНХРОННЫХ ЗАПРОСОВ")
print("=" * 80)
print()

updated_count = 0

for chart_name in chart_names:
    chart = next((c for c in charts if chart_name.lower() in c.get("slice_name", "").lower()), None)
    if not chart:
        print(f"Chart '{chart_name}' не найден")
        continue
    
    chart_id = chart["id"]
    print(f"Chart: {chart.get('slice_name')} (ID: {chart_id})")
    
    # Get full chart details
    chart_detail_response = session.get(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, timeout=30)
    chart_detail = chart_detail_response.json()["result"]
    
    # Prepare update - copy all fields
    update_payload = {}
    for key, value in chart_detail.items():
        if key not in ["id", "changed_on", "created_on", "changed_by", "created_by", 
                       "changed_by_fk", "created_by_fk", "owners", "dashboards"]:
            update_payload[key] = value
    
    # Update params to ensure async is used
    params = chart_detail.get("params", {})
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except:
            params = {}
    
    if not isinstance(params, dict):
        params = {}
    
    # Add async flag if not present
    if "async_query" not in params:
        params["async_query"] = True
        update_payload["params"] = json.dumps(params)
        print(f"  Добавлен async_query в params")
    
    # Try to update
    try:
        update_response = session.put(f"{SUPERSET_URL}/api/v1/chart/{chart_id}", headers=headers, json=update_payload, timeout=30)
        if update_response.status_code == 200:
            print(f"  ✓ Chart обновлен")
            updated_count += 1
        else:
            print(f"  ✗ Ошибка обновления: {update_response.status_code}")
            print(f"    {update_response.text[:200]}")
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
    
    print()

print("=" * 80)
print(f"ОБНОВЛЕНО CHARTS: {updated_count}/{len(chart_names)}")
print("=" * 80)
print()
print("ВАЖНО: Если проблема сохраняется, возможно нужно:")
print("1. Перезагрузить страницу Dashboard")
print("2. Очистить кеш браузера")
print("3. Проверить, что Database настройки применены (allow_run_async: true)")
print("4. Упростить SQL запросы (добавить фильтры по дате)")

