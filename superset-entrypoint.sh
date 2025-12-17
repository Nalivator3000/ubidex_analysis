#!/bin/bash
set -e

echo "=== Superset Entrypoint Script ==="
echo "Running as user: $(id -u)"
echo "Current directory: $(pwd)"

# Install system dependencies and psycopg2 if needed
if [ "$(id -u)" = "0" ]; then
    echo "Running as root, installing dependencies..."
    
    # Install system dependencies for psycopg2
    echo "Checking system dependencies..."
    if ! dpkg -l | grep -q "^ii.*libpq-dev"; then
        echo "Installing system dependencies for psycopg2..."
        apt-get update && \
        apt-get install -y \
            postgresql-client \
            libpq-dev \
            gcc \
            python3-dev \
            && rm -rf /var/lib/apt/lists/*
        echo "System dependencies installed."
    else
        echo "System dependencies already installed."
    fi
    
    # Verify flask_cors is available (it should be in the base image)
    echo "Checking for flask_cors..."
    if ! /app/.venv/bin/python -c "import flask_cors" 2>/dev/null; then
        echo "WARNING: flask_cors not found! This should not happen. Checking venv structure..."
        # Try to reinstall flask_cors if it's missing
        echo "Attempting to reinstall flask_cors..."
        /app/.venv/bin/python -m ensurepip --upgrade --default-pip 2>/dev/null || true
        /app/.venv/bin/python -m pip install --no-cache-dir flask-cors 2>/dev/null || {
            echo "ERROR: Cannot restore flask_cors! The venv may be corrupted."
            echo "This might be caused by previous psycopg2 installation attempts."
        }
    else
        echo "flask_cors is available."
    fi
    
    # Install pip into venv first if needed, then psycopg2
    echo "Checking for pip in venv..."
    if ! /app/.venv/bin/python -m pip --version 2>/dev/null; then
        echo "pip not found in venv. Installing pip..."
        /app/.venv/bin/python -m ensurepip --upgrade --default-pip || {
            echo "Warning: ensurepip failed, trying to install pip manually..."
            curl -sS https://bootstrap.pypa.io/get-pip.py | /app/.venv/bin/python || {
                echo "ERROR: Failed to install pip!"
                exit 1
            }
        }
    fi
    
    # Install psycopg2 if not already installed
    echo "Checking for psycopg2..."
    if ! /app/.venv/bin/python -c "import psycopg2" 2>/dev/null; then
        echo "psycopg2 not found. Installing psycopg2-binary into venv..."
        # Use python -m pip to ensure we're using the venv's pip
        /app/.venv/bin/python -m pip install --no-cache-dir psycopg2-binary && {
            echo "psycopg2-binary installed successfully via venv pip."
        } || {
            echo "ERROR: Failed to install psycopg2-binary via venv pip!"
            exit 1
        }
        # Verify flask_cors is still available after psycopg2 installation
        echo "Verifying flask_cors is still available..."
        /app/.venv/bin/python -c "import flask_cors; print('flask_cors still available')" || {
            echo "ERROR: flask_cors disappeared after psycopg2 installation!"
            echo "Attempting to reinstall flask_cors..."
            /app/.venv/bin/python -m pip install --no-cache-dir flask-cors || {
                echo "ERROR: Failed to restore flask_cors!"
                exit 1
            }
        }
        # Fix permissions
        chown -R superset:superset /app/.venv 2>/dev/null || true
        echo "Verifying psycopg2 installation..."
        /app/.venv/bin/python -c "import psycopg2; print('psycopg2 imported successfully')" || {
            echo "ERROR: psycopg2 installation verification failed!"
            exit 1
        }
    else
        echo "psycopg2 already installed."
    fi
else
    echo "Not running as root, skipping dependency installation."
fi

# Switch to app directory and set up environment
export PATH=/app/.venv/bin:$PATH
cd /app

# Run Superset commands
# Note: Running as root for simplicity. For production, consider switching to superset user.
echo "Running Superset initialization..."
superset db upgrade || true
superset fab create-admin --username admin --firstname Admin --lastname User --email admin@ubidex.com --password admin || true
superset init || true
python3 /app/superset_init.py || true

# Start Superset
echo "Starting Superset server..."
exec superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger

