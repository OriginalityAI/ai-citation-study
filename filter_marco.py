import pandas as pd

# === Step 1: Load your TSV file ===
input_path = 'datasets/ms-marco-web-search-queries.tsv'
df = pd.read_csv(input_path, sep='\t', header=None, names=['query_id', 'query', 'languages'])

# === Step 2: Define basic YMYL keyword list ===
ymyl_keywords = [
    # 📘 Health & Medical
    "symptom", "symptoms", "diagnosis", "treatment", "disease", "illness", "sickness",
    "infection", "injury", "flu", "covid", "cancer", "diabetes", "asthma",
    "heart attack", "stroke", "blood pressure", "cholesterol", "vitamin deficiency",
    "health condition", "is it safe to", "how to treat", "home remedy", "medication",
    "mental health", "anxiety", "depression", "bipolar", "panic attack", "ptsd",
    "psychologist", "therapist", "therapy", "suicide hotline", "eating disorder",
    "dental care", "skin cancer", "rash", "hiv", "aids", "std", "allergy treatment",

    # 🥗 Nutrition & Fitness
    "diet", "calories", "meal plan", "intermittent fasting", "keto", "low carb",
    "paleo", "vegetarian", "vegan", "nutritionist", "supplements", "weight loss",
    "how to lose weight", "best foods for", "exercise", "workout plan",
    "is fasting healthy", "is it safe to eat", "daily calorie needs",

    # 💰 Finance & Money
    "credit score", "how to improve credit", "credit report", "loan", "personal loan",
    "student loan", "car loan", "mortgage", "refinance", "debt", "payday loan",
    "budgeting", "retirement", "401k", "rrsp", "tax", "irs", "tax refund",
    "tax return", "tax bracket", "tax deduction", "crypto", "bitcoin", "invest",
    "how to invest", "mutual fund", "etf", "stock market", "roth ira", "capital gains",
    "interest rate", "inflation", "financial advisor", "open a bank account",
    "freelance income", "side hustle", "how to make money online",

    # ⚖️ Legal & Civic Information
    "lawyer", "legal advice", "divorce", "custody", "child support", "dui", "court case",
    "legal age", "tenant rights", "eviction", "lease agreement", "can i sue",
    "how to file a lawsuit", "small claims court", "personal injury lawyer",
    "immigration", "visa", "green card", "citizenship", "asylum", "deportation",
    "criminal record", "expungement", "legal aid", "public defender", "civil rights",

    # 🛡️ Safety & Crisis
    "domestic violence", "child abuse", "emergency hotline", "emergency shelter",
    "fire safety", "first aid", "choking", "cpr", "poison control", "gun safety",
    "how to report abuse", "emergency number", "what to do in an earthquake",
    "is it dangerous to", "should i call 911", "disaster preparedness",

    # 🧭 Major Life Decisions
    "career change", "how to quit your job", "is college worth it", "how to move abroad",
    "best cities to live", "rent vs buy", "should i get married", "relationship advice",
    "how to adopt", "pregnancy symptoms", "birth control", "is it time to retire",
    "life insurance", "funeral planning", "education loan", "how to choose a major",
    "best degree for", "job interview tips", "how to negotiate salary"
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

output_path = 'filtered_ymyl_queries_2.csv'
filtered_df[['query_id', 'query']].to_csv(output_path, index=False)

print(f"✅ Filtered {len(filtered_df)} YMYL queries and saved to {output_path}")
