import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import csv
import html
from collections import Counter
from playwright.sync_api import sync_playwright

# Set paths
SAMPLE_DIR = Path("samples/ymyl_1000/res_20250718_n100")
input_path = SAMPLE_DIR / "_urls_pool.csv"
ok_path = SAMPLE_DIR / "_scraped.csv"
unclassified_path = SAMPLE_DIR / "__unclassified_urls.csv"

# Load URLs
df = pd.read_csv(input_path)
results = []
type_counter = Counter()

# Normalize text
def normalize_text(text):
    return ' '.join(text.split())

# Known video domains
VIDEO_DOMAINS = [
    "youtube.com", "m.youtube.com", "youtu.be",
    "vimeo.com", "tiktok.com", "dailymotion.com",
    "bilibili.com", "facebook.com/watch",
    "instagram.com/reel", "snapchat.com"
]

# First pass (requests)
for i, row in df.iterrows():
    url = row["url"]

    if any(domain in url.lower() for domain in VIDEO_DOMAINS):
        row_type = "video"
        content = ""
    elif url.startswith("ftp:"):
        row_type = "broken_link"
        content = ""
    elif url.lower().endswith(".pdf"):
        row_type = "pdf"
        content = ""
    else:
        try:
            print(f"[{i+1}] Scraping (requests): {url}")
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

        except Exception as e:
            row_type = "headless_needed"
            content = ""

    results.append({"url": url, "type": row_type, "content": content})
    type_counter[row_type] += 1
    print(f"[{i+1}] {url} -> {row_type}")
    time.sleep(1)

# Retry headless
with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()

    for i, row in enumerate(results):
        if row["type"] != "headless_needed":
            continue

        url = row["url"]
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

            row["type"] = row_type
            row["content"] = text
            type_counter["headless_needed"] -= 1
            type_counter[row_type] += 1
            print(f"[Headless] ✅ {url} -> {row_type}")

        except Exception as e:
            row["type"] = "broken_link"
            row["content"] = ""
            type_counter["headless_needed"] -= 1
            type_counter["broken_link"] += 1
            print(f"[Headless] ❌ Failed: {url} ({str(e).splitlines()[0]})")

        time.sleep(1)

    browser.close()

# Save results to separate files
with open(ok_path, mode="w", newline="", encoding="utf-8") as f_ok, \
     open(unclassified_path, mode="w", newline="", encoding="utf-8") as f_unclassified:

    writer_ok = csv.DictWriter(f_ok, fieldnames=["url", "content"], quoting=csv.QUOTE_ALL)
    writer_unclassified = csv.DictWriter(f_unclassified, fieldnames=["url", "category"], quoting=csv.QUOTE_ALL)

    writer_ok.writeheader()
    writer_unclassified.writeheader()

    for row in results:
        if row["type"] == "OK":
            writer_ok.writerow({"url": row["url"], "content": row["content"]})
        else:
            writer_unclassified.writerow({"url": row["url"], "category": row["type"]})

# Print summary
print("\nType Counts:")
for k, v in type_counter.items():
    print(f"{k}: {v}")
