#!/usr/bin/env python3
# combine_fever_results.py
# Reads:
#   - checker_results.jsonl            (Originality fact checker)
#   - gpt_results_raw_gpt-4o.jsonl     (GPT-4o outputs)
#   - gpt_results_raw_gpt-5.jsonl      (GPT-5 outputs)
# Builds two DataFrames:
#   1) all_df with columns: fever_id, claim, gold, originality, gpt-4o, gpt-5
#   2) disagreements_df: rows where any of {gold, originality, gpt-4o, gpt-5} disagree
#
# Usage:
#   python combine_fever_results.py \
#       --orig checker_results.jsonl \
#       --gpt4o gpt_results_raw_gpt-4o.jsonl \
#       --gpt5 gpt_results_raw_gpt-5.jsonl \
#       --out-all all_results.csv \
#       --out-disagreements disagreements.csv
#
# If --out-* not provided, it just prints small samples & counts.

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", default="checker_results.jsonl", help="Originality JSONL path")
    ap.add_argument("--gpt4o", default="gpt_results_raw_gpt-4o.jsonl", help="GPT-4o JSONL path")
    ap.add_argument("--gpt5", default="gpt_results_raw_gpt-5.jsonl", help="GPT-5 JSONL path")
    ap.add_argument("--out-all", default=None, help="CSV path to write full combined results")
    ap.add_argument("--out-disagreements", default='disagree.csv', help="CSV path to write only disagreements")
    return ap.parse_args()


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines but continue processing
                continue


def normalize_label(val):
    """Normalize labels to one of: 'True', 'False', 'Unknown' (or None)."""
    if val is None:
        return None
    s = str(val).strip().lower()

    # direct booleans or strings
    if s in {"true", "t", "correct"}:
        return "True"
    if s in {"false", "f", "incorrect"}:
        return "False"

    # common 'unknown/insufficient' signals
    if any(k in s for k in [
        "unknown", "insufficient", "uncertain", "ambiguous",
        "cannot determine", "can't determine", "not enough info",
        "not enough information"
    ]):
        return "Unknown"

    # leave other content as None (treat as missing)
    return None


_gpt_head_pat = re.compile(
    r"^\s*(true|false|unknown|insufficient|cannot\s+determine|not\s+enough\s+info|not\s+enough\s+information|ambiguous|uncertain)\b",
    re.IGNORECASE
)


def parse_gpt_response_text(text: str):
    """Extract a label from GPT response text. Prefer first token; else heuristic."""
    if not text:
        return None
    m = _gpt_head_pat.match(text.strip())
    if m:
        tok = m.group(1).lower()
        if tok in {"true", "false"}:
            return tok.title()
        return "Unknown"

    low = text.lower()
    head = low[:120]  # heuristic window
    if "false" in head and "true" not in head:
        return "False"
    if "true" in head and "false" not in head:
        return "True"
    if any(k in low for k in ["insufficient", "unknown", "not enough", "cannot determine", "ambiguous", "uncertain"]):
        return "Unknown"
    return None  # couldn't confidently parse


def load_originality(path: Path):
    """
    Returns dict:
      fever_id -> {"claim": str|None, "gold": 'True'|'False'|'Unknown'|None, "originality": label|None}
    """
    out = {}
    for rec in iter_jsonl(path):
        fid = rec.get("fever_id")
        if fid is None:
            continue
        claim = rec.get("claim")
        gold = normalize_label(rec.get("gold"))

        label = None
        if rec.get("status_code") == 200:
            chk = rec.get("checker_response") or {}
            if chk.get("success"):
                data = chk.get("data") or {}
                results = data.get("results") or []
                if results:
                    label = normalize_label(results[0].get("classification"))

        out[fid] = {"claim": claim, "gold": gold, "originality": label}
    return out


def load_gpt(path: Path):
    """
    Returns dict:
      fever_id -> {"claim": str|None, "gold": 'True'|'False'|'Unknown'|None, "label": label|None}
    """
    out = {}
    for rec in iter_jsonl(path):
        fid = rec.get("fever_id")
        if fid is None:
            continue
        claim = rec.get("claim")
        gold = normalize_label(rec.get("gold"))

        label = None
        if rec.get("status") == "ok":
            label = parse_gpt_response_text(rec.get("response_text") or "")

        out[fid] = {"claim": claim, "gold": gold, "label": label}
    return out


def pick_first(*vals):
    """Return the first non-None, non-empty value."""
    for v in vals:
        if v not in (None, ""):
            return v
    return None


def main():
    args = parse_args()
    p_orig = Path(args.orig)
    p_g4o = Path(args.gpt4o)
    p_g5  = Path(args.gpt5)

    orig_map = load_originality(p_orig)
    g4o_map  = load_gpt(p_g4o)
    g5_map   = load_gpt(p_g5)

    all_ids = set(orig_map) | set(g4o_map) | set(g5_map)

    rows = []
    for fid in sorted(all_ids):
        orec = orig_map.get(fid, {})
        r4   = g4o_map.get(fid, {})
        r5   = g5_map.get(fid, {})

        row = {
            "fever_id": fid,
            "claim": pick_first(orec.get("claim"), r4.get("claim"), r5.get("claim")),
            "gold": pick_first(orec.get("gold"), r4.get("gold"), r5.get("gold")),
            "originality": orec.get("originality"),
            "gpt-4o": r4.get("label"),
            "gpt-5": r5.get("label"),
        }
        rows.append(row)

    all_df = pd.DataFrame(rows, columns=["fever_id", "claim", "gold", "originality", "gpt-4o", "gpt-5"])

    def has_disagreement(row) -> bool:
        labels = [row["gold"], row["originality"], row["gpt-4o"], row["gpt-5"]]
        labels = [x for x in labels if pd.notna(x) and x != ""]
        # If no labels or only one unique label, no disagreement
        return len(labels) > 1 and len(set(labels)) > 1

    disagreements_df = all_df[all_df.apply(has_disagreement, axis=1)].copy()

    # Output
    if args["out_all"] if isinstance(args, dict) else args.out_all:
        all_df.to_csv(args.out_all, index=False)
    if args["out_disagreements"] if isinstance(args, dict) else args.out_disagreements:
        disagreements_df.to_csv(args.out_disagreements, index=False)

    # Console preview
    print("\n=== Combined (sample) ===")
    print(all_df.head(10).to_string(index=False))
    print(f"\nTotal rows: {len(all_df)}")

    print("\n=== Disagreements (sample) ===")
    print(disagreements_df.head(10).to_string(index=False))
    print(f"\nDisagreement rows: {len(disagreements_df)}")


if __name__ == "__main__":
    main()
