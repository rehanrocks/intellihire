from .models import CreateItemCommand
from ..utils.database import get_collection
from ..utils.logging import log_info

async def handle_create_item(command: CreateItemCommand):
    await log_info(f"Creating item: {command.item_name}")
    collection = await get_collection("items")
    result = await collection.insert_one(command.dict())
    return {"status": "success", "message": "Item created", "id": str(result.inserted_id)}