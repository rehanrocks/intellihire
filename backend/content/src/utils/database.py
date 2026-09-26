from motor.motor_asyncio import AsyncIOMotorClient

async def get_database():
    client = AsyncIotorClient("mongodb://localhost:27017")
    return client["content_db"]

async def get_collection(collection_name: str):
    db = await get_database()
    return db[collection_name]