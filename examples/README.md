# Saved retailer research

**Open a current style brief:** [Atlas](retailers/atlas/style_brief.md) · [Shorthand](retailers/shorthand/style_brief.md) · [Wonder Fair](retailers/wonder-fair/style_brief.md)

These examples use real public website observations. They do not represent retailer partnerships, live inventory or commercial deployments.

```text
retailers/              Three complete store bundles
  atlas/
  shorthand/
  wonder-fair/
baselines/             Frozen combined retailer, match and evidence tables
evaluation/            36 pending comparison rows and separate A/B key
history/               Original validation reports and timestamps
sku_visual_notes.json  45 analyst catalog-image notes
review_queue.md        Current links followed by the historical queue
```

Each retailer directory contains both generations:

| Current style review | Frozen category comparator |
|---|---|
| `style_brief.md` — human-readable hypotheses | `buyer_brief.md` — original category preview |
| `matching.json` — all 210 candidate records | `candidate_audit.csv`, `recommendations.csv` — old selection |
| `product_evidence.json` — product observations and connector receipts | `research.json`, `api_receipt.json`, `evidence.csv` — older direct REST execution |

Keep complete bundles together: validators recompute catalog joins, source support and matching decisions. The newer product capture and older REST receipts have different acquisition provenance. [Full baseline guide](../docs/BASELINES.md).

The [combined retailer table](baselines/retailers.csv) retains its historical `current_pilot` labels for three stores and `legacy_not_revalidated` for 17 others. Those labels do not make the old [category matches](baselines/sku_matches.csv) current style recommendations. [Historical combined evidence](baselines/evidence.csv).

[Evaluation protocol](../docs/MATCHING_EVALUATION.md) · [36 blank review rows](evaluation/reviews.csv) · [Demo walkthrough](../docs/DEMO.md)

**MULTIMODAL LIVE NOT VALIDATED.** All product-quality and commercial judgements remain pending. Retailer image URLs were recorded; their pixels were not assessed.
