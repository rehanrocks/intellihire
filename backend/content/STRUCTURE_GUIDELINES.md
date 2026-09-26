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

## ⚠️ Key Rules
1. **No Cross-Dependency**: Commands should never depend on query handlers and vice versa
2. **Model Separation**: Use distinct models for commands (input) and queries (output)
3. **Handler Purity**: Keep handlers focused on business logic, not HTTP concerns
4. **Utility Reuse**: Place shared functionality in `utils/` (e.g., database helpers)

## 🧪 Testing Strategy
- **Commands**: Test handlers with mocked database operations
- **Queries**: Test handlers with mocked database results
- **API**: Use FastAPI test client for endpoint validation
- **External Clients**: Mock external service responses for testing

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

> Always update this document when adding new structural patterns or conventions.