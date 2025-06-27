from pathlib import Path
import pandas as pd

SAMPLE_NAME = 'v3_1000'
SAMPLE_DIR = Path('samples') / SAMPLE_NAME
LABELED_QUERIES_FILE = SAMPLE_DIR / f'queries_{SAMPLE_NAME}_labeled.csv'
OUTPUT_TXT_FILE = SAMPLE_DIR / f'{SAMPLE_NAME}_overview_stats.txt'

# Load CSV
df = pd.read_csv(LABELED_QUERIES_FILE)

# Calculate percentage
counts = df['triggered_ai_overview'].value_counts(normalize=True) * 100

# Format the result
lines = []
lines.append(f"Overview Trigger Stats for Sample: {SAMPLE_NAME}")
lines.append("==========================================")
for label in ['y', 'n', 'b']:
    percent = counts.get(label, 0.0)
    lines.append(f"{label.upper()}: {percent:.2f}%")

# Print to console
for line in lines:
    print(line)

# Write to TXT
with open(OUTPUT_TXT_FILE, 'w') as f:
    f.write('\n'.join(lines))

print(f"\nWritten to {OUTPUT_TXT_FILE}")
