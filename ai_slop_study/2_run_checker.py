#!/usr/bin/env python3
"""
Run FEVER 1k binary sample through your fact checker API with:
- progress bar
- line-by-line JSONL output
- resume logic (skip already-processed fever_id)
- full fact-checker response saved
- retries on non-200 with exponential backoff

Requires:
  pip install python-dotenv tqdm requests
"""

import os
import csv
import json
import time
import random
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# ---------- Config ----------
INPUT_CSV = Path("fever_binary_1k.csv")
OUTPUT_JSONL = Path("checker_results.jsonl")

API_URL = "http://54.152.224.7/api/v1/scan"
MAX_RETRIES = 5            # total attempts = MAX_RETRIES (including first try)
BACKOFF_BASE = 1.7         # exponential base
BACKOFF_JITTER = 0.4       # uniform(0, BACKOFF_JITTER) seconds
MAX_BACKOFF = 60           # cap sleep seconds
TIMEOUT = 30               # per-request timeout
SEED = 42
# ----------------------------

def load_done_ids(path: Path) -> set[int]:
    done = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    fid = obj.get("fever_id")
                    if isinstance(fid, int):
                        done.add(fid)
                except Exception:
                    continue
    return done

def try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        return None

def _sleep_with_backoff(attempt: int, retry_after: Optional[str] = None):
    # If server told us how long to wait, respect it
    if retry_after:
        try:
            secs = float(retry_after)
            time.sleep(min(secs, MAX_BACKOFF))
            return
        except Exception:
            pass
    # Otherwise exponential backoff + jitter
    base = (BACKOFF_BASE ** max(1, attempt))
    jitter = random.uniform(0, BACKOFF_JITTER)
    time.sleep(min(base + jitter, MAX_BACKOFF))

def call_checker(api_key: str, claim: str) -> Dict[str, Any]:
    """
    Call the checker API with retries.
    Retries on ANY non-200 or network error using exponential backoff.
    Returns:
      - status_code (int or None)
      - elapsed_sec (float)
      - retries (int)
      - checker_response (dict) if JSON
      - checker_raw (str) if non-JSON
      - error (str) on total failure
    """
    headers = {
        "Content-Type": "application/json",
        "X-OAI-API-KEY": api_key,
    }
    payload = {"content": claim}

    random.seed(SEED)
    start = time.time()
    last_status = None
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            last_status = resp.status_code

            if resp.status_code == 200:
                out: Dict[str, Any] = {
                    "status_code": resp.status_code,
                    "elapsed_sec": round(time.time() - start, 3),
                    "retries": attempt - 1,
                }
                try:
                    out["checker_response"] = resp.json()
                except ValueError:
                    out["checker_raw"] = resp.text
                return out

            # Non-200: backoff then retry (unless this was the last attempt)
            if attempt < MAX_RETRIES:
                _sleep_with_backoff(attempt, resp.headers.get("Retry-After"))
                continue

            # Give back the last non-200
            out: Dict[str, Any] = {
                "status_code": resp.status_code,
                "elapsed_sec": round(time.time() - start, 3),
                "retries": attempt - 1,
            }
            try:
                out["checker_response"] = resp.json()
            except ValueError:
                out["checker_raw"] = resp.text
            return out

        except requests.RequestException as e:
            last_err = repr(e)
            if attempt < MAX_RETRIES:
                _sleep_with_backoff(attempt)
                continue
            return {
                "status_code": None,
                "elapsed_sec": round(time.time() - start, 3),
                "retries": attempt - 1,
                "error": last_err or "unknown_error",
            }

def main():
    load_dotenv()
    api_key = os.getenv("ORIGINALITY_API_KEY")
    if not api_key:
        raise RuntimeError("ORIGINALITY_API_KEY is missing. Add it to your .env.")

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV.resolve()}")

    done_ids = load_done_ids(OUTPUT_JSONL)

    rows = []
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                fid = int(r["fever_id"])
            except Exception:
                continue
            rows.append({
                "fever_id": fid,
                "claim": r["claim"],
                "gold": r.get("classification"),
            })

    to_run = [r for r in rows if r["fever_id"] not in done_ids]
    if not to_run:
        print(f"All {len(rows)} items already processed. Nothing to do.")
        return

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out_f:
        for r in tqdm(to_run, total=len(to_run), desc="Checking claims"):
            result = call_checker(api_key, r["claim"])
            record = {
                "fever_id": r["fever_id"],
                "claim": r["claim"],
                "gold": r["gold"],
                **result,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done. Appended {len(to_run)} results to {OUTPUT_JSONL.resolve()}")

if __name__ == "__main__":
    main()
