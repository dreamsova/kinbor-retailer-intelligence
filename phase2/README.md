# Evidence and output map

**Current review entry points:** [Atlas](live/atlas/style_brief.md) · [Shorthand](live/shorthand/style_brief.md) · [Wonder Fair](live/wonder-fair/style_brief.md)

The three directories under `live/` each contain two stages. Keep complete bundles together; validators recompute catalog joins, receipts, evidence and decisions.

```text
live/<store>/
  style_brief.md           CURRENT: source-linked style hypotheses
  matching.json            CURRENT: all 210 candidate records
  product_evidence.json    CURRENT: official product observations + connector receipts
  research.json            FROZEN: older direct REST/category research
  api_receipt.json          FROZEN: receipt for that older research only
  evidence.csv             FROZEN: extracted page evidence
  candidate_audit.csv      FROZEN: full category-baseline audit
  recommendations.csv      FROZEN: old category preview
  buyer_brief.md            FROZEN: old illustrated category brief
```

Shared current input: [45 analyst image notes](sku_visual_notes.json). Evaluation: [36 blank comparison rows](reviews.csv) and a separate reviewer-withheld mapping key. [Protocol](../docs/MATCHING_EVALUATION.md).

The combined [retailers](retailers.csv), [matches](sku_matches.csv) and [evidence](evidence.csv) tables are frozen comparators. Their `current_pilot` labels refer to the previous category schema; 17 other stores remain `legacy_not_revalidated`. The [review queue](review_queue.md) contains current style links followed by that historical queue. Reports here retain their original timestamps and scope.

`live/` means previously captured website evidence, not live stock, buyer engagement or a deployed service. **MULTIMODAL LIVE NOT VALIDATED**; all quality and commercial judgements remain pending. See [baseline guide](../docs/BASELINES.md), [architecture](../docs/ARCHITECTURE.md), and [demo](../docs/DEMO.md).
