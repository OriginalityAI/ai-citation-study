import json
from pathlib import Path

FACT_RESULTS_DIR = Path("samples/ymyl_29000/res_20250723_n100/fact_results")

all_facts = []

for json_file in FACT_RESULTS_DIR.glob("*.json"):
    query_id = json_file.stem
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        facts = data.get("results", {}).get("facts", {})

        for fact_key, fact_data in facts.items():
            if not isinstance(fact_data, dict):
                continue

            raw_score = fact_data.get("truthfulness", "")
            try:
                score = float(str(raw_score).replace("%", "").strip())
            except (ValueError, TypeError):
                continue

            all_facts.append({
                "query_id": query_id,
                "score": score,
                "fact": fact_data.get("fact", "[No fact]"),
                "explanation": fact_data.get("explanation", "[No explanation]"),
                "links": fact_data.get("links", [])
            })

    except Exception as e:
        print(f"❌ Error processing {json_file.name}: {e}")

# Sort by score ascending
all_facts.sort(key=lambda x: x["score"])

# Display
for i, fact in enumerate(all_facts, 1):
    print(f"\n#{i} 🛑 Query ID: {fact['query_id']}")
    print(f"⚠️  Truthfulness: {fact['score']}%")
    print(f"📌 Fact: {fact['fact']}")
    print(f"🧠 Explanation: {fact['explanation']}")
    if fact["links"]:
        print("🔗 Links:")
        for link in fact["links"]:
            print(f"   - {link}")
    else:
        print("🔗 Links: [None]")

    input("\n➡️ Press Enter to see the next one...\n")
