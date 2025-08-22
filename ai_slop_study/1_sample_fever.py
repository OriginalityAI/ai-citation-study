#!/usr/bin/env python3
import json
import csv
import random
from pathlib import Path

INFILE = Path("shared_task_dev.jsonl")
OUTFILE = Path("fever_binary_1k.csv")
SEED = 42          # change if you want a different random sample
N_PER_CLASS = 500  # 500 true + 500 false = 1000 total

# Map FEVER -> binary labels we want
MAP = {
    "SUPPORTS": "true",
    "REFUTES": "false",
}

def main():
    if not INFILE.exists():
        raise FileNotFoundError(f"Couldn't find {INFILE.resolve()}")

    supports = []
    refutes = []

    # Read JSONL line-by-line
    with INFILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            label = obj.get("label", "").upper()
            if label in MAP:
                rec = {
                    "fever_id": obj.get("id"),
                    "claim": obj.get("claim", "").strip(),
                    "classification": MAP[label],
                }
                if label == "SUPPORTS":
                    supports.append(rec)
                elif label == "REFUTES":
                    refutes.append(rec)

    # Sanity checks
    if len(supports) < N_PER_CLASS or len(refutes) < N_PER_CLASS:
        raise ValueError(
            f"Not enough examples to sample {N_PER_CLASS} per class. "
            f"Found supports={len(supports)}, refutes={len(refutes)}"
        )

    # Reproducible random sample
    random.seed(SEED)
    supports_sample = random.sample(supports, N_PER_CLASS)
    refutes_sample = random.sample(refutes, N_PER_CLASS)

    sample = supports_sample + refutes_sample
    random.shuffle(sample)  # shuffle final mix

    # Write CSV
    with OUTFILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["fever_id", "claim", "classification"])
        writer.writeheader()
        writer.writerows(sample)

    print(f"Wrote {len(sample)} rows to {OUTFILE.resolve()}")

if __name__ == "__main__":
    main()
