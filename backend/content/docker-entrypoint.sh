#!/bin/sh
# Container start-up: bring the database schema up to date, then serve.
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API Server..."
python3 asgi.py
