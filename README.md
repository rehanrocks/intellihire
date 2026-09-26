# IntelliHire

IntelliHire is a hiring platform built with FastAPI and PostgreSQL, containerized using Docker.

## Prerequisites

- Docker and Docker Compose installed on your machine.
- Git (to clone the repository).

## Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd intellihire
   ```

2. Create a `.env` file in the root directory (if not already present) with the following variables:
   ```env
   # ports
   # adminer
   MACHINE_ADMINER_PORT=8080
   ADMINER_PORT=8080

   # postgres
   POSTGRES_PORT=5432
   POSTGRES_PASSWORD=postgres
   POSTGRES_USERNAME=postgres

   # content
   CONTENT_PORT=4010
   ```
   Adjust the values as needed.

3. Build and start the services:
   ```bash
   docker-compose up -d --build
   ```
   This will start three services:
   - **postgres**: PostgreSQL database with pgvector extension.
   - **content**: FastAPI application (the backend API).
   - **adminer**: Database administration tool (accessible at http://localhost:8080).

4. The application will be available at:
   - API: http://localhost:4010
   - Adminer: http://localhost:8080 (use PostgreSQL server `postgres`, username `postgres`, password `postgres`)

## Services Overview

- **postgres**: Runs on port 5432 (mapped from `POSTGRES_PORT`). Data is persisted in `./backend/db_data/`.
- **content**: The FastAPI app, built from `backend/content/`, runs on port 4010 (mapped from `CONTENT_PORT`).
- **adminer**: Runs on port 8080 (mapped from `MACHINE_ADMINER_PORT`) for easy database management.

## Environment Variables

The `.env` file configures the ports and credentials. Modify these values to avoid conflicts with other services on your machine.

## Stopping the Services

To stop and remove the containers, networks, and volumes:
```bash
docker-compose down
```
To also remove the persisted database volume:
```bash
docker-compose down -v
```

## Development

If you want to modify the FastAPI code and see changes in real-time without rebuilding the image, consider mounting the source code as a volume in `docker-compose.yml` (currently not set up for development). For production-like testing, rebuild the image after changes:
```bash
docker-compose up -d --build
```

## Notes

- The `content` service uses the command `sh ./docker-entrypoint.sh` to start the application. Ensure the script is executable.
- The `postgres` service is based on `ankane/pgvector:latest` to support vector operations.
- The `adminer` service is optional but useful for inspecting the database.

## License

[Specify license if applicable]

---
*README generated for IntelliHire project.*
