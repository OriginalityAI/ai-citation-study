import csv
from will_trigger_ai_overview import *

input_file = "queries_train.tsv"
output_file = "filtered_queries.txt"

def main():
    seen = set()
    selected = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            query = row[1].strip()
            if query in seen:
                continue
            if will_trigger_ai_overview_v1(query):
                selected.append(query)
                seen.add(query)

    with open(output_file, "w", encoding="utf-8") as f:
        for q in selected:
            f.write(q + "\n")

    print(f"✅ Saved {len(selected)} filtered queries to {output_file}")

if __name__ == "__main__":
    main()
