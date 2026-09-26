"""
This file initializes the FastAPI router
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from utils.exceptions import CustomHttpException

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["*"],
)

# pylint: disable=unused-argument
@app.exception_handler(CustomHttpException)
async def custom_http_exception_handler(request: Request, exc: CustomHttpException):
    """
    Maps CustomHttpException to JSONResponse
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message},
    )
