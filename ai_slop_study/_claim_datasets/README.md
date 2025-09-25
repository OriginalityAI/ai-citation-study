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

4.  2025-09-13 16:15:10 | INFO | Progress: 3283/153543 | ok=3272, fail=11, no_text=0 | elapsed=22h 3m 55s | eta=1009h 54m 12s
    2025-09-13 16:15:10 | INFO | (3284/153543) Submitting to checker | url=https://www.msmunify.com/study-in-australia/student-visa | chars=5000 | class=Human

5.  2025-09-14 19:18:28 | INFO | Progress: 3191/150271 | ok=3155, fail=36, no_text=0 | elapsed=26h 41m 37s | eta=1230h 21m 39s
    2025-09-14 19:18:28 | INFO | (3192/150271) Submitting to checker | url=https://my.clevelandclinic.org/health/diseases/21859-anosmia-loss-of-sense-of-smell | chars=5000 | class=Human

6.  2025-09-15 21:27:22 | INFO | Progress: 2860/147116 | ok=2852, fail=8, no_text=0 | elapsed=26h 7m 12s | eta=1317h 28m 1s
    2025-09-15 21:27:22 | INFO | (2861/147116) Submitting to checker | url=https://www.sandstonecare.com/blog/generational-trauma | chars=5000 | class=Human

7.  2025-09-15 21:57:54 | INFO | Progress: 56/146990 | ok=56, fail=0, no_text=0 | elapsed=28m 47s | eta=1258h 53m 32s
    2025-09-15 21:57:54 | INFO | (57/146990) Submitting to checker | url=https://stwserve.com/understanding-fers-disability-retirement-rules-2 | chars=5000 | class=Human

8.  2025-09-18 04:34:52 | INFO | Progress: 3671/146935 | ok=3646, fail=25, no_text=0 | elapsed=39h 11m 9s | eta=1529h 16m 0s
    2025-09-18 04:34:52 | INFO | (3672/146935) Submitting to checker | url=https://www.bhlsi.com/blog/spotting-the-warning-signs-of-lung-cancer | chars=5000 | class=Human

9.  2025-09-18 16:42:46 | INFO | Progress: 1023/143289 | ok=1006, fail=17, no_text=0 | elapsed=12h 6m 29s | eta=1683h 49m 44s
    2025-09-18 16:42:46 | INFO | (1024/143289) Submitting to checker | url=https://theconversation.com/kids-put-down-the-snails-they-could-carry-rat-lungworm-50183 | chars=4999 | class=Human

10. (AI only) 2025-09-25 11:45:32 | INFO | Progress: 5384/14286 | ok=5360, fail=24, no_text=0 | elapsed=44h 23m 37s | eta=73h 24m 5s
    2025-09-25 11:45:32 | INFO | (5385/14286) Submitting to checker | url=https://www.economicsonline.co.uk/definitions/regressive-taxes.html | chars=4999 | class=AI
