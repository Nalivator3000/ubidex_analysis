#!/bin/bash
# Script to setup database in Docker environment

echo "Setting up database for Docker..."

# Create data directory if it doesn't exist
mkdir -p data
mkdir -p output

# Check if database exists
if [ ! -f "data/events.db" ]; then
    echo "Warning: events.db not found in data/ directory"
    echo "Please copy your events.db file to ./data/events.db"
    echo ""
    echo "On Windows:"
    echo "  copy C:\\Users\\Nalivator3000\\superset-data-import\\events.db data\\events.db"
    echo ""
    echo "On Linux/Mac:"
    echo "  cp /path/to/events.db data/events.db"
    exit 1
fi

echo "Database found: data/events.db"
echo "Setup complete!"

