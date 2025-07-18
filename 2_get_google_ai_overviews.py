import os
import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from serpapi import GoogleSearch
from dotenv import load_dotenv

SAMPLE_NAME = 'ymyl_1000'
N = 100 # number of organic results

# Load API key
load_dotenv()
API_KEY = os.getenv("SERP_API_KEY")

SAMPLE_DIR = Path('samples') / SAMPLE_NAME
QUERIES_FILE = SAMPLE_DIR / f'queries_{SAMPLE_NAME}.csv'
DATE_STR = datetime.now(timezone.utc).strftime('%Y%m%d')
RESPONSE_DIR = SAMPLE_DIR / f'res_{DATE_STR}_n{N}'
LABELED_QUERIES_FILE = RESPONSE_DIR / f'_queries_labeled.csv'

# Ensure output directory exists
RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

# Load queries
df = pd.read_csv(QUERIES_FILE)

# Prepare list for labeled results
labeled = []

for _, row in df.iterrows():
    query_id = row['query_id']
    query_text = row['query_text']

    # Build params and call SerpApi
    params = {
        'engine': 'google',
        'q': query_text,
        'api_key': API_KEY,
        'gl': 'us',
        'hl': 'en',
        'num': N
    }
    search = GoogleSearch(params)
    results = search.get_dict()

    # Save full JSON response
    out_path = RESPONSE_DIR / f'{query_id}.json'
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    # Determine triggered_ai_overview label
    if "ai_overview" in results:
        if "references" in results["ai_overview"]:
            triggered_ai_overview = "y"
        else:
            triggered_ai_overview = "b"
    else:
        triggered_ai_overview = "n"


    labeled.append({
        'query_id': query_id,
        'query_text': query_text,
        'triggered_ai_overview': triggered_ai_overview
    })

    print(f"Processed {query_id}: {query_text} -> {triggered_ai_overview}")

# Save labeled CSV
pd.DataFrame(labeled).to_csv(LABELED_QUERIES_FILE, index=False)
print(f"Labeled results saved to: {LABELED_QUERIES_FILE}")
