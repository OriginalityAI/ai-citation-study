# OUROBOROS

This study aims to answer these questions:

- Are AI overviews citing AI generated content? If so, how much?

## Setup

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
