"""IntelliHire backend package.

Everything that makes up the API lives under this package:

- core/        settings, security helpers, shared FastAPI dependencies
- database/    SQLAlchemy engine/session and the table models
- schemas/     Pydantic models that validate request bodies and shape responses
- services/    business rules (register a user, log in, upload a CV ...)
- controller/  FastAPI routers: the HTTP endpoints that call the services
- main.py      builds the FastAPI application object
"""
