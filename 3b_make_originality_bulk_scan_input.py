import pandas as pd
from pathlib import Path
from urllib.parse import urlparse

# === Configuration ===
CSV_PATH = Path("samples/v3_1000/res_20250627_n100/_url_counts.csv")
OUTPUT_DIR = CSV_PATH.parent
BATCH_SIZE = 1000

def is_youtube_url(url):
    domain = urlparse(url).netloc
    return "youtube.com" in domain or "youtu.be" in domain

def main():
    df = pd.read_csv(CSV_PATH)

    # Remove YouTube links
    filtered = df[~df["url"].apply(is_youtube_url)]
    urls = filtered["url"].dropna().tolist()

    total = len(urls)
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"Total non-YouTube URLs: {total}")
    print(f"Splitting into {batch_count} batches of {BATCH_SIZE}...")

    for i in range(batch_count):
        batch_urls = urls[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        batch_file = OUTPUT_DIR / f"_urls_batch_{i+1}.csv"
        with open(batch_file, "w", encoding="utf-8") as f:
            f.write("\n".join(batch_urls))
        print(f"✔ Wrote {len(batch_urls)} URLs to {batch_file.name}")

    print("✅ Done.")

if __name__ == "__main__":
    main()
