FOLDER_PATH = "samples/v3_1000/res_20250627_n100"
OUTPUT_FILE = "_urls.csv"

def normalize_url(url):
    """Remove query params and fragments; return scheme + netloc + path (lowercased, no trailing slash)"""
    parsed = urlparse(url)
    norm = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    return norm.lower()

cited_count
in_organic_results_count