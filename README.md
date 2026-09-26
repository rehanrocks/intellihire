# IntelliHire

IntelliHire is a modern recruitment platform built with FastAPI using the CQRS pattern.

## Project Structure

```
backend/
└── content/
    └── src/
        ├── api/              # FastAPI endpoint definitions
        │   └── routers/      # Route handlers for HTTP endpoints
        ├── commands/         # Write operations (data modification)
        │   ├── handlers/     # Command execution logic
        │   └── models/       # Command data models (DTOs)
        ├── queries/          # Read operations (data retrieval)
        │   ├── handlers/     # Query execution logic
        │   └── models/       # Query result models
        ├── models/           # Shared SQLAlchemy models
        ├── external_clients/ # External service clients (REST, SOAP, etc.)
        ├── migrations/       # Alembic database migrations
        ├── utils/            # Shared utilities (database, logging)
        └── main.py           # FastAPI application entry point
```

## CQRS Structure Guidelines

For detailed information about the CQRS structure and how to expand the codebase, see [STRUCTURE_GUIDELINES.md](backend/content/STRUCTURE_GUIDELINES.md).

## Adding External Clients

External service clients that don't have SDKs should be placed in the `external_clients/` directory. This includes REST clients, SOAP clients, or any other custom integration.

Example:
```
external_clients/
├── __init__.py
├── payment_gateway.py     # Custom REST client for payment processing
└── hr_system.py           # Custom client for HR system integration
```

## Database Models and Migrations

- SQLAlchemy models should be placed in the `models/` directory
- Alembic migrations should be placed in the `migrations/` directory

## Unified Schema Language

To enable sharing models across different integrations, follow the unified schema language defined in [STRUCTURE_GUIDELINES.md](backend/content/STRUCTURE_GUIDELINES.md#unified-schema-language). This ensures consistent schema definitions that can be used across commands, queries, database models, and external integrations.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   uvicorn backend.content.src.main:app --reload
   ```

## Running with Docker

The content service can be containerized using Docker:

1. Build the Docker image:
   ```bash
   docker build -t content-service ./backend/content
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 content-service
   ```

The Dockerfile uses an entrypoint script that runs the main.py application.

## Development Guidelines

- Follow the CQRS pattern as described in STRUCTURE_GUIDELINES.md
- Place external service clients in the `external_clients/` directory
- Use the `models/` directory for SQLAlchemy models
- Use the `migrations/` directory for Alembic migrations
- Place shared utilities in the `utils/` directory
- Follow the unified schema language for cross-integration compatibility
