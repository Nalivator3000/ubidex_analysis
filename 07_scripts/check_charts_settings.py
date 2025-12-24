#!/usr/bin/env python3
"""
Проверка настроек Charts и Datasets для таймаута
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
print("НАСТРОЙКИ ПРОБЛЕМНЫХ CHARTS")
print("=" * 80)
print()

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
    
    print(f"  Dataset ID: {chart_detail.get('datasource_id')}")
    print(f"  Query context: {chart_detail.get('query_context') is not None}")
    
    # Check params
    params = chart_detail.get("params", {})
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except:
            params = {}
    
    print(f"  Params keys: {list(params.keys()) if isinstance(params, dict) else 'N/A'}")
    
    # Check for timeout in params
    if isinstance(params, dict):
        if "timeout" in params:
            print(f"  ⚠ Timeout в params: {params.get('timeout')}")
        if "query_timeout" in params:
            print(f"  ⚠ Query timeout в params: {params.get('query_timeout')}")
    
    # Check viz_type and query_context
    print(f"  Viz type: {chart_detail.get('viz_type')}")
    
    # Get dataset
    dataset_id = chart_detail.get("datasource_id")
    if dataset_id:
        dataset_response = session.get(f"{SUPERSET_URL}/api/v1/dataset/{dataset_id}", headers=headers, timeout=30)
        dataset = dataset_response.json()["result"]
        print(f"  Dataset: {dataset.get('table_name')}")
        print(f"  Database ID: {dataset.get('database', {}).get('id')}")
    
    print()

print("=" * 80)
print("РЕКОМЕНДАЦИИ")
print("=" * 80)
print()
print("Если query_timeout не настраивается через Database API,")
print("попробуйте обновить настройки через UI или упростить SQL запросы.")

