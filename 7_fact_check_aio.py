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

for query_idx, query_id in enumerate(aio_query_ids, 1):
    try:
        with open(SAMPLE_DIR / f'{query_id}.json', 'r') as f:
            data = json.load(f)
            query = data['search_parameters']['q']
            text_blocks = data['ai_overview']['text_blocks']
            
            human_readable_aio = f'Question: {query}\n\nAnswer: {flatten_text_blocks(text_blocks)}'

            fact_res = fact_check(human_readable_aio)

            if not fact_res:
                print(f"[{query_idx}/{len(aio_query_ids)}] ❗️ Empty response for {query_id}.")

            for i, fact_obj in fact_res['results']['facts'].items():
                try:
                    t = int(str(fact_obj['truthfulness']).replace('%', '').strip())
                    if t < 50:
                        print(f"\n⚠️ {t}% truth \nFact: {fact_obj['fact']}\nExplanation: {fact_obj['explanation']}\n")
                except Exception as e:
                    print(f'❗️ Oops, failed to read t! {e}')

            with open(OUTPUT_DIR / f'facts_{query_id}.json', "w", encoding="utf-8") as jf:
                json.dump(fact_res, jf, indent=2)

            elapsed = time.time() - start_time
            eta_time = elapsed / query_idx * (len(aio_query_ids) - query_idx)

            print(f"[{query_idx}/{len(aio_query_ids)}] Fact checked {query_id}. ⏱️ Elapsed: {elapsed:.2f}s. ETA: {(eta_time / 60 / 60):.2f}h")
    except Exception as e:
        print(f"[{query_idx}/{len(aio_query_ids)}] ❗️ Unexpected error for {query_id}. Error: {e}")