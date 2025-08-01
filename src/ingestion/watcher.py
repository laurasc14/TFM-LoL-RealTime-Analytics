import time, os, glob, asyncio
from replay_topic import main as replay_main

WATCH_DIR = "/app/data/historial/"
seen = set()

while True:
    files = set(glob.glob(os.path.join(WATCH_DIR, "*.jsonl")))
    new_files = files - seen
    if new_files:
        print(f"Detected new files: {new_files}, sending to Kafka...")
        asyncio.run(replay_main(pattern=os.path.join(WATCH_DIR, "*.jsonl")))
        seen |= new_files
    time.sleep(10)
