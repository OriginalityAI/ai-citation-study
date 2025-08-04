import pandas as pd
import requests
from pathlib import Path
import time
import os
import json
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")

# File paths
CITATIONS_CSV = Path("legal_ai_citations.csv")
SCRAPED_CSV = Path("samples/ymyl_29000/res_20250723_n100/_scraped.csv")
FACT_RESULTS_DIR = Path("fact_results")
FACT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Load input data
citations_df = pd.read_csv(CITATIONS_CSV)
scraped_df = pd.read_csv(SCRAPED_CSV)
scraped_dict = dict(zip(scraped_df['url'], scraped_df['content']))

for i, row in citations_df.iterrows():
    query_id = row["query_id"]
    url = row["url"]
    content = scraped_dict.get(url, "")

    if not isinstance(content, str) or content.strip() == "":
        print(f"[{i+1}] ⏩ No content found for: {url}")
        continue

    json_path = FACT_RESULTS_DIR / f"{query_id}_{i}.json"

    try:
        print(f"[{i+1}] 🔍 Fact-checking: {url}")

        payload = {
            "title": "Ouroboros Fact Check",
            "check_ai": False,
            "check_plagiarism": False,
            "check_facts": True,
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

        # Save full JSON response
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(data, jf, indent=2)

        print(f"✅ Saved: {json_path}")
        time.sleep(2)

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error for {url}: {e}")
    except Exception as e:
        print(f"❌ General error for {url}: {e}")
