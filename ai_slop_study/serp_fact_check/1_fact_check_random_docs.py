#!/usr/bin/env python3
# Fact-check SERP pages:
# - Reads ../samples/ymyl_29000/res_20250723_n100/__classified_urls.csv (url, ai_class, confidence)
# - Reads sibling _scraped.csv (url, content)
# - Calls fact checker (max 1 req/sec), writes JSONL line-by-line with resume + progress logs

import os
import csv
import json
import time
import random
import logging
from pathlib import Path
from typing import Set, List, Dict, Any

import requests
from dotenv import load_dotenv

# ---------- Paths (relative to this script) ----------
HERE = Path(__file__).resolve().parent
BASE = (HERE / "../../samples/ymyl_29000/res_20250723_n100").resolve()
CLASSIFIED_CSV = BASE / "__classified_urls.csv"
SCRAPED_CSV    = BASE / "_scraped.csv"
OUTPUT_JSONL   = HERE / "fact_checked_docs.jsonl"
LOG_PATH       = HERE / "serp_fc.log"

# ---------- API / Runtime Config ----------
API_URL     = "http://54.152.224.7/api/v1/scan"
TIMEOUT_S   = 120          # 2 minutes per request
MAX_RETRIES = 1            # retry non-200 with 2,4,8,... backoff
MAX_SLEEP   = 300          # cap a single backoff sleep to 5 min
MIN_CONTENT_CHARS = 50     # consider pages with less as too short

# Rate limiting: max 1 request per second (global)
RATE_LIMIT_RPS = 1.0
MIN_INTERVAL = 1.0 / RATE_LIMIT_RPS
_last_call_ts = 0.0

# ---------- Logging ----------
LOGGER = logging.getLogger("serp_fc")

def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # Clear existing handlers if re-run in a notebook/shell
    LOGGER.handlers.clear()
    LOGGER.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    LOGGER.addHandler(sh)

    if os.getenv("LOG_TO_FILE", "1") not in {"0", "false", "False"}:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        LOGGER.addHandler(fh)

    LOGGER.info("Logger initialized (level=%s, to_file=%s)", level_name, os.getenv("LOG_TO_FILE", "1"))
    LOGGER.debug("Process PID=%s, CWD=%s", os.getpid(), os.getcwd())

def human_bytes(n: int) -> str:
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < step:
            return f"{n:.1f}{unit}"
        n /= step
    return f"{n:.1f}PB"

def file_info(p: Path) -> str:
    try:
        size = p.stat().st_size
        return f"{p} ({human_bytes(size)})"
    except Exception:
        return f"{p} (size=?))"

def pace():
    """Ensure at most 1 request per second (across retries too)."""
    global _last_call_ts
    now = time.monotonic()
    wait = (_last_call_ts + MIN_INTERVAL) - now
    if wait > 0:
        LOGGER.debug("Rate limit: sleeping %.3fs to honor %.2f rps", wait, RATE_LIMIT_RPS)
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

def load_done_urls(path: Path) -> Set[str]:
    """Treat rows with status_code==200 as done (so failures retry next run)."""
    LOGGER.info("Resume scan: parsing previously completed URLs from %s", file_info(path))
    done: Set[str] = set()
    errors = 0
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                try:
                    obj = json.loads(line)
                    if obj.get("status_code") == 200:
                        u = obj.get("url")
                        if isinstance(u, str) and u:
                            done.add(u)
                except Exception:
                    errors += 1
                    if errors <= 3:
                        LOGGER.debug("Resume scan JSONL parse error at line %d (will ignore): %.120r", i, line)
    LOGGER.info("Resume scan: found %d completed URLs%s",
                len(done),
                "" if errors == 0 else f" (ignored {errors} malformed lines)")
    return done

def read_classified(path: Path) -> List[Dict[str, Any]]:
    LOGGER.info("Loading classified CSV: %s", file_info(path))
    t0 = time.time()
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            u = (r.get("url") or "").strip()
            if not u:
                continue
            ai_class = r.get("ai_class")
            if ai_class == "AI": # ONLY AI DOCUMENTS
                rows.append({
                    "url": u,
                    "ai_class": ai_class,
                    "confidence": r.get("confidence")
                })
    LOGGER.info("Loaded %d classified rows in %s", len(rows), fmt_secs(time.time() - t0))
    return rows

def load_scraped_map(path: Path) -> Dict[str, str]:
    LOGGER.info("Loading scraped content CSV (this may be large): %s", file_info(path))
    t0 = time.time()
    m: Dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"Missing scraped file: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            u = (r.get("url") or "").strip()
            if not u:
                continue
            m[u] = (r.get("content") or "")
    LOGGER.info("Built scraped map of %d URLs in %s", len(m), fmt_secs(time.time() - t0))
    return m

def call_checker(api_key: str, content: str) -> Dict[str, Any]:
    """POST to the fact checker with 1 rps pacing + exponential backoff on non-200."""
    headers = {"Content-Type": "application/json", "X-OAI-API-KEY": api_key}
    payload = {"content": content}
    t0 = time.time()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt == 1:
                LOGGER.debug("Checker: attempt %d (content_chars=%d, timeout=%ss)", attempt, len(content), TIMEOUT_S)
            else:
                LOGGER.warning("Checker: retry attempt %d", attempt)

            pace()  # <- enforce 1 req/sec before each network call
            resp = requests.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT_S)

            if resp.status_code == 200:
                elapsed = round(time.time() - t0, 3)
                LOGGER.debug("Checker: 200 OK in %ss (attempts=%d)", elapsed, attempt)
                out: Dict[str, Any] = {
                    "status_code": 200,
                    "elapsed_sec": elapsed,
                    "retries": attempt - 1,
                }
                try:
                    out["checker_response"] = resp.json()
                except Exception:
                    out["checker_raw"] = resp.text
                return out

            # non-200
            LOGGER.warning("Checker: non-200 status=%s on attempt %d", resp.status_code, attempt)
            if attempt < MAX_RETRIES:
                sleep_s = min(2 ** attempt, MAX_SLEEP)
                LOGGER.warning("Checker: backing off for %ss (cap=%ss)", sleep_s, MAX_SLEEP)
                time.sleep(sleep_s)
                continue

            # last attempt (non-200)
            elapsed = round(time.time() - t0, 3)
            LOGGER.error("Checker: giving up after %d attempts (status=%s, elapsed=%ss)",
                         attempt, resp.status_code, elapsed)
            out = {
                "status_code": resp.status_code,
                "elapsed_sec": elapsed,
                "retries": attempt - 1,
            }
            try:
                out["checker_response"] = resp.json()
            except Exception:
                out["checker_raw"] = resp.text
            return out

        except requests.RequestException as e:
            LOGGER.warning("Checker: request exception on attempt %d: %r", attempt, e)
            if attempt < MAX_RETRIES:
                sleep_s = min(2 ** attempt, MAX_SLEEP)
                LOGGER.warning("Checker: backing off for %ss (cap=%ss)", sleep_s, MAX_SLEEP)
                time.sleep(sleep_s)
                continue
            elapsed = round(time.time() - t0, 3)
            LOGGER.error("Checker: final failure after %d attempts (elapsed=%ss)", attempt, elapsed)
            return {
                "status_code": None,
                "elapsed_sec": elapsed,
                "retries": attempt - 1,
                "error": repr(e),
            }

def main():
    setup_logging()

    LOGGER.info("Loading environment (.env)")
    load_dotenv()
    api_key = os.getenv("ORIGINALITY_API_KEY")
    if not api_key:
        LOGGER.critical("ORIGINALITY_API_KEY is missing in your .env")
        raise RuntimeError("ORIGINALITY_API_KEY is missing in your .env")

    LOGGER.info("Base directory: %s", BASE)
    if not CLASSIFIED_CSV.exists():
        LOGGER.critical("Missing %s", CLASSIFIED_CSV)
        raise FileNotFoundError(f"Missing {CLASSIFIED_CSV}")
    if not SCRAPED_CSV.exists():
        LOGGER.critical("Missing %s", SCRAPED_CSV)
        raise FileNotFoundError(f"Missing {SCRAPED_CSV}")

    # Inputs (long-ish operations)
    rows = read_classified(CLASSIFIED_CSV)
    scraped_map = load_scraped_map(SCRAPED_CSV)

    # Dedup URLs (keep first occurrence)
    LOGGER.info("Deduplicating URLs (keep first occurrence)")
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for r in rows:
        u = r["url"]
        if u in seen:
            continue
        seen.add(u)
        deduped.append(r)
    LOGGER.info("Deduped: %d -> %d unique URLs", len(rows), len(deduped))

    # Resume
    done = load_done_urls(OUTPUT_JSONL)
    to_run = [r for r in deduped if r["url"] not in done]
    random.shuffle(to_run)
    
    total = len(to_run)
    LOGGER.info("Resume state: %d already done, %d queued for processing", len(done), total)
    if total == 0:
        LOGGER.info("All %d URLs already processed successfully. Nothing to do.", len(deduped))
        print(f"All {len(deduped)} URLs already processed successfully. Nothing to do.")
        return

    LOGGER.info("Opening output JSONL for append: %s", OUTPUT_JSONL)
    start = time.time()
    processed = succeeded = failed = no_content = 0

    with OUTPUT_JSONL.open("a", encoding="utf-8") as out_f:
        for idx, r in enumerate(to_run, 1):
            processed += 1
            u = r["url"]
            ai_class = r.get("ai_class")
            conf = r.get("confidence")
            content = (scraped_map.get(u) or "").strip()
            clen = len(content)

            if clen < MIN_CONTENT_CHARS:
                LOGGER.debug("Skipping (no/short content, %d chars): %s", clen, u)
                rec = {
                    "url": u, "ai_class": ai_class, "confidence": conf,
                    "status_code": None, "error": "no_content_or_too_short",
                    "content_chars": clen,
                }
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_f.flush()
                no_content += 1
            else:
                LOGGER.info("(%d/%d) Submitting to checker | url=%s | chars=%d | class=%s",
                            idx, total, u, clen, ai_class or "")
                result = call_checker(api_key, content)

                rec = {
                    "url": u,
                    "ai_class": ai_class,
                    "confidence": conf,
                    "content_chars": clen,
                    **result,  # status_code, elapsed_sec, retries, checker_response|checker_raw|error
                }
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_f.flush()

                status = result.get("status_code")
                if status == 200:
                    succeeded += 1
                    LOGGER.info("(%d/%d) Completed: 200 OK | url=%s | elapsed=%ss | retries=%d",
                                idx, total, u, result.get("elapsed_sec"), result.get("retries"))
                else:
                    failed += 1
                    LOGGER.warning("(%d/%d) Completed: status=%s | url=%s | elapsed=%ss | retries=%d",
                                   idx, total, status, u, result.get("elapsed_sec"), result.get("retries"))

            # Progress + ETA
            elapsed = time.time() - start
            eta = (elapsed / processed) * (total - processed) if processed else 0.0
            LOGGER.info("Progress: %d/%d | ok=%d, fail=%d, no_text=%d | elapsed=%s | eta=%s",
                        processed, total, succeeded, failed, no_content, fmt_secs(elapsed), fmt_secs(eta))

    elapsed_total = time.time() - start
    LOGGER.info("Done. Queued=%d | Succeeded=%d | Failed=%d | No text=%d | Time=%s | Output=%s",
                total, succeeded, failed, no_content, fmt_secs(elapsed_total), OUTPUT_JSONL.resolve())
    print("\nDone.")
    print(f"Queued   : {total}")
    print(f"Succeeded: {succeeded}")
    print(f"Failed   : {failed}")
    print(f"No text  : {no_content}")
    print(f"Time     : {fmt_secs(elapsed_total)}")
    print(f"Output   : {OUTPUT_JSONL.resolve()}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last-chance visibility if something unexpected happens early
        try:
            LOGGER.exception("Fatal error: %r", e)
        except Exception:
            # LOGGER not set up yet
            print(f"[FATAL] {e!r}")
        raise
