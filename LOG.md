# Ouroboros – Weekly Progress Log

## Week of June 24–July 1

- TODO: Create WTAO_v2 with higher AI overview rate (> 50%)
- TODO: Collect a larger v2 sample
- TODO: Combine data into 1 CSV with columns: `url`, `cited_count`, `in_organic_results_count`
- TODO: Use Originality Batch API to add the `ai_prob` column

---

## Week of June 17–24

- Refined research question: analyze `P(cited | AI-generated)` vs `P(cited | human-written)`
- Planned new data collection and citation analysis strategy (use organic results as the ref set)
- Write a script that calculates citation presence
- Found an optimal number of organic results (N=40) with high citation presence (53%)
- Review GEO paper and its dataset

---

## Week of June 10–17

- Received project brief and access credentials
- Set up accounts and tools
- Reviewed prior studies and selected MS MARCO (9M+ Bing queries)
- Chose SerpAPI for querying Google AI Overview
- Integrated SerpAPI into the codebase for batch collection
- Built and tested initial data collection pipeline
- Sampled 50 queries and evaluated v1 trigger filter (~62% success)
