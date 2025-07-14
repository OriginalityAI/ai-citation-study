# When AI Cites AI: A Look Into Citation Bias in Google AI Overviews

Before we dive into citation patterns, let’s first explain how we collected the data.

---

## Data Collection Pipeline

We started with the **MS MARCO Web Search** dataset — a collection of ~10 million real-world Bing queries. Using a filter we called **WTAO**, we sampled 1000 queries predicted to trigger Google’s AI Overviews.

For each query, we collected:

- The **AI Overview** response (including all cited URLs)
- The **Top 100 organic search results** returned by Google

This gave us two sets of URLs per query:

- Citations from the AI Overview
- Organic search results

We merged and deduplicated the URLs, and classified them as **AI-generated** or **Human-written** using Originality.ai’s Batch API.

---

## Citation Events: Where Did Citations Actually Come From?

The first thing we realized is: citations don’t always come from the organic results.

So we split cited URLs into two categories:

- **Cited-from-organic**: URLs that overlapped with the top-100 organic results
- **Cited-out-of-organic**: URLs cited by AI Overviews that weren’t in the top-100

![Cited URLs: In vs Out of Organic Results](path/to/pie_chart.png)

---

## First Discovery: Overall Probabilities

Then we broke it down by AI vs Human origin.

AI

- P(cited | AI): 27.53%
- P(cited-from-organic | AI): 7.93%
- P(cited-out-of-organic | AI): 19.60%

Human

- P(cited | Human): 14.95%
- P(cited-from-organic | Human): 8.34%
- P(cited-out-of-organic | Human): 6.61%

![Citation Source Breakdown](path/to/breakdown_graphic.png)

`cited-from-organic` are on par between AI and Human

but `cited-out-of-organic` is 3 times higher for AI content!!!

and as a result overall `cited` probability is almost double for AI

AI Overviews are **pulling in AI content from outside** the organic results

---

## What About Ranking Position?

We wanted to see: among the top-k ranked organic results, how does citation likelihood change?

So we computed:

- P(cited-from-organic | AI & top-k)
- P(cited-from-organic | Human & top-k)

for k = 100 down to 1.

![Citation Probability vs Top-k](path/to/top_k_plot.png)

What we found:

- AI documents had a consistently **higher** chance of being cited than human docs at every rank
- The gap widened the closer you get to rank #1

- P(cited-from-organic | AI & top-1): 70.00%
- P(cited-from-organic | Human & top-1): 60.08%

---

## So What’s Going On?

It looks like there’s a two-part trend here:

1. **Within the organic list**, AI content is _slightly favored_ for citation, especially at the top.
2. **Outside the list**, AI content is _massively favored_. The model seems to “know” where to find other AI-written documents, even if Google search doesn’t.

That’s weird. It hints at a possible semantic or stylistic bias. Maybe the AI is drawn to other AI content. Maybe it’s an emergent feedback loop. Maybe something deeper.

We don’t know yet.

But we’ve got:

- A replicable setup
- A growing dataset
- And a curious little finding that might matter

![Summary Graphic](path/to/summary_slide.png)
