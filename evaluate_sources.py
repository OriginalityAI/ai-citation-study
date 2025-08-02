#!/usr/bin/env python3
import os
import csv
import json
import re
from dotenv import load_dotenv
import openai

# ==== CONFIG ====
INPUT_CSV = "legal_ai_citations.csv"
JSON_DIR = "samples/ymyl_29000/res_20250723_n100"
SCRAPED_CSV = "samples/ymyl_29000/res_20250723_n100/_scraped.csv"
OUTPUT_CSV = "support_eval_minimal.csv"
MODEL = "gpt-4.1-nano-2025-04-14"
# ================

SYSTEM_PROMPT = """You are a careful fact-checking assistant. Your task is to judge whether a specific SOURCE supports the CLAIM made in an AI Overview snippet, given the original QUERY context.

Return one of the categories and a concise rationale:

Categories (choose exactly one):
- supports: The source directly substantiates the claim.
- partially_supports: The source is relevant and offers partial or qualified support; key parts are missing/uncertain.
- refutes: The source contradicts the claim.
- unrelated: The source does not address the claim.

Guidelines:
- Focus on whether the SOURCE content, as provided, supports the CLAIM.
- If the claim is broader than the source, but the supported portion still aligns, consider partially_supports.
- If the source is paywalled/boilerplate with no substantive content in the provided excerpt, choose unrelated unless it clearly refutes.
- Quote very sparingly from the source (<= 20 words total) if needed. Prefer paraphrase.
Respond in JSON with fields: {"category": <one of the categories>, "rationale": <string>}."""

def normalize_url(url):
    return url.split("#")[0].split("?")[0].rstrip("/")

def extract_text(resp):
    """Try multiple ways to extract model text output from OpenAI response."""
    if hasattr(resp, "output") and hasattr(resp.output, "text") and resp.output.text:
        return resp.output.text
    if hasattr(resp, "output") and isinstance(resp.output, list):
        collected = []
        for o in resp.output:
            if hasattr(o, "content"):
                for c in o.content:
                    if "text" in c and isinstance(c["text"], str):
                        collected.append(c["text"])
        if collected:
            return "\n".join(collected)
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    return ""

def safe_parse_json(text):
    """Attempt to parse possibly malformed JSON by fixing common issues."""
    # Fix missing quotes around category values
    text = re.sub(r'("category"\s*:\s*)(supports|refutes|unrelated|partially_supports)',
                  r'\1"\2"', text)
    # Ensure valid JSON quotes
    try:
        return json.loads(text)
    except Exception:
        return None

def main():
    # Load key
    load_dotenv()
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Load scraped content
    url_content = {}
    with open(SCRAPED_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            url_content[normalize_url(row["url"])] = row["content"]

    total = sum(1 for _ in open(INPUT_CSV, encoding='utf-8')) - 1
    processed = 0

    with open(INPUT_CSV, newline='', encoding='utf-8') as f_in, \
         open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=["query_id", "query_text", "url", "snippet", "support_category", "rationale"])
        writer.writeheader()

        for row in reader:
            qid = row["query_id"]
            query = row["query_text"]
            url = row["url"]
            norm_url = normalize_url(url)
            processed += 1

            print(f"[{processed}/{total}] Processing query_id={qid}...", flush=True)

            json_path = os.path.join(JSON_DIR, f"{qid}.json")
            if not os.path.exists(json_path):
                print("   Skipped: JSON not found", flush=True)
                continue

            with open(json_path, encoding='utf-8') as jf:
                data = json.load(jf).get("ai_overview", {})

            # Find snippets citing this URL
            ref_indices = [r["index"] for r in data.get("references", []) if normalize_url(r.get("link","")) == norm_url]
            snippets = []

            for blk in data.get("text_blocks", []):
                if blk.get("type") in ("paragraph", "heading"):
                    if any(i in ref_indices for i in blk.get("reference_indexes", [])):
                        snippets.append(blk.get("snippet", ""))
                elif blk.get("type") == "list":
                    for it in blk.get("list", []):
                        if any(i in ref_indices for i in it.get("reference_indexes", [])):
                            snippets.append(it.get("snippet", ""))

            if not snippets:
                print("   Skipped: No matching snippets", flush=True)
                continue

            content = url_content.get(norm_url, "")

            for snip in snippets:
                prompt = f"""QUERY:\n{query}\n\nCLAIM:\n{snip}\n\nSOURCE CONTENT:\n{content[:2000]}"""
                try:
                    resp = client.responses.create(
                        model=MODEL,
                        input=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                        max_output_tokens=200
                    )

                    text = extract_text(resp)

                    if not text.strip():
                        print("   ⚠️ Empty model output", flush=True)
                        cat = "unrelated"
                        rat = "Model returned no content"
                    else:
                        parsed = safe_parse_json(text)
                        if parsed:
                            cat = parsed.get("category", "")
                            rat = parsed.get("rationale", "")
                            print(f"   ✅ Result: {cat}", flush=True)
                        else:
                            print(f"   ⚠️ Non-JSON model output: {text[:100]}...", flush=True)
                            cat = "unrelated"
                            rat = text.strip()

                except Exception as e:
                    cat = "unrelated"
                    rat = f"Model error: {e}"
                    print(f"   ⚠️ Error: {e}", flush=True)

                writer.writerow({
                    "query_id": qid,
                    "query_text": query,
                    "url": url,
                    "snippet": snip,
                    "support_category": cat,
                    "rationale": rat
                })

    print("✅ Done processing all rows.")

if __name__ == "__main__":
    main()
