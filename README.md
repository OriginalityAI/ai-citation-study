# OUROBOROS

## Research Questions

- What is the likelihood of AI content to be cited in AI Overviews? What is the correlation of AI content being cited in AI overview vs human content being cited in AI overviews? (positive correlation or negative correlation?)
- What proportion of sources cited in Google AI Overviews are AI-generated?
- How is AI/human ratio distributed across different query topics?
- What queries do not result in an AI summary? Which queries result in "An AI Overview is not available for this search"?
- Does this impact the quality of overviews?
- What are the implications for SEO?

## Project Setup

1. Download the [MS MARCO queries dataset](https://msmarco.z22.web.core.windows.net/msmarcowebsearch/100M_queries/queries_train.tsv) (9.2M real Bing queries) and save it as `/dataset/ms-marco-web-search-queries.tsv`.

## Project Structure

- `/datasets` - all source datasets.
- `/samples` - contains sampled queries from MS MARCO dataset.
  - e.g. folder named `v1_50` means `v1` filter was used (filters out queries that are unlikely to trigger AI overviews) and 50 queries were randomly sampled
  - Files prefixed with `queries_` contain queries and their unique IDs
  - Query files postfixed with `_labeled` contain an additional `triggered_ai_overview` column:
    - `y`: query triggers an AI overview
    - `n`: no AI overview
    - `b`: attempted to show an AI overview, but blocked by Google's policies ("
      An AI Overview is not available for this search" is displayed). E.g. `why liberals hate america` query.

## Related Work

- **[GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735)** - a large-scale benchmark of diverse user queries across multiple domains, along with relevant web sources to answer these queries. Through rigorous evaluation, we demonstrate that GEO can boost visibility by up to 40% in generative engine responses.

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

1. **Sample Queries**  
   Generate or select a large set of queries predicted to trigger AI Overviews using the WTAO filter.

2. **Run Queries & Collect Responses**  
   For each query, retrieve:

- AI Overview response with all cited URLs
- Top N organic search result URLs (configurable N, e.g., 10 or 20)

3. **Combine & Deduplicate URLs**  
   Merge URLs from both organic results and AI Overview citations.  
   Normalize URLs to avoid duplicates (e.g., remove query parameters, consistent casing).  
   Deduplicate to create a master pool of unique URLs.

4. **Label URLs with Citation & Organic Counts**  
   For each URL, track:

- `cited_count`: Number of times cited by AI Overviews across all queries
- `in_organic_results_count`: Number of times appearing in organic results

5. **Classify URLs as AI-generated or Human-written**  
   Use Originality.ai Batch Scan API to classify each URL's content.  
   Store classification results including confidence scores and labels.

6. **Calculate Citation Probabilities and Analyze**  
   Compute conditional probabilities:

   - P(cited | AI-generated) = (# cited AI URLs) / (# total AI URLs)

   - P(cited | human-written) = (# cited human URLs) / (# total human URLs)

   Analyze citation frequency distributions, overlap ratios, and trends over time or by query category.

## Timeline

- **Week 1 (June 9+):** Plan the study and outline the data collection pipeline
- **Week 2 (June 16+):** Set up Originality.ai API for classification, increase SerpAPI query access, improve AI Overview filtering
- **Week 3 (June 23+):** Start scaling up the number of samples and get early results on AI vs human citation ratios
- **Week 4 (June 30+):** Analyze main results and start drafting the paper
- **Weeks 5–7 (July 7+):** Explore secondary questions, refine insights, document insights with supporting graphics and plots
- **Week 8 (July 28+):** Draft the blog post and prepare it for publishing
- **Week 9 (August 4+):** Finalize the paper and prepare for publishing

## WTAO Filter Stats

| Version | Sample Size | Y   | N   | B   |
| ------- | ----------- | --- | --- | --- |
| v1      | 50          | 48% | 18% | 34% |
