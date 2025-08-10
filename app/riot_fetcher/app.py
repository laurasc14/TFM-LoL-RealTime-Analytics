import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from services.riot_fetcher.fetcher import main as fetcher_main

if __name__ == "__main__":
    fetcher_main()
