import os, json, asyncio, signal, logging
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaConsumer, ConsumerRecord
from aiokafka.errors import KafkaError
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ValidationError

# -------- Logging --------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("consumer")

# -------- Config --------
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9093,kafka3:9094")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "lol-consumer")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "matches")
AUTO_OFFSET_RESET = os.getenv("AUTO_OFFSET_RESET", "latest")  # earliest para reprocesar

MONGO_URI = os.getenv("MONGO_URI", "mongodb://final-mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "lol")
MONGO_COLL = os.getenv("MONGO_COLL", "matches_raw")

MAX_BATCH = int(os.getenv("MAX_BATCH", "100"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "10"))

# -------- Schema --------
class MatchMsg(BaseModel):
    match_id: str = Field(..., min_length=3)
    timestamp: float

# -------- Mongo helpers --------
@asynccontextmanager
async def mongo_client(uri: str):
    client = AsyncIOMotorClient(uri, uuidRepresentation="standard", serverSelectionTimeoutMS=8000)
    try:
        # fuerza ping rápido al conectar
        await client.admin.command("ping")
        yield client
    finally:
        client.close()

async def ensure_indexes(coll):
    await coll.create_index("match_id", name="ux_match_id", unique=True)

# -------- Processing --------
async def process_record(coll, record: ConsumerRecord):
    try:
        raw = record.value.decode("utf-8")
        data = json.loads(raw)
        msg = MatchMsg(**data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.warning(f"[skip] JSON inválido offset={record.offset}: {e}")
        return
    except ValidationError as e:
        log.warning(f"[skip] Mensaje inválido offset={record.offset}: {e.errors()}")
        return

    try:
        res = await coll.update_one(
            {"match_id": msg.match_id},
            {"$setOnInsert": {"match_id": msg.match_id},
             "$set": {"timestamp": msg.timestamp, "raw": data}},
            upsert=True
        )
        log.info(
            f"[mongo] upsert match_id={msg.match_id} matched={res.matched_count}"
            f"matched={res.matched_count} modified={res.modified_count} upserted_id={res.upserted_id}"
        )
    except Exception as e:
        log.exception(f"[mongo] fallo escribiendo match_id={msg.match_id}: {e}")

# -------- Main loop --------
async def run():
    stop_event = asyncio.Event()

    def _graceful(*_):
        log.info("⏹️ Señal de parada recibida…")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _graceful)

    log.info(f"BOOTSTRAP={KAFKA_BOOTSTRAP} TOPIC={KAFKA_TOPIC} GROUP={KAFKA_GROUP_ID}")
    log.info(f"MONGO_URI={MONGO_URI} DB={MONGO_DB} COLL={MONGO_COLL}")
    backoff = 1

    while not stop_event.is_set():
        consumer = None
        try:
            async with mongo_client(MONGO_URI) as mcli:
                db = mcli[MONGO_DB]
                coll = db[MONGO_COLL]
                await ensure_indexes(coll)

                consumer = AIOKafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                    group_id=KAFKA_GROUP_ID,
                    enable_auto_commit=False,
                    auto_offset_reset=AUTO_OFFSET_RESET,
                    value_deserializer=lambda v: v
                )
                await consumer.start()
                log.info(f"✅ Consumiendo de '{KAFKA_TOPIC}' como grupo '{KAFKA_GROUP_ID}'")
                backoff = 1  # reset backoff

                while not stop_event.is_set():
                    try:
                        batch = await consumer.getmany(timeout_ms=1000, max_records=MAX_BATCH)
                    except Exception as e:
                        log.warning(f"[kafka] getmany falló: {e}; reiniciando ciclo")
                        break

                    tasks = []
                    for _, records in batch.items():
                        for rec in records:
                            tasks.append(process_record(coll, rec))

                    if tasks:
                        sem = asyncio.Semaphore(MAX_CONCURRENCY)
                        async def _guarded(coro):
                            async with sem:
                                await coro
                        await asyncio.gather(*[_guarded(t) for t in tasks])
                        await consumer.commit()
        except KafkaError as e:
            log.error(f"[kafka] error: {e}; reintentando en {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        except Exception as e:
            log.exception(f"[loop] error inesperado: {e}; reintentando en {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        finally:
            if consumer is not None:
                try:
                    await consumer.stop()
                except Exception:
                    pass

def main():
    asyncio.run(run())
