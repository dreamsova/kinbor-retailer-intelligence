# Matching review protocol

This is a small decision-usefulness comparison for Atlas Stationers, Shorthand and Wonder Fair. It does not establish accuracy, buyer preference or a commercial outcome. No human gold labels have been supplied.

Run offline after generating each store's `matching.json`:

```bash
python3 eval.py --generate
python3 eval.py --summarize phase2/reviews.csv
```

Generation validates all three saved matching outputs offline before writing anything, then creates 36 blank review rows: 12 unique real catalog SKUs per store. The deterministic sample includes the frozen pre-change category baseline, the new shortlist, evidence-supported alternatives and deliberate design/function challenges. The four probes include a blind-box pen, a storage item, a blank A6 refill and an illustrated A6 journal. These are hypotheses to inspect, never pre-labelled positive or negative examples. The same SKU can be suitable for multiple stores; diversity is not a quality metric.

`phase2/reviews.csv` is the reviewer-facing worksheet. `phase2/reviews.key.csv` contains the hidden A/B system mapping and sampling rationale. Give reviewers only the worksheet, actual catalog images, retailer source pages and the instructions below. Keep the key and implementation/output shortlist files away from them until answers are locked. Side assignments and row order are reproducible from a fixed seed; each row compares two explanations for the same retailer–SKU pair. System names are concealed, but the prose and “not selected” baseline statements may reveal origin. This is partial blinding, not a fully blinded experiment. Do not treat its responses as an independent training or accuracy benchmark.

For each row:

1. Open the real Kinbor image, check the SKU and carton quantity, and inspect the linked retailer product evidence. A page listing is not proof of current stock or authorization.
2. Judge whether explanation A or B helps you make a better selection decision. Enter `A`, `B`, `uncertain` or `tie` in `choice`; uncertainty is a valid answer.
3. Independently enter `yes`, `no` or `uncertain` in `sku_fit`: would you include this SKU for further buyer review given the present evidence? This is reviewer judgement, not buyer acceptance. Explain the main reason or missing fact in `reason`.
4. Record a reviewer identifier and actual elapsed seconds if measured. Leave timing blank when unmeasured. Do not estimate past time.

First review independently, without consulting the mapping key or another reviewer's answers. If two reviewers are available, generate separate worksheet copies and keep both original responses. Discuss disagreements only after locking each copy, recording the unresolved evidence gap; do not silently replace uncertainty with consensus. Use separate filenames for later rounds so labels and explanations remain tied to the evaluated version. The generator refuses to replace either existing worksheet or key unless `--force` is explicitly supplied; keep user responses out of a public Git commit.

Read the evidence in three layers:

| Layer | What can be assessed |
|---|---|
| Confirmed catalog facts | SKU, catalog image path, source coordinates, carton quantity and the one-full-carton-per-individual-SKU project rule. Catalog categories can themselves be inferred. |
| Observations and inference | Official page titles, observed description/price/currency/image URLs and timestamps are source observations. Aesthetic similarity, positioning, compatibility and recommendation reasoning are hypotheses; a URL alone is not an image assessment. |
| Commercial unknown | Buyer interest, current inventory, brand/resale authorization, supplier availability, wholesale price, margin, material/performance equivalence and willingness to purchase one carton. |

The summarizer reports actual A/B preferences decoded as new/old, uncertain/tie/pending counts, definite `yes`/`no` fit labels, separately counted uncertain fit responses, and timing only where supplied. It does not compute accuracy or an improvement percentage. Compare disagreement reasons and time required to reach a useful decision before deciding whether the new matching is useful. A later independent expert-labelled set can support an accuracy study; these comparison responses must not be reused as gold without a separately designed, independent assessment.

The frozen baseline has different discovery evidence from the enriched product-evidence run. This comparison evaluates the combined acquisition-and-matching change, not an isolated algorithm effect. Rules-only output must retain `MULTIMODAL LIVE NOT VALIDATED` when no live vision assessment occurred. Fewer recommendations or abstention can be the correct response to insufficient evidence; a complete shortlist is not a success criterion.
