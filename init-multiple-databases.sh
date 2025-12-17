#!/bin/bash
# Initialize multiple PostgreSQL databases

set -e

# Default databases
POSTGRES_MULTIPLE_DATABASES=${POSTGRES_MULTIPLE_DATABASES:-ubidex,superset}

function create_database() {
	local database=$1
	echo "Creating database '$database'"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	    SELECT 'CREATE DATABASE $database'
	    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
	    GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
	echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
	for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
		# Skip if it's the default database
		if [ "$db" != "$POSTGRES_DB" ]; then
			create_database $db
		fi
	done
	echo "Multiple databases created"
fi

