#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Usage:
#   python export_fever_evidence_txt.py \
#       --csv gold_incorrect.csv \
#       --fever_json shared_task_dev.jsonl \
#       --wiki_dir wiki-pages \
#       --out report.txt
#
# CSV requirements:
#   - Prefer a column named "id" (int). If missing, it will try "statement" or "claim".
#   - If both id and statement/claim exist, id match is used.
#
# Output format (per row):
#   ID: ...
#   Claim: ...
#   Gold Label: ...
#   Evidence:
#     - Evidence set 1:
#       - Title#idx: sentence text
#       - ...
#     - Evidence set 2:
#       - ...
#
import os, json, csv, glob, argparse
from typing import Dict, List, Tuple, Set

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to gold_incorrect.csv")
    ap.add_argument("--fever_json", required=True, help="Path to shared_task_dev.jsonl (FEVER)")
    ap.add_argument("--wiki_dir", required=True, help="Directory with wiki-*.jsonl shards (unzipped wiki-pages.zip)")
    ap.add_argument("--out", default="report.txt", help="Output .txt file")
    return ap.parse_args()

def parse_lines_blob(blob: str) -> List[str]:
    """Convert '0\\tSentence\\n1\\tSentence...' to an indexable list."""
    lines: List[str] = []
    for row in blob.split("\n"):
        if not row.strip():
            continue
        if "\t" in row:
            n_str, txt = row.split("\t", 1)
            try:
                n = int(n_str)
            except ValueError:
                continue
            if n >= len(lines):
                lines.extend([""] * (n - len(lines) + 1))
            lines[n] = txt
    return lines

def load_requests_from_csv(path: str) -> List[Tuple[int, str]]:
    """
    Return a list of requested items as (id_or_-1, claim_text_or_empty).
    Priority is ID if present; otherwise fall back to statement/claim text.
    """
    reqs: List[Tuple[int, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Guess column names
        cols = {c.lower(): c for c in reader.fieldnames or []}
        id_col = cols.get("id")
        text_col = cols.get("statement") or cols.get("claim") or cols.get("text")
        for row in reader:
            cid = -1
            if id_col and row.get(id_col, "").strip():
                try:
                    cid = int(row[id_col])
                except ValueError:
                    cid = -1
            text = ""
            if text_col:
                text = (row.get(text_col) or "").strip()
            if cid == -1 and not text:
                # nothing usable on this row; skip
                continue
            reqs.append((cid, text))
    return reqs

def index_fever_by_id_and_claim(jsonl_path: str):
    """
    Scan shared_task_dev.jsonl and build:
      - by_id:    id -> example
      - by_claim: claim_text -> list of examples (usually 1)
    """
    by_id: Dict[int, dict] = {}
    by_claim: Dict[str, List[dict]] = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            ex = json.loads(line)
            cid = ex.get("id")
            claim = ex.get("claim") or ""
            if isinstance(cid, int):
                by_id[cid] = ex
            if claim:
                by_claim.setdefault(claim, []).append(ex)
    return by_id, by_claim

def gather_titles_needed(examples: List[dict]) -> Set[str]:
    titles: Set[str] = set()
    for ex in examples:
        for ev_set in ex.get("evidence", []):
            for row in ev_set:
                if len(row) >= 4 and row[2] and isinstance(row[3], int) and row[3] >= 0:
                    titles.add(row[2])
    return titles

def build_title_index_for_titles(wiki_dir: str, needed_titles: Set[str]) -> Dict[str, List[str]]:
    """
    Stream wiki shards and collect only the titles we need.
    Returns: title -> list_of_lines
    """
    needed = set(needed_titles)
    out: Dict[str, List[str]] = {}
    shards = sorted(glob.glob(os.path.join(wiki_dir, "wiki-*.jsonl")))
    if not shards:
        raise FileNotFoundError(f"No wiki shards found under {wiki_dir}/")
    for shard in shards:
        if not needed:
            break
        with open(shard, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                tid = obj.get("id")
                if tid in needed:
                    blob = obj.get("lines") or obj.get("text") or ""
                    out[tid] = parse_lines_blob(blob)
                    needed.remove(tid)
                    if not needed:
                        break
    return out

def evidence_text_sets(ex: dict, title_to_lines: Dict[str, List[str]]) -> List[List[str]]:
    """
    For a FEVER example, return a list of evidence sets;
    each set is a list of human-readable sentences.
    """
    all_sets: List[List[str]] = []
    for ev_set in ex.get("evidence", []):
        set_text: List[str] = []
        for row in ev_set:
            if len(row) >= 4:
                title, idx = row[2], row[3]
                lines = title_to_lines.get(title)
                if lines is not None and isinstance(idx, int) and 0 <= idx < len(lines):
                    set_text.append(lines[idx])
                else:
                    set_text.append(f"[missing: {title}#{idx}]")
        if set_text:
            all_sets.append(set_text)
    return all_sets

def main():
    args = parse_args()

    # 1) Requests from CSV
    requests = load_requests_from_csv(args.csv)
    if not requests:
        raise SystemExit("No usable rows found in CSV (need 'id' or 'statement/claim').")

    # 2) Index FEVER jsonl
    by_id, by_claim = index_fever_by_id_and_claim(args.fever_json)

    # 3) Resolve requests to FEVER examples
    resolved: List[dict] = []
    for (cid, text) in requests:
        ex = None
        if cid != -1:
            ex = by_id.get(cid)
        if ex is None and text:
            matches = by_claim.get(text, [])
            ex = matches[0] if matches else None
        if ex is not None:
            resolved.append(ex)

    if not resolved:
        raise SystemExit("No matching FEVER examples found for the CSV rows.")

    # 4) Collect titles and build a minimal title->lines index
    needed = gather_titles_needed(resolved)
    title_to_lines = build_title_index_for_titles(args.wiki_dir, needed)

    # 5) Write report
    with open(args.out, "w", encoding="utf-8") as fout:
        for ex in resolved:
            cid = ex.get("id")
            claim = ex.get("claim") or ""
            label = ex.get("label") or ""
            fout.write(f"ID: {cid}\n")
            fout.write(f"Claim: {claim}\n")
            fout.write(f"Gold Label: {label}\n")
            fout.write("Evidence:\n")

            sets = evidence_text_sets(ex, title_to_lines)
            if not sets:
                fout.write("  (No evidence sets)\n\n")
                continue

            for k, s in enumerate(sets, 1):
                fout.write(f"  - Evidence set {k}:\n")
                # Reprint with Title#idx marker too (handy for spot checks)
                ev_set = ex["evidence"][k-1]
                for j, sent in enumerate(s):
                    title, idx = ev_set[j][2], ev_set[j][3]
                    fout.write(f"    - {title}#{idx}: {sent}\n")
            fout.write("\n")

    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
