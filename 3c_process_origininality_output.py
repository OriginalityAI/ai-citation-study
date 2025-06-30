import pandas as pd
from pathlib import Path

# === Config ===
SAMPLE_DIR = Path("samples/v3_1000/res_20250627_n100")
CLASSIFIED_OUTPUT_DIR = SAMPLE_DIR / "classified_batches"
OUTPUT_CSV = SAMPLE_DIR / "_classified_urls.csv"
SKIPPED_LOG = SAMPLE_DIR / "_skipped_batches.txt"

REQUIRED_COLUMNS = ["Url", "AI Classification", "Confidence"]

all_data = []
skipped = []

for file in CLASSIFIED_OUTPUT_DIR.glob("*.xlsx"):
    try:
        df = pd.read_excel(file, header=1)

        if not all(col in df.columns for col in REQUIRED_COLUMNS):
            missing = set(REQUIRED_COLUMNS) - set(df.columns)
            print(f"⚠️ Skipped {file.name}: missing columns {missing}")
            skipped.append(f"{file.name}: missing columns {missing}")
            continue

        df_clean = df[REQUIRED_COLUMNS].copy()
        df_clean.columns = ["url", "ai_class", "confidence"]
        all_data.append(df_clean)

    except Exception as e:
        print(f"❌ Failed to read {file.name}: {e}")
        skipped.append(f"{file.name}: {e}")

# Merge and write
if all_data:
    combined = pd.concat(all_data, ignore_index=True)
    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved: {OUTPUT_CSV}")

# Log skipped files
if skipped:
    with open(SKIPPED_LOG, "w") as f:
        f.write("\n".join(skipped))
    print(f"📄 Skipped file log saved to: {SKIPPED_LOG}")
