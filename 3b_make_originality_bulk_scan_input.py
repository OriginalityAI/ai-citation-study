import pandas as pd
from pathlib import Path
from urllib.parse import urlparse

CSV_PATH = Path("samples/v3_1000/res_20250627_n100/_url_counts.csv")
OUTPUT_CSV = CSV_PATH.parent / "_urls_no_youtube.csv"

def is_youtube_url(url):
    domain = urlparse(url).netloc
    return "youtube.com" in domain or "youtu.be" in domain

def main():
    df = pd.read_csv(CSV_PATH)
    
    # Filter out YouTube links
    filtered = df[~df["url"].apply(is_youtube_url)]

    # Keep only the 'url' column
    result = filtered[["url"]]

    result.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(result)} URLs to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
