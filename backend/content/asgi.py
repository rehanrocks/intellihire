"""Local entry point: `python asgi.py` starts the server with auto-reload.

In Docker the entrypoint script runs uvicorn directly instead.
"""
from os import getenv
import uvicorn

from app.main import app

if __name__ == "__main__":


    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(getenv("PORT", "8000")),
        reload=getenv("RELOAD", "true").lower() == "true",
    )
