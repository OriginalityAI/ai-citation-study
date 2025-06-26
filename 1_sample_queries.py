import os
import csv
import random
from wtao_filters import will_trigger_ai_overview_map

random.seed(42)

SAMPLE_SIZE = 50
OVERVIEW_TRIGGER_VERSION = 'v2'

will_trigger_ai_overview = will_trigger_ai_overview_map[OVERVIEW_TRIGGER_VERSION]

DATASET_PATH = "datasets/ms-marco-web-search-queries.tsv"
OUTPUT_PATH = f"samples/{OVERVIEW_TRIGGER_VERSION}_{SAMPLE_SIZE}/queries_{OVERVIEW_TRIGGER_VERSION}_{SAMPLE_SIZE}.csv"

def main():
    seen = set()
    selected = []

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            query_id = row[0].strip()
            query = row[1].strip()
            if query in seen:
                continue
            if will_trigger_ai_overview(query):
                selected.append((query_id, query))
                seen.add(query)
    
    # Down sample to specified amount of queries
    selected = random.sample(selected, min(SAMPLE_SIZE, len(selected)))
    print(f"🔍 {len(selected)} sampled from {len(seen)} filtered queries")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query_id", "query_text"])  # CSV header

        for row in selected:
            writer.writerow(row)

    print(f"✅ Saved {len(selected)} filtered queries to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
