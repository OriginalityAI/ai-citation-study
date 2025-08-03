#!/usr/bin/env python3
import pandas as pd
import textwrap

CSV_PATH = "support_eval_minimal.csv"  # same folder
WRAP = 100
COLS = ["query_id", "query_text", "url", "snippet", "support_category", "rationale"]

# Try to enable ANSI colors on Windows (optional)
try:
    from colorama import init as colorama_init
    colorama_init()
except Exception:
    pass

# ANSI styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDER = "\033[4m"

# Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
GREY = "\033[90m"

def color_text(s, style):
    return f"{style}{s}{RESET}"

def color_category(cat: str) -> str:
    c = (cat or "").strip().lower()
    if c == "supports":
        return color_text(cat, GREEN + BOLD)
    if c == "partially_supports":
        return color_text(cat, YELLOW + BOLD)
    if c == "refutes":
        return color_text(cat, RED + BOLD)
    if c == "unrelated":
        return color_text(cat, MAGENTA + BOLD)
    if c == "error":
        return color_text(cat, RED + BOLD)
    return color_text(cat or "—", BLUE + BOLD)

def wrap_block(label, value, width=WRAP, label_style=BOLD, value_style=""):
    s = "" if pd.isna(value) else str(value).strip()
    head = f"{color_text(label, label_style)}:"
    if not s:
        return f"{head} {color_text('—', GREY)}\n"
    wrapped = textwrap.fill(s, width=width)
    if value_style:
        wrapped = color_text(wrapped, value_style)
    return f"{head}\n{wrapped}\n"

def main():
    # Prevent pandas truncation if you print Series/DataFrames
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.width", 0)

    df = pd.read_csv(CSV_PATH)

    # Filter to only non-supports (case-insensitive)
    mask = df["support_category"].astype(str).str.strip().str.lower().ne("supports")
    subset = df.loc[mask, COLS].reset_index(drop=True)

    if subset.empty:
        print(color_text("No rows where support_category != 'supports'.", GREEN))
        return

    total = len(subset)
    for i, row in subset.iterrows():
        header = f"[{i+1}/{total}]"
        cat_colored = color_category(str(row.get("support_category", "")))
        print(color_text(header, GREY), "-", cat_colored)

        print(wrap_block("query_id", row["query_id"], label_style=GREY))
        print(wrap_block("query_text", row["query_text"], value_style=BOLD))
        print(wrap_block("url", row["url"], value_style=UNDER + CYAN))
        print(wrap_block("snippet", row["snippet"], value_style=CYAN))
        print(wrap_block("support_category", row["support_category"]))
        print(wrap_block("rationale", row["rationale"]))

        if input(color_text("Press Enter for next, or 'q' to quit: ", GREY)).strip().lower().startswith("q"):
            break

if __name__ == "__main__":
    main()
