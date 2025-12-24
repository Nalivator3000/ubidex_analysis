#!/usr/bin/env python3
"""
Обновление таймаута через поле extra в Database
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
get_response = session.get(f"{SUPERSET_URL}/api/v1/database/1", headers=headers, timeout=30)
current_db = get_response.json()["result"]

print("=" * 80)
print("ОБНОВЛЕНИЕ ТАЙМАУТА ЧЕРЕЗ EXTRA")
print("=" * 80)
print()

# Check current extra
extra = current_db.get("extra", "{}")
if isinstance(extra, str):
    try:
        extra = json.loads(extra)
    except:
        extra = {}
elif extra is None:
    extra = {}

print(f"Текущий extra: {json.dumps(extra, indent=2, ensure_ascii=False)}")
print()

# Update extra with timeout
if not isinstance(extra, dict):
    extra = {}

# Add timeout settings to extra
extra["engine_params"] = extra.get("engine_params", {})
extra["engine_params"]["connect_args"] = extra["engine_params"].get("connect_args", {})
extra["engine_params"]["connect_args"]["options"] = "-c statement_timeout=600000"  # 10 minutes in milliseconds

# Also try query_timeout in extra
extra["query_timeout"] = 600

print(f"Новый extra: {json.dumps(extra, indent=2, ensure_ascii=False)}")
print()

# Prepare update
update_payload = {}
for key, value in current_db.items():
    if key not in ["id", "changed_on", "created_on", "changed_by", "created_by", 
                   "changed_by_fk", "created_by_fk", "owners", "tables"]:
        update_payload[key] = value

update_payload["allow_run_async"] = True
update_payload["extra"] = json.dumps(extra)

print("Обновляю Database...")
update_response = session.put(f"{SUPERSET_URL}/api/v1/database/1", headers=headers, json=update_payload, timeout=30)

if update_response.status_code == 200:
    print("✓ Обновление успешно!")
    
    # Verify
    verify_response = session.get(f"{SUPERSET_URL}/api/v1/database/1", headers=headers, timeout=30)
    verified_db = verify_response.json()["result"]
    print()
    print("Проверка:")
    print(f"  allow_run_async: {verified_db.get('allow_run_async')}")
    verified_extra = verified_db.get("extra", "{}")
    if isinstance(verified_extra, str):
        try:
            verified_extra = json.loads(verified_extra)
        except:
            pass
    print(f"  extra.query_timeout: {verified_extra.get('query_timeout') if isinstance(verified_extra, dict) else 'N/A'}")
else:
    print(f"✗ Ошибка: {update_response.status_code}")
    print(update_response.text)

