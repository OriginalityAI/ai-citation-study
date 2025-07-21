import pandas as pd

# === Step 1: Load your TSV file ===
input_path = 'datasets/ms-marco-web-search-queries.tsv'
df = pd.read_csv(input_path, sep='\t', header=None, names=['query_id', 'query', 'languages'])

# === Step 2: Define basic YMYL keyword list ===
ymyl_keywords = [
    "symptoms", "treatment", "disease", "illness", "diagnosis",
    "loan", "mortgage", "debt", "credit", "invest", "retirement", "finance",
    "mental health", "therapy", "depression", "anxiety", "psychologist",
    "calories", "diet", "nutrition", "cholesterol", "blood pressure",
    "insurance", "tax", "lawyer", "legal", "divorce", "visa", "immigration", "asylum"
]

# === Step 3: Clean and prepare query text ===
# Convert to string, strip whitespace, lowercase
df['query_clean'] = df['query'].astype(str).str.strip().str.lower()

# === Step 4: Apply keyword filter safely ===
df['is_ymyl'] = df['query_clean'].apply(
    lambda q: any(kw in q for kw in ymyl_keywords)
)

# === Step 5: Filter and export ===
filtered_df = df[df['is_ymyl']].copy()

output_path = 'filtered_ymyl_queries.csv'
filtered_df[['query_id', 'query']].to_csv(output_path, index=False)

print(f"✅ Filtered {len(filtered_df)} YMYL queries and saved to {output_path}")
