import pandas as pd
import time
import csv
import html
from pathlib import Path
from playwright.sync_api import sync_playwright

# File paths
SAMPLE_DIR = Path("samples/v3_1000/res_20250627_n100")
input_path = SAMPLE_DIR / "_scraped_unclassified.csv"  # already filtered file
output_path = SAMPLE_DIR / "_rescued_error_scrapes.csv"  # new output

# Load only "error" rows
df = pd.read_csv(input_path)
error_urls = df[df["type"] == "error"]["url"].tolist()

# Prepare output CSV writer
with open(output_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["url", "type", "content"],
        quoting=csv.QUOTE_ALL
    )
    writer.writeheader()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        for i, url in enumerate(error_urls):
            # Skip FTP or PDF
            if url.startswith("ftp:"):
                print(f"[{i+1}] Skipping FTP: {url}")
                writer.writerow({"url": url, "type": "ftp", "content": ""})
                continue
            if url.lower().endswith(".pdf"):
                print(f"[{i+1}] Skipping PDF: {url}")
                writer.writerow({"url": url, "type": "pdf", "content": ""})
                continue

            try:
                print(f"[{i+1}] Visiting: {url}")
                page.goto(url, timeout=10000)  # 10s timeout
                text = page.inner_text('body')[:5000]

                # Clean up
                text = html.unescape(text.replace('\x00', ''))
                text = text.encode('utf-8', errors='ignore').decode('utf-8')

                # Type classification
                word_count = len(text.split())
                video_tags = page.locator("video, iframe").count()

                if word_count < 50:
                    row_type = "too_short"
                elif video_tags > 0 and word_count < 100:
                    row_type = "video"
                else:
                    row_type = "OK"

                writer.writerow({"url": url, "type": row_type, "content": text})
                print(f"[{i+1}] ✅ {row_type}")

            except Exception as e:
                print(f"[{i+1}] ❌ Failed: {url} ({str(e).splitlines()[0]})")
                writer.writerow({"url": url, "type": "error", "content": ""})

            time.sleep(1)  # Polite delay

        browser.close()
