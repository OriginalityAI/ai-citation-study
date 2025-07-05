import pandas as pd
import requests
from pathlib import Path
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")
INPUT_CSV = Path("samples/v3_1000/res_20250627_n100/_scraped_unclassified.csv")
OUTPUT_CSV = INPUT_CSV.with_name("_originality_results.csv")

df = pd.read_csv(INPUT_CSV)
results = []

for i, row in df.iterrows():
    url = row["url"]
    content = row["content"]

    if not content or content.strip() == "":
        print(f"[{i+1}] Skipping empty content for: {url}")
        continue

    try:
        print(f"[{i+1}] Scanning with Originality.ai: {url}")

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

        ai_score = data.get("ai_score", {})
        label = ai_score.get("likelyAI", None)
        confidence = ai_score.get("confidence", None)

        if label is None or confidence is None:
            print(f"⚠️ Incomplete result for {url}")
            continue

        results.append({
            "url": url,
            "ai_class": "AI" if label else "Human",
            "confidence": confidence
        })

        time.sleep(2)  # polite delay to avoid rate limits

    except Exception as e:
        print(f"❌ Error scanning {url}: {e}")

# Save results
pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ Done. Results saved to: {OUTPUT_CSV}")
