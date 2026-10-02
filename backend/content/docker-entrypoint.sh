#!/bin/sh
# Container start-up: bring the database schema up to date, then serve.
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
