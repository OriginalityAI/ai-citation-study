import os
from dotenv import load_dotenv
import pandas as pd
import time
import json
import csv
import openai
from tqdm import tqdm

# === Load OpenAI API key from .env ===
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Config ===
INPUT_CSV = "marco_ymyl_queries.csv"
OUTPUT_CSV = "marco_ymyl_queries_labeled.csv"
MODEL = "gpt-4-1106-preview"
TEMPERATURE = 0
RATE_LIMIT_DELAY = 1.5  # seconds between calls

# === System Prompt ===
system_prompt = """You are a search analyst. Given a user query, classify it into the following 4 categories. Return valid JSON using lowercase values and keys:

1. risk_category: "ymyl", "sensitive", or "general"
2. intent_category: "info", "navigational", "commercial", or "transactional"
3. funnel_stage: "TOFU", "MOFU", or "BOFU"
4. ymyl_category: "health/safety", "finance", "legal", "politics", or "-" if not YMYL

Respond with JSON like:
{
  "risk_category": "ymyl",
  "intent_category": "info",
  "funnel_stage": "TOFU",
  "ymyl_category": "health/safety"
}
"""

# === Tracking structures ===
seen_values = {
    "risk_category": set(),
    "intent_category": set(),
    "funnel_stage": set(),
    "ymyl_category": set()
}
category_counts = {
    "risk_category": {},
    "intent_category": {},
    "funnel_stage": {},
    "ymyl_category": {}
}

def update_counts(key, value):
    seen_values[key].add(value)
    category_counts[key][value] = category_counts[key].get(value, 0) + 1

def print_summary():
    print("\n📊 Current counts:")
    for key in category_counts:
        print(f"\n{key}:")
        for val, count in sorted(category_counts[key].items()):
            print(f"  {val}: {count}")

# === GPT Classification ===
def classify_query(query):
    user_prompt = f'Query: "{query}"\nClassify it as described above.'

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content.strip()

        # Handle code block wrapper (e.g., ```json\n{...}\n```)
        if content.startswith("```"):
            lines = content.strip("`").splitlines()
            content = "\n".join(line for line in lines if not line.strip().lower().startswith("json"))

        return json.loads(content)

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error for query:\n{query}\nRaw content:\n{content}\nError: {e}")
        return None
    except Exception as e:
        print(f"⚠️ API error for query:\n{query}\nError: {e}")
        return None

# === Load input CSV ===
df = pd.read_csv(INPUT_CSV)

# === Write header if starting from scratch ===
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "query_text", "risk_category",
            "intent_category", "funnel_stage", "length_category", "ymyl_category"
        ])

# === Stream processing ===
with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)

    for i, row in tqdm(df.iterrows(), total=len(df)):
        query_id = row['query_id']
        query_text = row['query']

        label = classify_query(query_text)
        if label is None:
            continue

        # Track seen values and counts
        for key in seen_values.keys():
            val = label.get(key, "MISSING")
            update_counts(key, val)

        # Word count to length category
        word_count = len(str(query_text).split())
        if word_count <= 2:
            length_category = "head"
        elif word_count == 3:
            length_category = "mid-tail"
        else:
            length_category = "long-tail"

        # Write row
        writer.writerow([
            query_id,
            query_text,
            label.get("risk_category", ""),
            label.get("intent_category", ""),
            label.get("funnel_stage", ""),
            length_category,
            label.get("ymyl_category", "")
        ])
        f.flush()

        # Print summary every 20 queries
        if (i + 1) % 20 == 0:
            print_summary()

        time.sleep(RATE_LIMIT_DELAY)

# === Final summary ===
print("\n✅ Finished classification.")
print_summary()
