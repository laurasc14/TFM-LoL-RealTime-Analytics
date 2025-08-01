import asyncio, json, glob, os, aiofiles
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("TOPIC", "events_raw")

async def send_file(producer, path):
    async with aiofiles.open(path, "r") as f:
        async for line in f:
            await producer.send_and_wait(TOPIC, line.encode())
    print(f"✔  {path} enviado")

async def main(pattern="data/historial/*.jsonl"):
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await producer.start()
    try:
        for file in sorted(glob.glob(pattern)):
            await send_file(producer, file)
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())