import pandas as pd
import requests
from pathlib import Path
import time
import os
import csv
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")

# Paths
INPUT_CSV = Path("samples/v3_1000/res_20250627_n100/_scraped_unclassified.csv")
OUTPUT_CSV = INPUT_CSV.with_name("_originality_results.csv")

# Load data, filter to only type == "OK"
df = pd.read_csv(INPUT_CSV)
df = df[df["type"] == "OK"]

# Write CSV incrementally with flush and print
with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["url", "ai_class", "confidence"])
    writer.writeheader()

    for i, row in df.iterrows():
        url = row["url"]
        content = row["content"]

        if not isinstance(content, str) or content.strip() == "":
            print(f"[{i+1}] ⏩ Skipping empty content for: {url}")
            continue

        try:
            print(f"[{i+1}] 🔍 Scanning: {url}")

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

            response = requests.post(
                "https://api.originality.ai/api/v3/scan",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            ai_info = data.get("results", {}).get("ai", {})
            classification = ai_info.get("classification", {})
            confidence_data = ai_info.get("confidence", {})

            if not classification or not confidence_data:
                print(f"⚠️ Incomplete result for {url}")
                continue

            is_ai = classification.get("AI", 0) > classification.get("Original", 0)
            label = "AI" if is_ai else "Human"
            confidence = confidence_data.get("AI" if is_ai else "Original", None)

            if confidence is None:
                print(f"⚠️ Missing confidence score for {url}")
                continue

            writer.writerow({
                "url": url,
                "ai_class": label,
                "confidence": confidence
            })
            f.flush()

            # 👇 Print result to console
            percent = round(confidence * 100, 1)
            print(f"✅ {label} ({percent}%) — {url}")

            time.sleep(2)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                print(f"⚠️ 422 Unprocessable Entity for {url} — skipping.")
                continue
            else:
                print(f"❌ HTTP error for {url}: {e}")
        except Exception as e:
            print(f"❌ General error scanning {url}: {e}")
