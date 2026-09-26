from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from ..commands.models import CreateItemCommand
from ..commands.handlers import handle_create_item
from ..queries.models import GetItemQuery
from ..queries.handlers import handle_get_item

router = APIRouter(prefix="/api")

@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(command: CreateItemCommand):
    result = await handle_create_item(command)
    return result

@router.get("/items/{item_id}", status_code=status.HTTP_200_OK)
async def get_item(item_id: int):
    query = GetItemQuery(item_id=item_id)
    result = await handle_get_item(query)
    return result

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy"}