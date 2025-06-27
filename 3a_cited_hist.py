import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# === Configuration ===
CSV_PATH = Path("samples/v3_1000/res_20250627_n100/_url_counts.csv")
PLOT_DIR = CSV_PATH.parent / "histograms"
PLOT_DIR.mkdir(exist_ok=True)

def plot_hist(df, col, title, log_scale=False):
    plt.figure(figsize=(8, 5))
    ax = df[col].value_counts().sort_index().plot.bar()
    plt.title(title)
    plt.xlabel(col)
    plt.ylabel("URL Count")
    if log_scale:
        ax.set_yscale('log')
        plt.ylabel("URL Count (log)")
    plt.tight_layout()
    plot_path = PLOT_DIR / f"{col}_hist.png"
    plt.savefig(plot_path)
    plt.close()
    print(f"Saved histogram: {plot_path.name}")

def main():
    df = pd.read_csv(CSV_PATH)

    # Basic stats
    total_urls = len(df)
    total_global_citations = df["global_cited_count"].sum()
    total_organic_citations = df["organic_cited_count"].sum()
    cited_multiple_times = (df["global_cited_count"] >= 2).sum()

    # Cited but never found in organic
    cited_only = df[df["global_cited_count"] > 0]
    hallucinated = (cited_only["organic_cited_count"] == 0).sum()
    cited_and_in_organic = (cited_only["organic_cited_count"] > 0).sum()

    # Average match rate (only for cited URLs)
    match_rates = cited_only["organic_cited_count"] / cited_only["global_cited_count"]
    avg_match_rate = match_rates.mean()

    # Global coverage rate
    global_coverage_rate = (
        total_organic_citations / total_global_citations
        if total_global_citations > 0 else 0
    )

    # Print stats
    print(f"Total unique URLs: {total_urls}")
    print(f"Total global citations: {total_global_citations}")
    print(f"URLs cited ≥ 2 times: {cited_multiple_times}")
    print(f"URLs cited but never in organic: {hallucinated}")
    print(f"URLs cited and appeared in organic: {cited_and_in_organic}")
    print(f"Average per-URL organic citation rate: {avg_match_rate:.2%}")
    print(f"Global citation coverage in organic: {global_coverage_rate:.2%}")

    # Plot histograms
    plot_hist(df, "global_cited_count", "Global Cited Count per URL", log_scale=True)
    plot_hist(df, "organic_cited_count", "Organic Cited Count per URL", log_scale=True)
    plot_hist(df, "in_organic_results_count", "Organic Presence Count per URL", log_scale=True)

if __name__ == "__main__":
    main()
