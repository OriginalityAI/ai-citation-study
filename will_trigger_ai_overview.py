# This file contains functions that filter out queries that most likely won't trigger an AI overview.

# 220368 queries
def will_trigger_ai_overview_v1(query):
    min_words = 3
    prefixes = [
        "how", "what", "why", "can", "does",
        "is", "are", "when", "which", "do"
    ]
    bad_prefixes = [
        "login", "facebook", "youtube", "netflix",
        "twitter", "instagram", "nba", "download", "best"
    ]
    q = query.lower().strip()
    if any(q.startswith(b + ' ') for b in bad_prefixes):
        return False
    if not any(q.startswith(p + ' ') for p in prefixes):
        return False
    if len(q.split()) < min_words:
        return False
    return True

# V2 ideas
# consider removing queries like "what does X mean"
# filter for "are pabco shingles any good" "... any good"
# queries that are too long

will_trigger_ai_overview_map = {
    "v1": will_trigger_ai_overview_v1
}
