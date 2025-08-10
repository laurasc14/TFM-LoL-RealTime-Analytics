import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from services.kafka_consumer.consumer import main as consumer_main

if __name__ == "__main__":
    consumer_main()
