import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import csv
import html

# Set paths
SAMPLE_DIR = Path("samples/v3_1000/res_20250627_n100")
input_path = SAMPLE_DIR / "_unclassified_urls.csv"
output_path = SAMPLE_DIR / "_scraped_unclassified.csv"

# Load the list of URLs
df = pd.read_csv(input_path)

# Prepare output CSV
with open(output_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["url", "type", "content"],
        quoting=csv.QUOTE_ALL  # Escapes commas, quotes, newlines
    )
    writer.writeheader()

    for i, row in df.iterrows():
        url = row["url"]

        # Skip FTP links
        if url.startswith("ftp:"):
            print(f"[{i+1}] Skipping FTP: {url}")
            writer.writerow({"url": url, "type": "ftp", "content": ""})
            continue

        # Skip PDFs
        if url.lower().endswith(".pdf"):
            print(f"[{i+1}] Skipping PDF: {url}")
            writer.writerow({"url": url, "type": "pdf", "content": ""})
            continue

        try:
            print(f"[{i+1}] Scraping: {url}")
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            status_code = response.status_code

            if status_code != 200:
                print(f"[{i+1}] HTTP error {status_code}: {url}")
                writer.writerow({"url": url, "type": str(status_code), "content": ""})
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract and sanitize text
            text = soup.get_text(separator=' ', strip=True)
            text = html.unescape(text.replace('\x00', ''))  # Remove nulls and decode HTML entities
            text = text.encode('utf-8', errors='ignore').decode('utf-8')  # Drop bad chars
            text = text[:5000]  # Limit to 5000 characters

            word_count = len(text.split())
            video_tags = soup.find_all(['video', 'iframe'])

            # Decide type
            if word_count < 50:
                row_type = "too_short"
            elif video_tags and word_count < 100:
                row_type = "video"
            else:
                row_type = "OK"

            # Write row
            writer.writerow({"url": url, "type": row_type, "content": text})
            time.sleep(1)  # Polite delay

        except requests.RequestException as e:
            code = getattr(e.response, 'status_code', 'error')
            print(f"[{i+1}] Failed: {url} ({code})")
            writer.writerow({"url": url, "type": str(code), "content": ""})
