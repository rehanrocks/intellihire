"""Builds the FastAPI application.

`uvicorn app.main:app` imports this module and serves the `app` object.
Everything is assembled inside create_app() so tests can build a fresh app
with different settings.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="IntelliHire backend. Module 1: authentication and account management.",
    )

# CORS: which browser origins may call this API. "*" is fine while developing;
# in production list the real frontend domain(s).
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


