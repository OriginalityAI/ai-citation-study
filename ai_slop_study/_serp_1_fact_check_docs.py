#!/usr/bin/env python3
# Fact-check SERP pages:
# - Reads ../samples/ymyl_29000/res_20250723_n100/__classified_urls.csv (url, ai_class, confidence)
# - Reads sibling _scraped.csv (url, content)
# - Calls fact checker (max 1 req/sec), writes JSONL line-by-line with resume + progress logs

import os
import csv
import json
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------- Paths (relative to this script) ----------
HERE = Path(__file__).resolve().parent
BASE = (HERE / "../samples/ymyl_29000/res_20250723_n100").resolve()
CLASSIFIED_CSV = BASE / "__classified_urls.csv"
SCRAPED_CSV    = BASE / "_scraped.csv"
OUTPUT_JSONL   = HERE / "serp_fc_results.jsonl"

# ---------- API / Runtime Config ----------
API_URL     = "http://54.152.224.7/api/v1/scan"
TIMEOUT_S   = 600          # 10 minutes per request
MAX_RETRIES = 100          # retry non-200 with 2,4,8,... backoff
MAX_SLEEP   = 300          # cap a single backoff sleep to 5 min
MIN_CONTENT_CHARS = 50     # consider pages with less as too short

# Rate limiting: max 1 request per second (global)
RATE_LIMIT_RPS = 1.0
MIN_INTERVAL = 1.0 / RATE_LIMIT_RPS
_last_call_ts = 0.0

def pace():
    """Ensure at most 1 request per second (across retries too)."""
    global _last_call_ts
    now = time.monotonic()
    wait = (_last_call_ts + MIN_INTERVAL) - now
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()

# ---------- Helpers ----------
def fmt_secs(s: float) -> str:
    s = int(round(s))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h: return f"{h}h {m}m {sec}s"
    if m: return f"{m}m {sec}s"
    return f"{sec}s"

def load_done_urls(path: Path) -> set[str]:
    """Treat rows with status_code==200 as done (so failures retry next run)."""
    done = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("status_code") == 200:
                    u = obj.get("url")
                    if isinstance(u, str) and u:
                        done.add(u)
    return done

def read_classified(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            u = (r.get("url") or "").strip()
            if not u:
                continue
            rows.append({
                "url": u,
                "ai_class": (r.get("ai_class") or "").strip(),
                "confidence": r.get("confidence")
            })
    return rows

def load_scraped_map(path: Path) -> dict[str, str]:
    m = {}
    if not path.exists():
        raise FileNotFoundError(f"Missing scraped file: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            u = (r.get("url") or "").strip()
            if not u:
                continue
            m[u] = (r.get("content") or "")
    return m

def call_checker(api_key: str, content: str) -> dict:
    """POST to the fact checker with 1 rps pacing + exponential backoff on non-200."""
    headers = {"Content-Type": "application/json", "X-OAI-API-KEY": api_key}
    payload = {"content": content}
    t0 = time.time()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pace()  # <- enforce 1 req/sec before each network call
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT_S)

            if resp.status_code == 200:
                out = {
                    "status_code": 200,
                    "elapsed_sec": round(time.time() - t0, 3),
                    "retries": attempt - 1,
                }
                try:
                    out["checker_response"] = resp.json()
                except Exception:
                    out["checker_raw"] = resp.text
                return out

            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, MAX_SLEEP))
                continue

            # last attempt (non-200)
            out = {
                "status_code": resp.status_code,
                "elapsed_sec": round(time.time() - t0, 3),
                "retries": attempt - 1,
            }
            try:
                out["checker_response"] = resp.json()
            except Exception:
                out["checker_raw"] = resp.text
            return out

        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, MAX_SLEEP))
                continue
            return {
                "status_code": None,
                "elapsed_sec": round(time.time() - t0, 3),
                "retries": attempt - 1,
                "error": repr(e),
            }

def main():
    load_dotenv()
    api_key = os.getenv("ORIGINALITY_API_KEY")
    if not api_key:
        raise RuntimeError("ORIGINALITY_API_KEY is missing in your .env")

    if not CLASSIFIED_CSV.exists():
        raise FileNotFoundError(f"Missing {CLASSIFIED_CSV}")
    if not SCRAPED_CSV.exists():
        raise FileNotFoundError(f"Missing {SCRAPED_CSV}")

    # Inputs
    rows = read_classified(CLASSIFIED_CSV)
    scraped_map = load_scraped_map(SCRAPED_CSV)

    # Dedup URLs (keep first occurrence)
    seen = set()
    deduped = []
    for r in rows:
        u = r["url"]
        if u in seen:
            continue
        seen.add(u)
        deduped.append(r)

    # Resume
    done = load_done_urls(OUTPUT_JSONL)
    to_run = [r for r in deduped if r["url"] not in done]
    total = len(to_run)
    if total == 0:
        print(f"All {len(deduped)} URLs already processed successfully. Nothing to do.")
        return

    start = time.time()
    processed = succeeded = failed = no_content = 0

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out_f:
        for r in to_run:
            processed += 1
            u = r["url"]
            ai_class = r.get("ai_class")
            conf = r.get("confidence")
            content = (scraped_map.get(u) or "").strip()

            if len(content) < MIN_CONTENT_CHARS:
                rec = {
                    "url": u, "ai_class": ai_class, "confidence": conf,
                    "status_code": None, "error": "no_content_or_too_short",
                    "content_chars": len(content),
                }
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_f.flush()
                no_content += 1
                elapsed = time.time() - start
                eta = (elapsed / processed) * (total - processed) if processed else 0.0
                print(f"({processed} / {total}) url={u} elapsed={fmt_secs(elapsed)} eta={fmt_secs(eta)} status=None (no_content)")
                continue

            result = call_checker(api_key, content)

            rec = {
                "url": u,
                "ai_class": ai_class,
                "confidence": conf,
                "content_chars": len(content),
                **result,  # status_code, elapsed_sec, retries, checker_response|checker_raw|error
            }
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_f.flush()

            status = result.get("status_code")
            if status == 200:
                succeeded += 1
            else:
                failed += 1

            elapsed = time.time() - start
            eta = (elapsed / processed) * (total - processed) if processed else 0.0
            print(f"({processed} / {total}) url={u} elapsed={fmt_secs(elapsed)} eta={fmt_secs(eta)} status={status}")

    elapsed_total = time.time() - start
    print("\nDone.")
    print(f"Queued   : {total}")
    print(f"Succeeded: {succeeded}")
    print(f"Failed   : {failed}")
    print(f"No text  : {no_content}")
    print(f"Time     : {fmt_secs(elapsed_total)}")
    print(f"Output   : {OUTPUT_JSONL.resolve()}")

if __name__ == "__main__":
    main()
