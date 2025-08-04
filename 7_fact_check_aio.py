import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ORIGINALITY_API_KEY")

SAMPLE_DIR = Path('samples/ymyl_29000/res_20250723_n100')
OUTPUT_DIR = SAMPLE_DIR / 'fact_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

aio_query_ids = pd.read_csv(SAMPLE_DIR / '_responses.csv')['query_id']

def flatten_text_blocks(text_blocks):
    lines = []

    for block in text_blocks:
        block_type = block.get("type")

        if block_type == "paragraph":
            lines.append(block.get("snippet", ""))

        elif block_type == "heading":
            lines.append(f"{block.get('snippet', '')}:")

        elif block_type == "list":
            for item in block.get("list", []):
                title = item.get("title", "").strip()
                snippet = item.get("snippet", "").strip()
                if title and snippet:
                    lines.append(f"- {title} {snippet}")
                elif snippet:
                    lines.append(f"- {snippet}")

    return "\n".join(lines)

def fact_check(content):
    try:
        payload = {
            "title": "AIO Fact Check",
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
        return data
    
    except Exception as e:
        print(f"❌ Fact check error: {e}")
        return None

start_time = time.time()

for i, query_id in enumerate(aio_query_ids):
    with open(SAMPLE_DIR / f'{query_id}.json', 'r') as f:
        data = json.load(f)
        query = data['search_parameters']['q']
        text_blocks = data['ai_overview']['text_blocks']
        
        human_readable_aio = f'Question: {query}\n\nAnswer: {flatten_text_blocks(text_blocks)}'

        fact_res = fact_check(human_readable_aio)

        for i, fact_obj in fact_res['results']['facts'].items():
            t = int(str(fact_obj['truthfulness']).replace('%', '').strip())
            if t < 50:
                print(f"⚠️ {t}% truth \nFact: {fact_obj['fact']}\nExplanation: {fact_obj['explanation']}")

        with open(OUTPUT_DIR / f'facts_{query_id}.json', "w", encoding="utf-8") as jf:
            json.dump(fact_res, jf, indent=2)

        elapsed = time.time() - start_time
        eta_time = elapsed / (i+1) * (len(aio_query_ids) - (i+1))

        print(f"[{i+1}/{len(aio_query_ids)}] Fact checked AIO {query_id}. ⏱️ Elapsed: {elapsed:.2f} sec. ETA: {eta_time}")
