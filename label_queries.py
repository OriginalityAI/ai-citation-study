import os
from dotenv import load_dotenv
import pandas as pd
import time
import json
import csv
import openai
from tqdm import tqdm

# === Load OpenAI API key ===
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Config ===
INPUT_CSV = "marco_ymyl_queries.csv"
OUTPUT_CSV = "marco_ymyl_queries_labeled.csv"
MODEL = "gpt-4-1106-preview"
TEMPERATURE = 0
BATCH_SIZE = 20
RATE_LIMIT_DELAY = 1.5

# === System prompt ===
system_prompt = """You are a search analyst. Given a list of user queries, classify each one into the following categories. Your job is to return a JSON array of objects with the following fields:

- query_id (copied from input)
- risk_category: must be one of:
  - "ymyl" if the query relates to health/safety, finance, legal, or politics
  - "sensitive" only if the query relates to **Adult content, gambling, alcohol, firearms, dangerous instructions, hate/harassment, misinformation, children’s content (COPPA), or crisis events**
  - "general" for all other topics
- intent_category: one of "info", "navigational", "commercial", or "transactional"
- funnel_stage: one of "TOFU", "MOFU", or "BOFU"
- ymyl_category: one of "health/safety", "finance", "legal", "politics", or "-" if not YMYL

Return all fields in lowercase. Return only the JSON array with one object per query.

Example:
[
  {
    "query_id": 123,
    "risk_category": "ymyl",
    "intent_category": "info",
    "funnel_stage": "TOFU",
    "ymyl_category": "health/safety"
  },
  ...
]
"""

# === Tracking ===
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

# === Format prompt for GPT ===
def make_user_prompt(batch):
    formatted = "\n".join(json.dumps({"query_id": int(qid), "query_text": qtext}) for qid, qtext in batch)
    return f"Here are {len(batch)} queries:\n{formatted}\n\nReturn a JSON array of classifications."

# === Parse GPT response ===
def parse_response(text):
    if text.startswith("```"):
        lines = text.strip("`").splitlines()
        text = "\n".join(line for line in lines if not line.strip().lower().startswith("json"))
    try:
        data = json.loads(text)
        if not isinstance(data, list):
            print(f"⚠️ Response is not a list:\n{text}")
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON error:\n{text}\nError: {e}")
        return None

# === Load input ===
df = pd.read_csv(INPUT_CSV)

# === Write header if needed ===
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_id", "query_text", "risk_category",
            "intent_category", "funnel_stage", "length_category", "ymyl_category"
        ])

# === Stream write loop ===
with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)

    for i in tqdm(range(0, len(df), BATCH_SIZE)):
        batch_df = df.iloc[i:i + BATCH_SIZE]
        batch = list(zip(batch_df['query_id'], batch_df['query']))

        try:
            user_prompt = make_user_prompt(batch)
            response = client.chat.completions.create(
                model=MODEL,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.choices[0].message.content.strip()
            labels = parse_response(content)
            if labels is None:
                continue

            label_map = {str(item["query_id"]): item for item in labels}

            for qid, qtext in batch:
                qid_str = str(qid)
                label = label_map.get(qid_str)
                if not label:
                    print(f"⚠️ Missing label for query_id {qid}")
                    continue

                for key in seen_values.keys():
                    val = label.get(key, "MISSING")
                    update_counts(key, val)

                word_count = len(str(qtext).split())
                if word_count <= 2:
                    length_category = "head"
                elif word_count == 3:
                    length_category = "mid-tail"
                else:
                    length_category = "long-tail"

                writer.writerow([
                    qid,
                    qtext,
                    label.get("risk_category", ""),
                    label.get("intent_category", ""),
                    label.get("funnel_stage", ""),
                    length_category,
                    label.get("ymyl_category", "")
                ])
                f.flush()

            if (i // BATCH_SIZE + 1) % 5 == 0:
                print_summary()

            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"⚠️ API error on batch {i}-{i+BATCH_SIZE}: {e}")
            continue

print("\n✅ Done. Final category stats:")
print_summary()
