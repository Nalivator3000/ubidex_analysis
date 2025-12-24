"""
Superset configuration for Ubidex Analysis
"""
import os

# Database connection for Superset metadata
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "postgresql://ubidex:ubidex@postgres:5432/superset",
)

# Redis for caching (supports optional password, e.g. Railway Redis)
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
}

if REDIS_PASSWORD:
    # Needed when Redis requires AUTH (e.g. managed services)
    CACHE_CONFIG["CACHE_REDIS_PASSWORD"] = REDIS_PASSWORD

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

# Query timeout settings (in seconds)
# Increase timeout for long-running queries
SQLLAB_TIMEOUT = 600  # 10 minutes for SQL Lab queries (default is 60)
SQLLAB_ASYNC_TIME_LIMIT_SEC = 600  # 10 minutes for async queries

# Web server timeout (for HTTP requests)
SUPERSET_WEBSERVER_TIMEOUT = 600  # 10 minutes for web server requests

# Database connection pool settings
SQLALCHEMY_POOL_TIMEOUT = 120  # Connection pool timeout (increased for long queries)
SQLALCHEMY_POOL_RECYCLE = 3600  # Recycle connections after 1 hour
SQLALCHEMY_POOL_PRE_PING = True  # Verify connections before using

# Note: 
# 1. Chart query timeout can also be set per database connection in Superset UI:
#    Data → Databases → Edit your database → Advanced → "Query Timeout"
#    Set it to 600 (10 minutes) or higher
# 2. IMPORTANT: Do NOT add connect_args to SQLAlchemy URI in Superset UI - it doesn't work!
#    Instead, enable "Asynchronous query execution" in Database settings → Query Execution Options

# Enable CORS if needed
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": ["*"],
}

