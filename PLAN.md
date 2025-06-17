## Research Questions

- **What proportion of sources cited in Google AI Overviews are AI-generated?**
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

Dataset comparison (ORCA vs MS MARCO vs ..)
a table
number of queries, recency, source (human or not), relevancy (human queries that trigger AI overview)

filter queries to those that will trigger AI overview,
then random sampling (justify)

genarate a sample from 9M queries

get AI overview responses + citations for the sample, label them as y/n/b

(for next batch, identify which queries don't trigger AI overview and improve filter to maximize number of collected AI overviews)

fetch cited sources and run their content through Originality AI API (cache duplicates) classify as AI/human

analyze collected data

future:
maybe classify queries by topic using GPT API, add cost, value

## Timeline

- **Week 1 (June 9+):** Plan the study and outline the data collection pipeline
- **Week 2 (June 16+):** Set up Originality.ai API for classification, increase SerpAPI query access, improve AI Overview filtering
- **Week 3 (June 23+):** Start scaling up the number of samples and get early results on AI vs human citation ratios
- **Week 4 (June 30+):** Analyze main results and start drafting the paper
- **Weeks 5–7 (July 7+):** Explore secondary questions, refine insights, document insights with supporting graphics and plots
- **Week 8 (July 28+):** Draft the blog post and prepare it for publishing
- **Week 9 (August 4+):** Finalize the paper and prepare for publishing
