## Research Questions

- What is the likelihood of AI content to be cited in AI Overviews? What is the correlation of AI content being cited in AI overview vs human content being cited in AI overviews? (positive correlation or negative correlation?)
- What proportion of sources cited in Google AI Overviews are AI-generated?
- How is AI/human ratio distributed across different query topics?
- What queries do not result in an AI summary? Which queries result in "An AI Overview is not available for this search"?
- Does this impact the quality of overviews?
- What are the implications for SEO?

## Related Work

- **[How Deep Do Large Language Models Internalize Scientific Literature and Citation Practices? (arXiv:2504.02767)](https://arxiv.org/abs/2504.02767)** - analyzes ~275,000 GPT‑4 citations across 10,000 simulated papers, revealing a systematic preference for highly cited, recent sources. The “rich get richer” effect in AI-generated references.

- **[From Content Creation to Citation Inflation: A GenAI Case Study](https://arxiv.org/abs/2503.23414)**
  Examines AI-generated papers that cite each other, artificially boosting each other's credibility.

**Model collapse when training on AI data:**

- **[The Curse of Recursion: Training on Generated Data Makes Models Forget (Shumailov et al., 2023)](https://arxiv.org/abs/2305.17493)** - lose diversity and information over time
- **[AI models collapse when trained on recursively generated data (Nature, 2024)](https://www.nature.com/articles/s41586-024-07566-y)** - degrade in quality and accuracy

## Data Collection

### Online Query Datasets

| Dataset                                                                          | # Queries   | Recency | Source Type               | Notes                                                 |
| -------------------------------------------------------------------------------- | ----------- | ------- | ------------------------- | ----------------------------------------------------- |
| **[MS MARCO Web Search](https://github.com/microsoft/MSMARCO-Document-Ranking)** | ~10 million | ~2024   | Human (Bing search logs)  | Real-world queries; main dataset                      |
| **[ORCAS](https://microsoft.github.io/msmarco/ORCAS)**                           | ~10 million | ~2020   | Human (click logs)        | Includes query-document pairs with user click signals |
| **[Natural Questions](https://ai.google.com/research/NaturalQuestions)**         | ~320,000    | ~2019   | Human (Google QA queries) | QA-focused dataset with gold answers                  |

We selected **MS MARCO Web Search** as our primary dataset because:

- Large, diverse set of **real** user queries from Bing
- Recency (2024), reflecting modern search behavior
- Representative of average user search, covers a wide range of query types
- Well documented and formatted

## Data Collection Pipeline

1. **Start with MS MARCO (9M)**

   - Large, recent, real-world queries

2. **Filter likely AI Overview queries**

   - Heuristics: "what is", "how to", etc.

3. **Randomly sample filtered queries**

   - Ensures topic and phrasing diversity

4. **Fetch AI Overviews via SerpAPI**

   - Save response and citations
   - Label as Y / N / B
   - Purchase a plan (see pricing table below)

5. **Refine filtering (next batches)**

   - Use failed queries to improve heuristics

6. **Classify cited sources**

   - Fetch content
   - Use Originality.ai (cache duplicates)
   - Label as AI / Human

7. **Analyze data**

   - Compute AI vs Human ratios
   - Plot trends by topic/query type

8. **(Optional) Classify queries by topic**
   - Use GPT API
   - ~50 USD to label 100,000 queries

### SerpAPI Pricing Plans

| Plan       | Cost (USD) | Queries | Price per Query (USD) |
| ---------- | ---------- | ------- | --------------------- |
| Developer  | $75        | 5,000   | $0.015                |
| Production | $150       | 15,000  | $0.010                |
| Big Data   | $275       | 30,000  | $0.009                |
| Searcher   | $725       | 100,000 | $0.007                |
| Volume     | $1,475     | 250,000 | $0.006                |

We chose SerpAPI over other tools like Octoparse or custom scrapers because it's easier to use, more stable, and less likely to get blocked.

## Timeline

- **Week 1 (June 9+):** Plan the study and outline the data collection pipeline
- **Week 2 (June 16+):** Set up Originality.ai API for classification, increase SerpAPI query access, improve AI Overview filtering
- **Week 3 (June 23+):** Start scaling up the number of samples and get early results on AI vs human citation ratios
- **Week 4 (June 30+):** Analyze main results and start drafting the paper
- **Weeks 5–7 (July 7+):** Explore secondary questions, refine insights, document insights with supporting graphics and plots
- **Week 8 (July 28+):** Draft the blog post and prepare it for publishing
- **Week 9 (August 4+):** Finalize the paper and prepare for publishing

## Likely-to-Trigger AI Overview Filter Stats

| Version | Sample Size | Y   | N   | B   |
| ------- | ----------- | --- | --- | --- |
| v1      | 50          | 48% | 18% | 34% |
