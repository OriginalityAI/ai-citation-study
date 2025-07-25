import csv
import html
import os
import time
import queue
import threading
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from collections import Counter
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# === Config ===
BATCH_SIZE = 10
SAMPLE_DIR = Path("samples/ymyl_29000/res_20250723_n100")
input_path = SAMPLE_DIR / "_urls_pool.csv"
scraped_path = SAMPLE_DIR / "_scraped.csv"
classified_path = SAMPLE_DIR / "__classified_urls.csv"
unclassified_path = SAMPLE_DIR / "__unclassified_urls.csv"
API_URL = "https://api.originality.ai/api/v3/scan/batch"

# === Globals ===
type_counter = Counter()
q = queue.Queue()
lock = threading.Lock()
load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")

VIDEO_DOMAINS = [
    "youtube.com", "m.youtube.com", "youtu.be", "vimeo.com", "tiktok.com",
    "dailymotion.com", "bilibili.com", "facebook.com/watch",
    "instagram.com/reel", "snapchat.com"
]

# === Helpers ===
def normalize_text(text):
    return ' '.join(text.split())

def classify_batch(batch, writer_cls):
    contents = [item['content'] for item in batch]
    urls = [item['url'] for item in batch]
    try:
        headers = {
            "X-OAI-API-KEY": API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "batches": contents,
            "title": "Ouroboros Batch",
            "check_ai": True,
            "check_plagiarism": False,
            "check_facts": False,
            "check_readability": False,
            "check_grammar": False
        }
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        for url, result in zip(urls, data['results']):
            ai_info = result.get("ai", {})
            classification = ai_info.get("classification", {})
            confidence_data = ai_info.get("confidence", {})

            if not classification or not confidence_data:
                print(f"[!] Incomplete result for {url}")
                continue

            is_ai = classification.get("AI", 0) > classification.get("Original", 0)
            label = "AI" if is_ai else "Human"
            confidence = confidence_data.get("AI" if is_ai else "Original", None) * 100

            if confidence is not None:
                writer_cls.writerow({
                    "url": url,
                    "ai_class": label,
                    "confidence": confidence
                })
                print(f"[✓] {label} ({confidence:.1f}%) — {url}")
    except Exception as e:
        print(f"[X] Batch classification failed: {e}")

# === Classifier Thread ===
def classifier_thread_fn():
    with open(classified_path, "a", newline="", encoding="utf-8") as f_cls:
        writer_cls = csv.DictWriter(f_cls, fieldnames=["url", "ai_class", "confidence"])
        if f_cls.tell() == 0:
            writer_cls.writeheader()

        batch = []
        while True:
            item = q.get()
            if item is None:
                break
            batch.append(item)

            if len(batch) == BATCH_SIZE:
                with lock:
                    classify_batch(batch, writer_cls)
                    f_cls.flush()
                batch.clear()

        # Final partial batch
        if batch:
            with lock:
                classify_batch(batch, writer_cls)
                f_cls.flush()

# === Load already processed URLs
def load_processed_urls():
    processed = set()
    for path in [scraped_path, classified_path, unclassified_path]:
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, usecols=["url"], dtype=str)
            processed.update(df["url"].dropna().str.strip().tolist())
        except Exception as e:
            print(f"[!] Failed to read {path}: {e}")
    return processed

# === Main Scraper ===
def run_scraper():
    df = pd.read_csv(input_path)
    total_urls = len(df)

    processed_urls = load_processed_urls()
    unprocessed_rows = [row for _, row in df.iterrows() if row["url"] not in processed_urls]
    pbar = tqdm(total=len(unprocessed_rows), desc="Scraping and queuing")

    with open(scraped_path, "a", newline="", encoding="utf-8") as f_scraped, \
         open(unclassified_path, "a", newline="", encoding="utf-8") as f_unclassified, \
         sync_playwright() as p:

        writer_scraped = csv.DictWriter(f_scraped, fieldnames=["url", "content"], quoting=csv.QUOTE_ALL)
        writer_unclassified = csv.DictWriter(f_unclassified, fieldnames=["url", "category"], quoting=csv.QUOTE_ALL)

        if f_scraped.tell() == 0:
            writer_scraped.writeheader()
        if f_unclassified.tell() == 0:
            writer_unclassified.writeheader()

        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        for row in unprocessed_rows:
            url = row["url"]
            row_type = None
            content = ""

            try:
                if any(domain in url.lower() for domain in VIDEO_DOMAINS):
                    row_type = "video"
                elif url.startswith("ftp:"):
                    row_type = "broken_link"
                elif url.lower().endswith(".pdf"):
                    row_type = "pdf"
                else:
                    response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    if response.status_code != 200:
                        raise requests.RequestException(f"HTTP {response.status_code}")

                    soup = BeautifulSoup(response.content, "html.parser")
                    text = soup.get_text(separator=' ', strip=True)
                    text = html.unescape(text.replace('\x00', ''))
                    text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    text = normalize_text(text[:5000])
                    word_count = len(text.split())
                    video_tags = soup.find_all(['video', 'iframe'])

                    if word_count < 50:
                        row_type = "text_too_short"
                    elif video_tags and word_count < 100:
                        row_type = "video"
                    else:
                        row_type = "OK"
                        content = text

            except Exception:
                row_type = "headless_needed"

            if row_type == "headless_needed":
                try:
                    page.goto(url, timeout=10000)
                    text = page.inner_text('body')[:5000]
                    text = html.unescape(text.replace('\x00', ''))
                    text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    text = normalize_text(text)
                    word_count = len(text.split())
                    video_tags = page.locator("video, iframe").count()

                    if word_count < 50:
                        row_type = "text_too_short"
                    elif video_tags > 0 and word_count < 100:
                        row_type = "video"
                    else:
                        row_type = "OK"
                        content = text

                except Exception as e:
                    print(f"[Headless ❌] {url} failed ({str(e).splitlines()[0]})")
                    row_type = "broken_link"

            type_counter[row_type] += 1

            if row_type == "OK":
                writer_scraped.writerow({"url": url, "content": content})
                with lock:
                    f_scraped.flush()
                q.put({"url": url, "content": content})
            else:
                writer_unclassified.writerow({"url": url, "category": row_type})
                with lock:
                    f_unclassified.flush()

            pbar.update(1)

        browser.close()
        pbar.close()

# === Entrypoint ===
if __name__ == "__main__":
    t = threading.Thread(target=classifier_thread_fn)
    t.start()

    run_scraper()

    q.put(None)
    t.join()

    print("\n✅ Finished!")
    print("Type Counts:")
    for k, v in type_counter.items():
        print(f"{k}: {v}")
