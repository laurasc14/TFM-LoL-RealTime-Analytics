import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient

uri = os.getenv("MONGO_URI", "mongodb://final-mongo:27017")
dbn = os.getenv("MONGO_DB", "lol")
coln = os.getenv("MONGO_COLL", "matches_raw")

async def main():
    c = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    print("Ping:", await c.admin.command("ping"))
    col = c[dbn][coln]
    r = await col.insert_one({"_probe": True})
    print("Inserted _probe id:", r.inserted_id)
    c.close()

if __name__ == "__main__":
    asyncio.run(main())
