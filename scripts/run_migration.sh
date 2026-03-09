#!/bin/bash
# Run Alembic migrations
set -e

cd /app
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."
