import logging
from logging.config import dictConfig

def setup_logging():
    dictConfig({
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] [%(levelname)s] %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "DEBUG",
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console"]
        }
    })

async def log_info(message: str):
    logging.info(message)

async def log_error(message: str):
    logging.error(message)