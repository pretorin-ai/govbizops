#!/usr/bin/env bash
# Start a PostgreSQL dev database in Docker for govbizops.
# Idempotent — skips if the container is already running.

set -euo pipefail

CONTAINER_NAME="govbizops-postgres"
POSTGRES_USER="govbizops"
POSTGRES_PASSWORD="govbizops"
POSTGRES_DB="govbizops"
POSTGRES_PORT="5432"
VOLUME_NAME="govbizops-pgdata"

# Check if container already running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "✓ Container '${CONTAINER_NAME}' is already running."
    echo ""
    echo "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Starting existing container '${CONTAINER_NAME}'..."
    docker start "${CONTAINER_NAME}"
else
    echo "Creating new PostgreSQL container '${CONTAINER_NAME}'..."
    docker run -d \
        --name "${CONTAINER_NAME}" \
        -e POSTGRES_USER="${POSTGRES_USER}" \
        -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
        -e POSTGRES_DB="${POSTGRES_DB}" \
        -p "${POSTGRES_PORT}:5432" \
        -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
        postgres:16-alpine
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker exec "${CONTAINER_NAME}" pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready!"
        echo ""
        echo "Add this to your .env file:"
        echo "DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
        exit 0
    fi
    sleep 1
done

echo "✗ Timed out waiting for PostgreSQL to start."
exit 1
