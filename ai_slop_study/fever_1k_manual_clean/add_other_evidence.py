#!/usr/bin/env python3
# add_evidence_columns_hardcoded.py

import csv, json, shutil
from pathlib import Path

# --- hardcoded paths ---
DISAGREE_CSV = Path("manual_label_error_clean/disagree.csv")
ORIG_JSONL   = Path("checker_results.jsonl")
G4O_JSONL    = Path("gpt_results_raw_gpt-4o.jsonl")
G5_JSONL     = Path("gpt_results_raw_gpt-5.jsonl")

def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def squash(s: str) -> str:
    return " ".join((s or "").split())

def load_originality_evidence(path: Path):
    """fever_id -> single-line evidence (explanation + compact sources)"""
    out = {}
    for rec in iter_jsonl(path):
        fid = rec.get("fever_id")
        if fid is None:
            continue
        ev = ""
        cr = rec.get("checker_response") or {}
        if cr.get("success"):
            data = cr.get("data") or {}
            results = data.get("results") or []
            if results:
                r0 = results[0]
                expl = r0.get("explanation") or ""
                sources = r0.get("sources") or []
                bits = []
                for s in sources:
                    t = s.get("title") or ""
                    u = s.get("url") or ""
                    if t and u: bits.append(f"{t} ({u})")
                    elif t:     bits.append(t)
                    elif u:     bits.append(u)
                src_txt = f" Sources: {'; '.join(bits)}" if bits else ""
                ev = squash(expl + src_txt)
        try:
            out[int(fid)] = ev
        except (TypeError, ValueError):
            pass
    return out

def load_gpt_evidence(path: Path):
    """fever_id -> single-line evidence from response_text"""
    out = {}
    for rec in iter_jsonl(path):
        fid = rec.get("fever_id")
        if fid is None:
            continue
        try:
            out[int(fid)] = squash(rec.get("response_text") or "")
        except (TypeError, ValueError):
            pass
    return out

def main():
    # load evidence maps
    orig_map = load_originality_evidence(ORIG_JSONL)
    g4o_map  = load_gpt_evidence(G4O_JSONL)
    g5_map   = load_gpt_evidence(G5_JSONL)

    # read CSV
    with DISAGREE_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise SystemExit("disagree.csv has no data rows.")
        fieldnames = list(reader.fieldnames or [])

    # ensure new columns exist
    for col in ("originality_evidence", "gpt-4o_evidence", "gpt-5_evidence"):
        if col not in fieldnames:
            fieldnames.append(col)

    # augment
    for r in rows:
        try:
            fid = int(r.get("fever_id"))
        except (TypeError, ValueError):
            fid = None
        r["originality_evidence"] = orig_map.get(fid, "") if fid is not None else ""
        r["gpt-4o_evidence"]      = g4o_map.get(fid, "")  if fid is not None else ""
        r["gpt-5_evidence"]       = g5_map.get(fid, "")   if fid is not None else ""

    # backup and rewrite in place
    shutil.copyfile(DISAGREE_CSV, DISAGREE_CSV.with_suffix(DISAGREE_CSV.suffix + ".bak"))
    with DISAGREE_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"updated {DISAGREE_CSV} (+ .bak backup)")

if __name__ == "__main__":
    main()
