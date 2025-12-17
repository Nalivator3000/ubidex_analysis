"""
Superset configuration for Ubidex Analysis
"""
import os

# Database connection for Superset metadata
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "postgresql://ubidex:ubidex@postgres:5432/superset"
)

# Redis for caching
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
}

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ENABLE_TEMPLATE_REMOVE_FILTERS": True,
}

# Security
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "your-secret-key-change-in-production")

# Language
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "ru": {"flag": "ru", "name": "Russian"},
}

# Timezone
TIMEZONE = "UTC"

# Row limit for charts
ROW_LIMIT = 50000

# SQL Lab display limit (how many rows to show in SQL Lab results)
DISPLAY_MAX_ROW = 100000

# SQL Lab query limit (maximum rows that can be returned by a query)
SQL_MAX_ROW = 1000000

# Enable CORS if needed
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": ["*"],
}

