import os, json, asyncio
from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "events_raw"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "lol_realtime"
COLLECTION = "matches"

async def consume():
    print("Starting Kafka consumer...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION]

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="lol-consumer-group",
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )
    await consumer.start()
    try:
        count = 0
        async for msg in consumer:
            await collection.insert_one(msg.value)
            count += 1
            print(f"[{count}] Inserted match {msg.value.get('match_id')}")
    finally:
        await consumer.stop()
        print("Consumer stopped.")

if __name__ == "__main__":
    asyncio.run(consume())
