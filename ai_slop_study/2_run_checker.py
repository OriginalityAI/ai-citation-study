#!/usr/bin/env python3
"""
Run FEVER 1k binary sample through your fact checker API with:
- progress bar
- line-by-line JSONL output
- resume logic (skip already-processed fever_id)
- full fact-checker response saved

Requires:
  pip install python-dotenv tqdm requests
Inputs:
  - fever_binary_1k.csv  (columns: fever_id, claim, classification)
Outputs:
  - checker_results.jsonl (one JSON object per line)
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
MAX_RETRIES = 3
BACKOFF_BASE = 1.5
TIMEOUT = 30         # seconds
SEED = 42
# ----------------------------

def load_done_ids(path: Path) -> set[int]:
    """Collect already-written fever_ids for resume."""
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
                    # ignore malformed lines
                    continue
    return done

def try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        return None

def call_checker(api_key: str, claim: str) -> Dict[str, Any]:
    """
    Call the checker API with retries.
    Returns a dict containing:
      - status_code
      - elapsed_sec
      - checker_response (dict)  if JSON body
      - checker_raw      (str)   if non-JSON body
    """
    headers = {
        "Content-Type": "application/json",
        "X-OAI-API-KEY": api_key,
    }
    payload = {"content": claim}

    random.seed(SEED)
    attempt = 0
    start = time.time()
    last_err = None

    while attempt < MAX_RETRIES:
        try:
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            elapsed = time.time() - start

            out: Dict[str, Any] = {
                "status_code": resp.status_code,
                "elapsed_sec": round(elapsed, 3),
            }

            # Prefer exact JSON as returned by the API
            body_json = None
            # First: try .json() (more robust with correct headers)
            try:
                body_json = resp.json()
            except ValueError:
                # Fallback: try manual parse
                body_json = try_parse_json(resp.text)

            if isinstance(body_json, dict):
                out["checker_response"] = body_json  # full response JSON
            else:
                out["checker_raw"] = resp.text       # raw body if not JSON

            return out

        except requests.RequestException as e:
            last_err = repr(e)
            attempt += 1
            sleep_s = (BACKOFF_BASE ** attempt) + random.uniform(0, 0.25)
            time.sleep(sleep_s)

    return {
        "status_code": None,
        "elapsed_sec": round(time.time() - start, 3),
        "error": last_err or "unknown_error",
    }

def main():
    # Load env / API key
    load_dotenv()
    api_key = os.getenv("ORIGINALITY_API_KEY")
    if not api_key:
        raise RuntimeError("ORIGINALITY_API_KEY is missing. Add it to your .env.")

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV.resolve()}")

    # Resume set
    done_ids = load_done_ids(OUTPUT_JSONL)

    # Read all rows (for progress bar + ordering)
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
                "gold": r.get("classification"),  # "true"/"false"
            })

    # Filter those not yet processed
    to_run = [r for r in rows if r["fever_id"] not in done_ids]
    if not to_run:
        print(f"All {len(rows)} items already processed. Nothing to do.")
        return

    # Append results line-by-line
    with OUTPUT_JSONL.open("a", encoding="utf-8") as out_f:
        for r in tqdm(to_run, total=len(to_run), desc="Checking claims"):
            fid = r["fever_id"]
            claim = r["claim"]

            result = call_checker(api_key, claim)

            record = {
                "fever_id": fid,
                "claim": claim,
                "gold": r["gold"],
                # "api_url": API_URL,
                **result,  # includes status_code, elapsed_sec, and checker_response or checker_raw
            }

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    print(f"Done. Appended {len(to_run)} results to {OUTPUT_JSONL.resolve()}")

if __name__ == "__main__":
    main()
