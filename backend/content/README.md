# Content Service

The `content` service is the FastAPI backend application for IntelliHire.

## Structure

```
backend/content/
├── app/
│   └── main.py          # FastAPI app initialization and middleware setup
├── asgi.py              # Entry point for Uvicorn server
├── docker-entrypoint.sh # Script to run migrations and start the server
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build instructions
├── controller/          # Route handlers and API endpoints
├── database/            # Database models, seeds, and connection utilities
├── schemas/             # Pydantic models for request/response validation
└── utils/               # Utility functions and helpers
```

## Key Components

### Core Application Files

- **app/main.py**: Creates the FastAPI instance and configures CORS middleware to allow cross-origin requests from frontend applications
- **asgi.py**: Entry point that imports the FastAPI app and runs it with Uvicorn on the PORT environment variable (default: 8000)
- **docker-entrypoint.sh**: Script that currently runs the ASGI application; can be extended to run database migrations using Alembic

### Project Structure

- **controller/**: Will contain API route handlers organized by resource (e.g., `/api/v1/users`, `/api/v1/jobs`)
- **database/**: Contains SQLAlchemy models for database tables and seed data for initial population
- **schemas/**: Contains Pydantic models for request/response validation and serialization
- **utils/**: Contains helper functions and utilities used across the application

## Dependencies

The `requirements.txt` file includes:
- FastAPI (0.68.0) - Web framework
- Uvicorn (0.15.0) - ASGI server
- Pydantic (1.8.2) - Data validation
- SQLAlchemy (1.4.23) - ORM
- Alembic (1.7.3) - Database migrations
- httpx (0.18.2) - HTTP client
- motor (2.5.1) - MongoDB driver (for potential future use)

## Container Configuration

- **Dockerfile**: Uses Python 3.9 slim image, installs dependencies, and sets up the application
- **docker-entrypoint.sh**: Currently runs the application directly; can be extended for database migrations

This modular structure allows for easy maintenance, testing, and scaling of the FastAPI application.