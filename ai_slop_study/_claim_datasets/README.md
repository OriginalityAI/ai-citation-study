Claims used for testing the fact checker.
Only True/False claims were used.

- `fever_1k.csv` - randomly sampled 1k True/False claims from [FEVER shared task](https://fever.ai/dataset/fever.html)
- `fever_1k_fixed.csv` - `fever_1k` with dropped ambiguous claims and fixed labels
- `scifact_693.csv` - [SciFact](https://arxiv.org/abs/2004.14974) 1409 claims filtered down to 693 True/False
- `averitec_3018.csv` - [AVeriTec](https://arxiv.org/abs/2305.13117) 4568 + 1215 claims filtered down to 3017 True/False

---

SERP Progress log

1.  2025-09-10 17:49:01 | INFO | Progress: 3591/163911 | ok=3566, fail=25, no_text=0 | elapsed=25h 7m 40s | eta=1121h 49m 46s
    2025-09-10 17:49:01 | INFO | (3592/163911) Submitting to checker | url=https://www.medicalnewstoday.com/articles/322101 | chars=4999 | class=Human

2.  2025-09-11 21:30:18 | INFO | Progress: 3894/160353 | ok=3875, fail=19, no_text=0 | elapsed=27h 40m 3s | eta=1111h 39m 57s
    2025-09-11 21:30:18 | INFO | (3895/160353) Submitting to checker | url=https://katiecouric.com/lifestyle/workplace/american-workers-vacation-guilt | chars=5000 | class=Human

3.  2025-09-12 17:45:00 | INFO | Progress: 2949/156479 | ok=2936, fail=13, no_text=0 | elapsed=20h 11m 48s | eta=1051h 28m 32s
    2025-09-12 17:45:00 | INFO | (2950/156479) Submitting to checker | url=https://www.freedomfromdiabetes.org/blog/post/relation%20between%20hypertension%20(bp)%20and%20diabetes/2618 | chars=5000 | class=Human
