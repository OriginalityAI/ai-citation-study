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


def will_trigger_ai_overview_v2(query):
    min_words = 3
    max_words = 12
    prefixes = [
        "how", "what", "why", "can", "does", "when", "which", "do"
    ]
    bad_keywords = [
        "login", "facebook", "youtube", "netflix", "twitter", "instagram", "nba",
        "download", "best", "reddit", "porn", "murder", "pregnant", "hate", "suicide", "anime",
        "buy", "price", "worth", "good", "bad", "vs", "vs.", "review", "list", "ranking", "any good"
    ]
    q = query.lower().strip()
    word_count = len(q.split())
    if word_count < min_words or word_count > max_words:
        return False
    if not any(q.startswith(p + ' ') for p in prefixes):
        return False
    if any(b in q for b in bad_keywords):
        return False
    return True


def will_trigger_ai_overview_v3(query):
    min_words = 3
    max_words = 12
    prefixes = [
        "how", "what", "does", "when", "why", "which"
    ]
    bad_prefixes = [
        "how old is", "how tall is", "when is", "who is", "what day",
        "what year", "how many", "how much"
    ]
    bad_keywords = [
        "login", "facebook", "youtube", "netflix", "twitter", "instagram", "nba",
        "download", "best", "reddit", "porn", "murder", "pregnant", "hate", "suicide", "anime",
        "buy", "price", "worth", "good", "bad", "vs", "vs.", "review", "list", "ranking", "any good",
        "tiktok", "telegram", "bts"
    ]
    q = query.lower().strip()
    word_count = len(q.split())
    if word_count < min_words or word_count > max_words:
        return False
    if not any(q.startswith(p + ' ') for p in prefixes):
        return False
    if any(q.startswith(p + ' ') for p in bad_prefixes):
        return False
    if any(b in q for b in bad_keywords):
        return False
    return True


will_trigger_ai_overview_map = {
    "v1": will_trigger_ai_overview_v1,
    "v2": will_trigger_ai_overview_v2
}
