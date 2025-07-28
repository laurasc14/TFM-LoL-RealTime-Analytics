import os, json, asyncio
from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "events_raw"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "lol_realtime"
COLLECTION = "matches"

async def consume():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION]

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await collection.insert_one(msg.value)
            print(f"Inserted match {msg.value.get('match_id')}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())
