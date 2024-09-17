import json
import os

CACHE_FILE = "cached_news_ranking_result.json"


def cache_result_to_file(data, filename=CACHE_FILE):
    with open(filename, "w") as f:
        json.dump(data, f)


def load_cached_result(filename=CACHE_FILE):
    if os.path.exists(filename):
        with open(filename) as f:
            return json.load(f)
    return None
