# CQRS Structure Guidelines for Content Service

This document defines how to maintain and expand the CQRS-based FastAPI codebase. The structure enforces separation of concerns between commands (write operations) and queries (read operations) while centralizing shared utilities.

## 📁 Directory Structure
```
backend/content/src/
├── api/              # FastAPI endpoint definitions
│   └── routers/      # Route handlers for HTTP endpoints
│       └── __init__.py
├── commands/         # Write operations (data modification)
│   ├── handlers/     # Command execution logic (e.g., create_user)
│   │   └── __init__.py
│   └── models/       # Command data models (DTOs)
│       └── __init__.py
├── queries/          # Read operations (data retrieval)
│   ├── handlers/     # Query execution logic (e.g., get_user)
│   │   └── __init__.py
│   └── models/       # Query result models
│       └── __init__.py
├── models/           # Shared SQLAlchemy models
├── external_clients/ # External service clients (REST, SOAP, etc.)
├── migrations/       # Alembic database migrations
├── utils/            # Shared utilities
│   ├── database.py   # Database connection and operations
│   └── logging.py    # Logging configuration and helpers
└── main.py           # FastAPI application entry point
```

## 🛠️ Adding New Features
### 1. For Write Operations (Commands)
- **Models**: Define input validation in `commands/models/`
  ```python
  # Example: commands/models/create_blog_post.py
  from pydantic import BaseModel

  class CreateBlogPostCommand(BaseModel):
      title: str
      content: str
      author_id: str
  ```
- **Handlers**: Implement business logic in `commands/handlers/`
  ```python
  # Example: commands/handlers/create_blog_post.py
  from .models import CreateBlogPostCommand
  from ..utils.database import get_collection

  async def handle_create_blog_post(command: CreateBlogPostCommand):
      collection = await get_collection("blog_posts")
      result = await collection.insert_one(command.dict())
      return {"id": str(result.inserted_id)}
  ```
- **API Integration**: Add routes in `api/routers/__init__.py`
  ```python
  @router.post("/blog-posts")
  async def create_blog_post(command: CreateBlogPostCommand):
      result = await handle_create_blog_post(command)
      return result
  ```

### 2. For Read Operations (Queries)
- **Models**: Define output shaping in `queries/models/`
  ```python
  # Example: queries/models/get_blog_post.py
  from pydantic import BaseModel

  class GetBlogPostQuery(BaseModel):
      post_id: str
  ```
- **Handlers**: Implement retrieval logic in `queries/handlers/`
  ```python
  # Example: queries/handlers/get_blog_post.py
  from .models import GetBlogPostQuery
  from ..utils.database import get_collection

  async def handle_get_blog_post(query: GetBlogPostQuery):
      collection = await get_collection("blog_posts")
      post = await collection.find_one({"_id": query.post_id})
      return post
  ```
- **API Integration**: Add routes in `api/routers/__init__.py`
  ```python
  @router.get("/blog-posts/{post_id}")
  async def get_blog_post(post_id: str):
      query = GetBlogPostQuery(post_id=post_id)
      result = await handle_get_blog_post(query)
      return result
  ```

### 3. Database Models
- **SQLAlchemy Models**: Define database schemas in `models/`
  ```python
  # Example: models/blog_post.py
  from sqlalchemy import Column, Integer, String, Text
  from sqlalchemy.ext.declarative import declarative_base
  
  Base = declarative_base()
  
  class BlogPost(Base):
      __tablename__ = "blog_posts"
      
      id = Column(Integer, primary_key=True, index=True)
      title = Column(String, index=True)
      content = Column(Text)
      author_id = Column(String)
  ```

### 4. External Clients
- **Custom Clients**: Implement external service clients in `external_clients/`
  ```python
  # Example: external_clients/payment_gateway.py
  import httpx
  
  class PaymentGatewayClient:
      def __init__(self, base_url: str, api_key: str):
          self.base_url = base_url
          self.api_key = api_key
          
      async def charge(self, amount: int, currency: str):
          async with httpx.AsyncClient() as client:
              response = await client.post(
                  f"{self.base_url}/charge",
                  json={"amount": amount, "currency": currency},
                  headers={"Authorization": f"Bearer {self.api_key}"}
              )
              return response.json()
  ```

### 5. Shared Utilities
- **Database**: Use `utils/database.py` for connection and collection access
- **Logging**: Use `utils/logging.py` for consistent logging
  ```python
  from ..utils.logging import log_info
  await log_info("Processing blog post creation...")
  ```

## 📐 Unified Schema Language

To enable sharing models across different integrations, follow this standardized schema definition process:

### Schema Definition Pattern
All models should follow a consistent structure that separates concerns while enabling reuse:

```python
# Unified schema pattern
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BaseSchema(BaseModel):
    """Base schema with common fields for all models"""
    id: str = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

# Example command schema
class CreateBlogPostCommand(BaseSchema):
    title: str = Field(..., max_length=200)
    content: str
    author_id: str
    tags: Optional[List[str]] = Field(default=None)

# Example query schema  
class GetBlogPostQuery(BaseSchema):
    post_id: str
    include_content: bool = Field(default=True)

# Example database model
class BlogPostDB(Base):
    __tablename__ = "blog_posts"
    
    id = Column(String, primary_key=True)
    title = Column(String, index=True, length=200)
    content = Column(Text)
    author_id = Column(String)
    tags = Column(String, default="[]")  # Stored as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Integration Pattern
When integrating with external systems, use the schema conversion layer:

```python
# Schema conversion for external integration
def convert_db_to_query(db_model: BlogPostDB) -> Dict:
    """Convert database model to query response schema"""
    return {
        "id": str(db_model.id),
        "title": db_model.title,
        "content": db_model.content,
        "author_id": db_model.author_id,
        "tags": json.loads(db_model.tags) if db_model.tags else [],
        "created_at": db_model.created_at.isoformat(),
        "updated_at": db_model.updated_at.isoformat()
    }

def convert_external_to_command(external_data: Dict) -> CreateBlogPostCommand:
    """Convert external system data to command schema"""
    return CreateBlogPostCommand(
        title=external_data.get("title"),
        content=external_data.get("content"),
        author_id=external_data.get("authorId"),
        tags=external_data.get("tags", [])
    )
```

### Sharing Across Integrations
1. **Central Schema Registry**: Keep shared schemas in a dedicated module
2. **Type Hints**: Use Python type hints for IDE support and validation
3. **JSON Serialization**: Ensure all schemas have consistent JSON configuration
4. **Database Mapping**: Use SQLAlchemy models as the single source of truth
5. **API Contracts**: Define clear API contracts using the standardized schemas

### Example: Multi-Integration Schema
```python
# schemas/__init__.py - Central schema definitions
from .base import BaseSchema
from .commands import CreateBlogPostCommand, UpdateBlogPostCommand
from .queries import GetBlogPostQuery, ListBlogPostsQuery

# external_integration.py - Using shared schemas
from schemas import CreateBlogPostCommand

def process_external_post(external_data: Dict):
    """Process posts from external systems using standardized schemas"""
    command = CreateBlogPostCommand(
        title=external_data["title"],
        content=external_data["content"],
        author_id=external_data["author"]["id"]
    )
    # Continue with command handler
```

## 🐳 Docker Deployment

### Container Structure
The service is containerized with the following structure:
```
backend/content/
├── Dockerfile
├── docker-entrypoint.sh
├── requirements.txt
└── src/
    └── main.py
```

### Dockerfile Configuration
```dockerfile
# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run the application via entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
```

### Entrypoint Script
The `docker-entrypoint.sh` script handles initialization and runs the application:
```bash
#!/bin/bash
# run alembic migrations
# alembic upgrade head

# run the main.py script using python3
python3 src/main.py
```

### Building and Running
```bash
# Build the Docker image
docker build -t content-service ./backend/content

# Run the container
docker run -p 8000:8000 content-service
```

### Environment Variables
Configure the service using environment variables:
- `DATABASE_URL` - Database connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `EXTERNAL_API_KEYS` - Keys for external service integrations

## ⚠️ Key Rules
1. **No Cross-Dependency**: Commands should never depend on query handlers and vice versa
2. **Model Separation**: Use distinct models for commands (input) and queries (output)
3. **Handler Purity**: Keep handlers focused on business logic, not HTTP concerns
4. **Utility Reuse**: Place shared functionality in `utils/` (e.g., database helpers)
5. **Schema Standardization**: Follow the unified schema language for cross-integration compatibility

## 🧪 Testing Strategy
- **Commands**: Test handlers with mocked database operations
- **Queries**: Test handlers with mocked database results
- **API**: Use FastAPI test client for endpoint validation
- **External Clients**: Mock external service responses for testing
- **Schema Validation**: Test schema serialization/deserialization

## 📦 Example Expansion
To add a `Comment` feature:
1. `commands/models/create_comment.py` - Input model
2. `commands/handlers/create_comment.py` - Business logic
3. `queries/models/get_comments.py` - Output model
4. `queries/handlers/get_comments.py` - Retrieval logic
5. `models/comment.py` - Database model
6. Update `api/routers/__init__.py` with new endpoints

This structure ensures:
- Clear separation of concerns
- Independent scaling of read/write operations
- Maintainable, testable code
- Consistent utility usage
- Cross-integration schema compatibility
- Containerized deployment readiness

> Always update this document when adding new structural patterns or conventions.