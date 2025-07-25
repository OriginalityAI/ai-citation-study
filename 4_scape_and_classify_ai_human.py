import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import csv
import html
import os
from collections import Counter
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# === Setup ===
load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")
SAMPLE_DIR = Path("samples/ymyl_29000/res_20250723_n100")
input_path = SAMPLE_DIR / "_urls_pool.csv"
scraped_path = SAMPLE_DIR / "_scraped.csv"
classified_path = SAMPLE_DIR / "__classified_urls.csv"
unclassified_path = SAMPLE_DIR / "__unclassified_urls.csv"

df = pd.read_csv(input_path)
VIDEO_DOMAINS = [
    "youtube.com", "m.youtube.com", "youtu.be",
    "vimeo.com", "tiktok.com", "dailymotion.com",
    "bilibili.com", "facebook.com/watch",
    "instagram.com/reel", "snapchat.com"
]

type_counter = Counter()
processed = 0

# === Normalization ===
def normalize_text(text):
    return ' '.join(text.split())

def classify_content(url, content, writer_cls):
    if not isinstance(content, str) or content.strip() == "":
        print(f"[!] ⏩ Skipping empty content for: {url}")
        return

    payload = {
        "title": "Ouroboros API Scan",
        "check_ai": True,
        "check_plagiarism": False,
        "check_facts": False,
        "check_readability": False,
        "check_grammar": False,
        "check_contentOptimizer": False,
        "aiModelVersion": "lite",
        "storeScan": False,
        "content": content
    }
    headers = {
        "X-OAI-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post("https://api.originality.ai/api/v3/scan",
                                 json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        ai_info = data.get("results", {}).get("ai", {})
        classification = ai_info.get("classification", {})
        confidence_data = ai_info.get("confidence", {})

        if not classification or not confidence_data:
            print(f"[!] Incomplete result for {url}")
            return

        is_ai = classification.get("AI", 0) > classification.get("Original", 0)
        label = "AI" if is_ai else "Human"
        confidence = confidence_data.get("AI" if is_ai else "Original", None) * 100
        if confidence is None:
            print(f"[!] Missing confidence score for {url}")
            return

        writer_cls.writerow({
            "url": url,
            "ai_class": label,
            "confidence": confidence
        })
        print(f"[✓] {label} ({confidence:.1f}%) — {url}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            print(f"[!] 422 Unprocessable Entity for {url} — skipping.")
        else:
            print(f"[X] HTTP error for {url}: {e}")
    except Exception as e:
        print(f"[X] General error scanning {url}: {e}")

# === Scrape Pass ===
with open(scraped_path, "w", newline="", encoding="utf-8") as f_scraped, \
     open(unclassified_path, "w", newline="", encoding="utf-8") as f_unclassified, \
     open(classified_path, "w", newline="", encoding="utf-8") as f_classified, \
     sync_playwright() as p:

    writer_scraped = csv.DictWriter(f_scraped, fieldnames=["url", "content"], quoting=csv.QUOTE_ALL)
    writer_unclassified = csv.DictWriter(f_unclassified, fieldnames=["url", "category"], quoting=csv.QUOTE_ALL)
    writer_classified = csv.DictWriter(f_classified, fieldnames=["url", "ai_class", "confidence"])

    writer_scraped.writeheader()
    writer_unclassified.writeheader()
    writer_classified.writeheader()

    browser = p.firefox.launch(headless=True)
    page = browser.new_page()

    for i, row in df.iterrows():
        url = row["url"]
        print(f"[{i+1}] Scraping: {url}")

        row_type = None
        content = ""

        if any(domain in url.lower() for domain in VIDEO_DOMAINS):
            row_type = "video"
        elif url.startswith("ftp:"):
            row_type = "broken_link"
        elif url.lower().endswith(".pdf"):
            row_type = "pdf"
        else:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    raise requests.RequestException(f"HTTP {resp.status_code}")
                soup = BeautifulSoup(resp.content, "html.parser")
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

        # Headless fallback
        if row_type == "headless_needed":
            try:
                print(f"[Headless] Visiting: {url}")
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
                print(f"[Headless ❌] Failed: {url} ({str(e).splitlines()[0]})")
                row_type = "broken_link"

        type_counter[row_type] += 1

        if row_type == "OK":
            writer_scraped.writerow({"url": url, "content": content})
            classify_content(url, content, writer_classified)
        else:
            writer_unclassified.writerow({"url": url, "category": row_type})

        processed += 1
        if processed % 10 == 0:
            f_scraped.flush()
            f_unclassified.flush()
            f_classified.flush()
            print(f"[Flush] Saved after {processed} entries")

        time.sleep(1)

    browser.close()

# === Summary ===
print("\nType Counts:")
for k, v in type_counter.items():
    print(f"{k}: {v}")
