import os
import json
import csv
from collections import defaultdict
from urllib.parse import urlparse, parse_qsl, urlencode

# === Configuration ===
FOLDER_PATH = "samples/v3_1000/res_20250627_n100"
URLS_POOL_CSV = "_urls_pool.csv"
RESPONSES_CSV = "_responses.csv"

def normalize_url(url):
    parsed = urlparse(url)
    query_sensitive_domains = {
        "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be",
        "www.google.com", "www.bing.com"
    }
    keep_query = parsed.netloc in query_sensitive_domains
    query = f"?{urlencode(sorted(parse_qsl(parsed.query)))}" if keep_query and parsed.query else ""
    norm = f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}".rstrip('/')
    return norm.lower()

def extract_normalized_links(res):
    cited_links = []
    organic_links = []

    cited_refs = res.get("ai_overview", {}).get("references", [])
    for ref in cited_refs:
        link = ref.get("link")
        if link:
            cited_links.append(normalize_url(link))

    organic_res = res.get("organic_results", [])
    for org in organic_res:
        link = org.get("link")
        if link:
            organic_links.append(normalize_url(link))

    return cited_links, organic_links

def main():
    urls_pool = set()
    response_rows = []

    json_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.json')]

    for filename in json_files:
        filepath = os.path.join(FOLDER_PATH, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                res = json.load(f)
        except Exception as e:
            print(f"Failed to load {filename}: {e}")
            continue

        cited_links, organic_links = extract_normalized_links(res)

        if not cited_links and not organic_links:
            continue

        if cited_links:
            urls_pool.update(cited_links)
            urls_pool.update(organic_links)

        response_rows.append({
            "query_id": filename[:-5],
            "references": json.dumps(cited_links),
            "organic_results": json.dumps(organic_links)
        })

    # Write cited URLs pool
    with open(os.path.join(FOLDER_PATH, URLS_POOL_CSV), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        for url in sorted(urls_pool):
            writer.writerow([url])

    # Write responses CSV
    with open(os.path.join(FOLDER_PATH, RESPONSES_CSV), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["query_id", "references", "organic_results"])
        writer.writeheader()
        writer.writerows(response_rows)

    print(f"Saved: {URLS_POOL_CSV} and {RESPONSES_CSV}")

if __name__ == "__main__":
    main()
