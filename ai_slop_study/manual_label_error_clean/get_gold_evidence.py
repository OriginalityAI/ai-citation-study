#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Usage:
#   python rewrite_disagree_with_evidence.py \
#       --disagree disagree.csv \
#       --fever_json shared_task_dev.jsonl \
#       --wiki_dir wiki-pages
#
# This will:
#   - create disagree.csv.bak (backup)
#   - rewrite disagree.csv adding a 'gold_evidence' column (single safe string)
#
import os, json, glob, csv, argparse, shutil
from typing import Dict, List, Set, Iterable

# ---------- FEVER/wiki helpers ----------

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

def index_fever_subset(jsonl_path: str, ids: Set[int]) -> Dict[int, dict]:
    """Return {id -> FEVER example} only for the requested ids."""
    by_id: Dict[int, dict] = {}
    wanted = set(ids)
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not wanted:
                break
            ex = json.loads(line)
            cid = ex.get("id")
            if isinstance(cid, int) and cid in wanted:
                by_id[cid] = ex
                wanted.remove(cid)
    return by_id

def gather_titles_needed_for_ids(fever_by_id: Dict[int, dict], ids: Iterable[int]) -> Set[str]:
    titles: Set[str] = set()
    for cid in ids:
        ex = fever_by_id.get(cid)
        if not ex:
            continue
        for ev_set in ex.get("evidence", []):
            for row in ev_set:
                # FEVER evidence row: [annotator_id, evidence_id, title, sent_idx]
                if len(row) >= 4 and row[2] and isinstance(row[3], int) and row[3] >= 0:
                    titles.add(row[2])
    return titles

def build_title_index_for_titles(wiki_dir: str, needed_titles: Set[str]) -> Dict[str, List[str]]:
    """
    Stream wiki shards (wiki-*.jsonl) and collect only the titles we need.
    Returns: {title -> [sentences by index]}.
    """
    need = set(needed_titles)
    out: Dict[str, List[str]] = {}
    shards = sorted(glob.glob(os.path.join(wiki_dir, "wiki-*.jsonl")))
    if not shards:
        raise FileNotFoundError(f"No wiki shards found under {wiki_dir}/")
    for shard in shards:
        if not need:
            break
        with open(shard, "r", encoding="utf-8") as f:
            for line in f:
                if not need:
                    break
                obj = json.loads(line)
                tid = obj.get("id")
                if tid in need:
                    blob = obj.get("lines") or obj.get("text") or ""
                    out[tid] = parse_lines_blob(blob)
                    need.remove(tid)
    return out

def _squash(s: str) -> str:
    """Collapse any whitespace (incl. newlines/tabs) into single spaces."""
    return " ".join((s or "").split())

def gold_evidence_string(
    fever_id: int,
    fever_by_id: Dict[int, dict],
    title_to_lines: Dict[str, List[str]],
) -> str:
    """
    Return a single-line 'safe' gold-evidence string for a FEVER example.
    - No newlines/tabs; extra whitespace collapsed to single spaces.
    - Per sentence: 'Title#idx: sentence'
    - Emits 'Title#idx: [missing]' if the sentence can't be located.
    - Returns '' if id not found or no evidence.
    """
    ex = fever_by_id.get(fever_id)
    if not ex:
        return ""
    parts: List[str] = []
    for ev_set in ex.get("evidence", []):
        for row in ev_set:
            if len(row) >= 4:
                title, idx = row[2], row[3]
                lines = title_to_lines.get(title)
                if isinstance(idx, int) and lines is not None and 0 <= idx < len(lines):
                    parts.append(f"{title}#{idx}: {lines[idx]}")
                else:
                    parts.append(f"{title}#{idx}: [missing]")
    return _squash(" ".join(parts))

# ---------- Script I/O ----------

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disagree", required=True, help="Path to disagree.csv")
    ap.add_argument("--fever_json", required=True, help="Path to shared_task_dev.jsonl (FEVER)")
    ap.add_argument("--wiki_dir", required=True, help="Directory with wiki-*.jsonl shards")
    ap.add_argument("--no_backup", action="store_true", help="Do not create disagree.csv.bak")
    return ap.parse_args()

def main():
    args = parse_args()
    disagree_path = args.disagree

    # Read rows
    with open(disagree_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise SystemExit("disagree.csv has no data rows.")
        fieldnames = list(reader.fieldnames or [])
        if "gold_evidence" not in fieldnames:
            fieldnames.append("gold_evidence")

    # Collect FEVER ids
    target_ids: Set[int] = set()
    for r in rows:
        try:
            target_ids.add(int(r.get("fever_id")))
        except (TypeError, ValueError):
            pass
    if not target_ids:
        raise SystemExit("No valid 'fever_id' values found in disagree.csv.")

    # Build indices once
    fever_by_id = index_fever_subset(args.fever_json, target_ids)
    needed_titles = gather_titles_needed_for_ids(fever_by_id, target_ids)
    title_to_lines = build_title_index_for_titles(args.wiki_dir, needed_titles)

    # Augment rows
    augmented = []
    for r in rows:
        fid = None
        try:
            fid = int(r.get("fever_id"))
        except (TypeError, ValueError):
            pass
        ev = gold_evidence_string(fid, fever_by_id, title_to_lines) if fid is not None else ""
        nr = dict(r)
        nr["gold_evidence"] = ev
        augmented.append(nr)

    # Backup, then rewrite in place
    if not args.no_backup:
        shutil.copyfile(disagree_path, disagree_path + ".bak")
    with open(disagree_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(augmented)

    print(f"Rewrote {disagree_path} with 'gold_evidence' column "
          f"(backup: {'skipped' if args.no_backup else disagree_path + '.bak'}).")

if __name__ == "__main__":
    main()
