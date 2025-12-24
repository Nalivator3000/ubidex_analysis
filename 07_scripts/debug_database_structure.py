#!/usr/bin/env python3
"""
Отладка структуры Database в Superset API
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

# Get database
db_response = session.get(f"{SUPERSET_URL}/api/v1/database/1", headers=headers, timeout=30)
db = db_response.json()["result"]

print("=" * 80)
print("СТРУКТУРА DATABASE В API")
print("=" * 80)
print()
print("Все поля Database:")
print(json.dumps(db, indent=2, ensure_ascii=False, default=str))

