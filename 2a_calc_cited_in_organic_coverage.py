"""
Optional step script to calculate what proportion of URLs cited in AI Overviews
are also present in that query's organic results.

Input:
- Folder path containing JSON response files (each file corresponds to one query response).

Output:
- Prints and saves aggregated coverage proportion in _cited_in_organic_coverage.txt inside the folder.
"""

import os
import json
from urllib.parse import urlparse

# Set your folder path here
FOLDER_PATH = "samples/v1_50/res_20250622_n40"
OUTPUT_FILE = "_cited_in_organic_coverage.txt"

def normalize_url(url):
    """Remove query params and fragments; return scheme + netloc + path (lowercased, no trailing slash)"""
    parsed = urlparse(url)
    norm = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return norm.lower()

def extract_links(res):
    """
    Extract and normalize cited and organic links from one JSON response object.
    Returns sets of normalized URLs.
    """
    cited_links = set()
    organic_links = set()

    try:
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
    except Exception as e:
        print(f"Error extracting links: {e}")

    return cited_links, organic_links

def main():
    json_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.json')]
    total_cited = 0
    total_cited_in_organic = 0

    for filename in json_files:
        filepath = os.path.join(FOLDER_PATH, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                res = json.load(f)
        except Exception as e:
            print(f"Failed to load {filename}: {e}")
            continue

        cited_links, organic_links = extract_links(res)
        if not cited_links:
            continue

        cited_in_organic = len(cited_links.intersection(organic_links))
        total_cited_in_organic += cited_in_organic
        total_cited += len(cited_links)

    if total_cited == 0:
        print("No cited URLs found in the dataset.")
        coverage_str = "No cited URLs found."
    else:
        coverage = total_cited_in_organic / total_cited
        coverage_str = (f"Proportion of cited URLs present in organic results: "
                        f"{coverage:.2%} ({total_cited_in_organic}/{total_cited})")

    print(coverage_str)

    output_path = os.path.join(FOLDER_PATH, OUTPUT_FILE)
    with open(output_path, 'w', encoding='utf-8') as out_f:
        out_f.write(coverage_str + '\n')

    print(f"Coverage report saved to {output_path}")

if __name__ == "__main__":
    main()
