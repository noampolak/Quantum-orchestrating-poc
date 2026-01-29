#!/bin/bash
set -e

# Create temporal databases if they don't exist
# Note: We connect to 'postgres' database to create other databases
# Temporal needs two databases: temporal and temporal_visibility

# Create temporal database
DB_EXISTS=$(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='temporal'")
if [ -z "$DB_EXISTS" ]; then
    echo "Creating temporal database..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -c "CREATE DATABASE temporal;"
    echo "Database 'temporal' created"
else
    echo "Database 'temporal' already exists"
fi

# Create temporal_visibility database
VIS_DB_EXISTS=$(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='temporal_visibility'")
if [ -z "$VIS_DB_EXISTS" ]; then
    echo "Creating temporal_visibility database..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -c "CREATE DATABASE temporal_visibility;"
    echo "Database 'temporal_visibility' created"
else
    echo "Database 'temporal_visibility' already exists"
fi
