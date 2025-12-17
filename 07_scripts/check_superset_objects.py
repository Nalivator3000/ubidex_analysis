#!/usr/bin/env python3
"""
Проверка существующих Dashboard и Chart в Superset
"""
import requests
import json
import sys
import io
import os

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://superset:8088")
SUPERSET_USERNAME = "admin"
SUPERSET_PASSWORD = "admin"

print("=" * 80)
print("ПРОВЕРКА DASHBOARD И CHART В SUPERSET")
print("=" * 80)
print()

# Login
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
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    print("✓ Авторизация успешна")
    print()
except Exception as e:
    print(f"✗ Ошибка авторизации: {e}")
    sys.exit(1)

# Check Dashboards
print("1. Существующие Dashboard:")
print()
try:
    dashboards_url = f"{SUPERSET_URL}/api/v1/dashboard/"
    dashboards_response = session.get(dashboards_url, headers=headers, timeout=10)
    dashboards_response.raise_for_status()
    dashboards = dashboards_response.json().get("result", [])
    
    if dashboards:
        for db in dashboards[:10]:  # Show first 10
            print(f"   - {db.get('dashboard_title')} (ID: {db.get('id')})")
            print(f"     URL: http://localhost:8088/superset/dashboard/{db.get('id')}/")
    else:
        print("   Нет созданных Dashboard")
    print()
except Exception as e:
    print(f"   Ошибка: {e}")
    print()

# Check Charts
print("2. Существующие Chart:")
print()
try:
    charts_url = f"{SUPERSET_URL}/api/v1/chart/"
    charts_response = session.get(charts_url, headers=headers, timeout=10)
    charts_response.raise_for_status()
    charts = charts_response.json().get("result", [])
    
    if charts:
        for chart in charts[:10]:  # Show first 10
            print(f"   - {chart.get('slice_name')} (ID: {chart.get('id')})")
            print(f"     URL: http://localhost:8088/superset/explore/?slice_id={chart.get('id')}")
    else:
        print("   Нет созданных Chart")
    print()
except Exception as e:
    print(f"   Ошибка: {e}")
    print()

print("=" * 80)
print("ИНСТРУКЦИЯ:")
print("=" * 80)
print()
print("Если Dashboard нет, создайте его:")
print("  1. Dashboards → + Dashboard")
print("  2. Название: 'Анализ паблишеров'")
print("  3. Save")
print()
print("Если Chart есть, но не добавлен в Dashboard:")
print("  1. Откройте Dashboard → Edit Dashboard")
print("  2. + Chart → выберите ваш Chart")
print("  3. Перетащите на Dashboard")
print("  4. Save")
print()

