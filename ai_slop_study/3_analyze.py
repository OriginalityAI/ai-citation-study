#!/usr/bin/env python3
# minimal evaluation: read JSONL -> confusion matrix -> metrics (binary true/false)

import json

INFILE = "checker_results.jsonl"

# normalize a label to {"true","false"} or None
def norm(label):
    if label is None:
        return None
    s = str(label).strip().lower()
    if s in {"true", "supports"}:
        return "true"
    if s in {"false", "refutes"}:
        return "false"
    return None  # anything else is skipped

# pull predicted label from one line
def get_pred(obj):
    try:
        return obj["checker_response"]["data"]["results"][0]["classification"]
    except Exception:
        return None

# confusion matrix:
# rows = gold (true,false), cols = pred (true,false)
# cm = [[TP_true, FN_true],
#       [FP_true, TN_true]]  (note: TN_true is TP for "false")
cm = [[0, 0],
      [0, 0]]

total = 0
evaluated = 0
skipped = 0

with open(INFILE, "r", encoding="utf-8") as f:
    for line in f:
        total += 1
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            skipped += 1
            continue

        gold = norm(obj.get("gold"))
        pred = norm(get_pred(obj))

        # only evaluate binary rows
        if gold not in {"true", "false"} or pred not in {"true", "false"}:
            print(f"{obj.get('fever_id')},{obj.get('claim')},{gold},{pred}")
            skipped += 1
            continue

        evaluated += 1
        gi = 0 if gold == "true" else 1
        pi = 0 if pred == "true" else 1
        cm[gi][pi] += 1

# derive metrics from cm
TP_t, FN_t = cm[0][0], cm[0][1]
FP_t, TN_t = cm[1][0], cm[1][1]

def prf1(tp, fp, fn):
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = (2*prec*rec)/(prec+rec) if (prec+rec) else 0.0
    return prec, rec, f1

# metrics for class "true"
p_true, r_true, f1_true = prf1(TP_t, FP_t, FN_t)

# metrics for class "false"
TP_f, FN_f = TN_t, FP_t
FP_f, TN_f = FN_t, TP_t
p_false, r_false, f1_false = prf1(TP_f, FP_f, FN_f)

support_true  = TP_t + FN_t
support_false = TP_f + FN_f
correct = TP_t + TN_t
acc = correct / evaluated if evaluated else 0.0

# print
print(f"Total lines: {total} | Evaluated: {evaluated} | Skipped: {skipped}\n")
print("Confusion Matrix [rows=gold, cols=pred] (true,false):")
print(f"[ [ {cm[0][0]:4d}, {cm[0][1]:4d} ],")
print(f"  [ {cm[1][0]:4d}, {cm[1][1]:4d} ] ]\n")

print(f"Accuracy: {acc:.3f}\n")

print("Precision / Recall / F1:")
print(f"  true : precision={p_true:.3f}  recall={r_true:.3f}  f1={f1_true:.3f}  support={support_true}")
print(f"  false: precision={p_false:.3f} recall={r_false:.3f} f1={f1_false:.3f} support={support_false}")

macro_f1 = (f1_true + f1_false) / 2
print(f"\nMacro-F1: {macro_f1:.3f}")
