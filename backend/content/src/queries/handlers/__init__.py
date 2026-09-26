from .models import GetItemQuery
from ..utils.database import get_collection
from ..utils.logging import log_info

async def handle_get_item(query: GetItemQuery):
    await log_info(f"Retrieving item: {query.item_id}")
    collection = await get_collection("items")
    item = await collection.find_one({"_id": query.item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "success", "data": item}