#!/usr/bin/env python3
# Run GPT-4 and GPT-5 on FEVER 1k; save raw responses per model; resume; 500ms delay.
# Uses your requested init: load_dotenv(); client = openai.OpenAI(...)

import os, csv, json, time
from pathlib import Path
from dotenv import load_dotenv
import openai  # client = openai.OpenAI(...)

INPUT_CSV = Path("_claim_datasets/scifact_693.csv")
OUT_PATH = Path("_results/scifact_693")
ID_LABEL = 'scifact_id'
MODELS = ["gpt-4o"]    # hardcoded models
DELAY_SEC = 0.5                 # 500 ms between requests

SYSTEM_MSG = (
    "You are a careful fact-checking assistant. Decide if the claim is TRUE or FALSE. "
    "If uncertain, choose the most defensible option and note uncertainty briefly."
)
USER_TMPL = 'Claim:\n"{claim}"\n\nDecide TRUE or FALSE and explain briefly.'

def safe_model_filename(m: str) -> str:
    return m.replace("/", "_").replace(":", "_")

def load_done_ids(out_path: Path) -> set[int]:
    """Treat rows with status=='ok' as done (so failures retry next run)."""
    done = set()
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("status") == "ok" and isinstance(obj.get(ID_LABEL), int):
                        done.add(obj[ID_LABEL])
                except Exception:
                    pass
    return done

def run_for_model(client, model: str):
    out_file = OUT_PATH / Path(f"gpt_results_raw_{safe_model_filename(model)}.jsonl")

    # Load rows
    rows = []
    with INPUT_CSV.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                fid = int(r[ID_LABEL])
            except Exception:
                continue
            rows.append({ID_LABEL: fid, "claim": r["claim"], "gold": r.get("classification")})

    # Resume
    done = load_done_ids(out_file)
    to_run = [r for r in rows if r[ID_LABEL] not in done]
    total = len(to_run)
    if total == 0:
        print(f"[{model}] All {len(rows)} items already processed successfully. Nothing to do.")
        return

    with out_file.open("a", encoding="utf-8") as out_f:
        for i, r in enumerate(to_run, 1):
            fid, claim = r[ID_LABEL], r["claim"]
            try:
                resp = client.responses.create(
                    model=model,
                    instructions=SYSTEM_MSG,
                    input=[{"role": "user", "content": USER_TMPL.format(claim=claim)}],
                    temperature=0 if model != 'gpt-5' else None,
                )
                # Keep EXACT raw text; collapse newlines to a single line
                raw_text = resp.output_text if hasattr(resp, "output_text") else str(resp)
                one_line = raw_text.replace("\r", " ").replace("\n", " ").strip()

                print(one_line)

                record = {
                    ID_LABEL: fid,
                    "claim": claim,
                    "gold": r["gold"],
                    "model": model,
                    "status": "ok",
                    "response_text": one_line,
                }
                print(f"[{model}] ({i} / {total}) id={fid} status=ok")
            except Exception as e:
                record = {
                    ID_LABEL: fid,
                    "claim": claim,
                    "gold": r["gold"],
                    "model": model,
                    "status": "error",
                    "error": repr(e),
                }
                print(f"[{model}] ({i} / {total}) id={fid} status=error")

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()
            time.sleep(DELAY_SEC)

    print(f"[{model}] Done. Appended {total} rows to {out_file.resolve()}")

def main():
    load_dotenv()
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing {INPUT_CSV.resolve()}")

    for m in MODELS:
        run_for_model(client, m)

if __name__ == "__main__":
    main()
