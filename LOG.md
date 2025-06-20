# Ouroboros – Weekly Progress Log

---

## Week of June 17–24

- Refined research question: analyze `P(cited | AI-generated)` vs `P(cited | human-written)`
- Planned new data collection and citation analysis strategy (use organic results as the ref set)
- TODO: Increase number of organic results (N) in SerpAPI queries
- TODO: Create WTAO_v2 with improved accuracy
- TODO: Extract URLs from AI Overview citations and organic results, combine into one CSV with columns: `url`, `cited_count`, `in_organic_results_count`
- TODO: Use Originality Batch API to add the `ai_prob` column
- TODO: Review GEO paper and its dataset

---

## Week of June 10–17

- Received project brief and access credentials
- Set up accounts and tools
- Reviewed prior studies and selected MS MARCO (9M+ Bing queries)
- Chose SerpAPI for querying Google AI Overview
- Integrated SerpAPI into the codebase for batch collection
- Built and tested initial data collection pipeline
- Sampled 50 queries and evaluated v1 trigger filter (~62% success)
