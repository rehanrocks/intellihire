# Production-style image for the content (API) service.
FROM python:3.12-slim

# Python settings: no .pyc clutter, unbuffered logs (so docker logs shows them live).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install dependencies first so Docker caches this layer between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh
CMD ["sh", "./docker-entrypoint.sh"]
