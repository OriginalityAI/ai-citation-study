import os
import json
import csv
from collections import defaultdict
from urllib.parse import urlparse

# === Configuration ===
FOLDER_PATH = "samples/v3_1000/res_20250627_n100"
OUTPUT_CSV = "_url_counts.csv"

def normalize_url(url):
    parsed = urlparse(url)
    norm = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return norm.lower()

def extract_normalized_links(res):
    cited_links = set()
    organic_links = set()

    cited_refs = res.get("ai_overview", {}).get("references", [])
    for ref in cited_refs:
        link = ref.get("link")
        if link:
            cited_links.add(normalize_url(link))

    organic_res = res.get("organic_results", [])
    for org in organic_res:
        link = org.get("link")
        if link:
            organic_links.add(normalize_url(link))

    return cited_links, organic_links

def main():
    global_cited = defaultdict(int)
    organic_cited = defaultdict(int)
    organic_present = defaultdict(int)

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

        # Skip if no cited references
        if not cited_links:
            continue

        # Count cited links globally
        for url in cited_links:
            global_cited[url] += 1

        # Count cited links that also appeared in the same organic results
        for url in cited_links.intersection(organic_links):
            organic_cited[url] += 1

        # Count links that appeared in organic results (for any AI overview query)
        for url in organic_links:
            organic_present[url] += 1

    all_urls = set(global_cited) | set(organic_cited) | set(organic_present)

    output_path = os.path.join(FOLDER_PATH, OUTPUT_CSV)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "url",
            "global_cited_count",
            "organic_cited_count",
            "in_organic_results_count"
        ])
        for url in sorted(all_urls):
            writer.writerow([
                url,
                global_cited.get(url, 0),
                organic_cited.get(url, 0),
                organic_present.get(url, 0)
            ])

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
