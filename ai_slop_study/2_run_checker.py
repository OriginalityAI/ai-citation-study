#!/usr/bin/env python3
# Minimal runner: retry non-200 up to 100 times with 2,4,8,... seconds backoff.

import os, csv, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

INPUT_CSV = Path("_claim_datasets/averitec_3018.csv")
OUTPUT_JSONL = Path("_results/averitec_3018/averitec_checker_results.jsonl")

ID_LABEL = 'averitec_id'
API_URL = "http://54.152.224.7/api/v1/scan"
TIMEOUT = 300              # seconds
MAX_RETRIES = 20           # total attempts per claim
MAX_SLEEP = 600            # cap any single sleep (seconds); tweak if you want

def load_done_ids(path: Path) -> set:
    """Only consider rows with status_code==200 as 'done' (so failures get retried next run)."""
    done = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("status_code") == 200 and isinstance(obj.get(ID_LABEL), int):
                    done.add(obj[ID_LABEL])
    return done

def call_checker(api_key: str, claim: str):
    headers = {"Content-Type": "application/json", "X-OAI-API-KEY": api_key}
    payload = {"content": claim}
    t0 = time.time()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(2) # limit request rate
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            print(f'attempt={attempt}', f'status={resp.status_code}', claim)
            if resp.status_code == 200:
                out = {"status_code": 200, "elapsed_sec": round(time.time() - t0, 3), "retries": attempt - 1}
                try:
                    out["checker_response"] = resp.json()
                except Exception:
                    out["checker_raw"] = resp.text
                return out
            # not 200 -> backoff and retry (unless last attempt)
            if attempt < MAX_RETRIES:
                sleep_s = min(2 ** attempt, MAX_SLEEP)  # 2,4,8,...
                time.sleep(sleep_s)
                continue
            # last attempt: return what we got
            out = {"status_code": resp.status_code, "elapsed_sec": round(time.time() - t0, 3), "retries": attempt - 1}
            try:
                out["checker_response"] = resp.json()
            except Exception:
                out["checker_raw"] = resp.text
            return out
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                sleep_s = min(2 ** attempt, MAX_SLEEP)
                time.sleep(sleep_s)
                continue
            return {"status_code": None, "elapsed_sec": round(time.time() - t0, 3), "retries": attempt - 1, "error": repr(e)}

def main():
    load_dotenv()
    api_key = os.getenv("ORIGINALITY_API_KEY")
    if not api_key:
        raise RuntimeError("ORIGINALITY_API_KEY is missing in .env")

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV.resolve()}")

    done_ids = load_done_ids(OUTPUT_JSONL)

    # Load all rows
    rows = []
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            fid = row[ID_LABEL]
            rows.append({ID_LABEL: fid, "claim": row["claim"], "gold": row.get("classification")})

    # Filter to those not yet successfully processed
    to_run = [r for r in rows if r[ID_LABEL] not in done_ids]
    total = len(to_run)
    if total == 0:
        print(f"All {len(rows)} items already processed successfully. Nothing to do.")
        return

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out_f:
        for idx, r in enumerate(to_run, start=1):
            result = call_checker(api_key, r["claim"])
            status = result.get("status_code")
            print(f"({idx} / {total}) fever_id={r[ID_LABEL]} status={status}")
            record = {ID_LABEL: r[ID_LABEL], "claim": r["claim"], "gold": r["gold"], **result}
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done. Appended {total} results to {OUTPUT_JSONL.resolve()}")

if __name__ == "__main__":
    main()
