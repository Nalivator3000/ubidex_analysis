"""
Utility functions for database connection
Supports both SQLite (legacy) and PostgreSQL
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import pandas as pd

def get_db_type():
    """Get database type from environment"""
    return os.environ.get('DB_TYPE', 'postgresql').lower()

def get_postgres_connection_string():
    """Build PostgreSQL connection string from environment variables"""
    # If full DATABASE_URL is provided (e.g. Railway style), use it directly
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    # Fallback to individual env vars
    host = os.environ.get('POSTGRES_HOST', 'localhost')
    port = os.environ.get('POSTGRES_PORT', '5432')
    user = os.environ.get('POSTGRES_USER', 'ubidex')
    password = os.environ.get('POSTGRES_PASSWORD', 'ubidex')
    database = os.environ.get('POSTGRES_DB', 'ubidex')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def get_sqlite_path():
    """
    Get SQLite database path from environment variable or use default.
    Works both in Docker and local environments.
    """
    db_path = os.environ.get('DB_PATH')
    
    if db_path:
        return db_path
    
    # Fallback to local Windows path (for local development)
    local_path = r'C:\Users\Nalivator3000\superset-data-import\events.db'
    if os.path.exists(local_path):
        return local_path
    
    # Docker default path
    return '/data/events.db'

def get_db_engine():
    """
    Get database engine (SQLAlchemy) for PostgreSQL or SQLite.
    """
    db_type = get_db_type()
    
    if db_type == 'postgresql':
        connection_string = get_postgres_connection_string()
        return create_engine(connection_string, pool_pre_ping=True, pool_size=10, max_overflow=20)
    else:
        # SQLite (legacy support)
        db_path = get_sqlite_path()
        return create_engine(f'sqlite:///{db_path}', pool_pre_ping=True)

def get_db_connection():
    """
    Get database connection.
    Returns SQLAlchemy connection for compatibility with pandas.read_sql.
    """
    engine = get_db_engine()
    return engine.connect()

def execute_query(query, params=None):
    """
    Execute SQL query and return results as pandas DataFrame.
    
    Args:
        query: SQL query string
        params: Optional parameters for parameterized queries
    
    Returns:
        pandas DataFrame with results
    """
    engine = get_db_engine()
    with engine.connect() as conn:
        if params:
            result = pd.read_sql(text(query), conn, params=params)
        else:
            result = pd.read_sql(text(query), conn)
    return result

def test_connection():
    """Test database connection"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print(f"✓ Database connection successful ({get_db_type()})")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
