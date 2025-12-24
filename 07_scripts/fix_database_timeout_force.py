#!/usr/bin/env python3
"""
Принудительное обновление таймаута Database в Superset
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

print("=" * 80)
print("ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ ТАЙМАУТА DATABASE")
print("=" * 80)
print()

# Login
session = requests.Session()
login_url = f"{SUPERSET_URL}/api/v1/security/login"
login_response = session.post(login_url, json={
    "username": SUPERSET_USERNAME,
    "password": SUPERSET_PASSWORD,
    "provider": "db",
    "refresh": True
}, timeout=30)
login_response.raise_for_status()
access_token = login_response.json()["access_token"]

# Get CSRF
csrf_url = f"{SUPERSET_URL}/api/v1/security/csrf_token/"
csrf_response = session.get(csrf_url, headers={
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
db_url = f"{SUPERSET_URL}/api/v1/database/"
db_response = session.get(db_url, headers=headers, timeout=30)
databases = db_response.json()["result"]
db = next((d for d in databases if d.get("database_name") == "Ubidex Events DB"), None)

if not db:
    print("База данных не найдена!")
    sys.exit(1)

db_id = db["id"]
print(f"База данных найдена: ID {db_id}")
print(f"Текущий query_timeout: {db.get('query_timeout')}")
print(f"Текущий allow_run_async: {db.get('allow_run_async')}")
print()

# Get full database details
get_db_url = f"{SUPERSET_URL}/api/v1/database/{db_id}"
get_response = session.get(get_db_url, headers=headers, timeout=30)
current_db = get_response.json()["result"]

# Prepare update - include ALL fields
update_payload = {}
for key, value in current_db.items():
    if key not in ["id", "changed_on", "created_on", "changed_by", "created_by", 
                   "changed_by_fk", "created_by_fk", "owners", "tables"]:
        update_payload[key] = value

# Force update timeout settings
update_payload["allow_run_async"] = True
update_payload["query_timeout"] = 600

print("Обновляю настройки...")
print(f"  allow_run_async: {update_payload['allow_run_async']}")
print(f"  query_timeout: {update_payload['query_timeout']}")
print()

# Update
update_url = f"{SUPERSET_URL}/api/v1/database/{db_id}"
update_response = session.put(update_url, headers=headers, json=update_payload, timeout=30)

if update_response.status_code == 200:
    print("✓ Обновление успешно!")
    
    # Verify
    verify_response = session.get(get_db_url, headers=headers, timeout=30)
    verified_db = verify_response.json()["result"]
    print()
    print("Проверка:")
    print(f"  allow_run_async: {verified_db.get('allow_run_async')}")
    print(f"  query_timeout: {verified_db.get('query_timeout')} секунд")
else:
    print(f"✗ Ошибка: {update_response.status_code}")
    print(update_response.text)

