# Phase 2 evidence and operating notes

This upgrade promotes only Atlas Stationers, Shorthand and Wonder Fair after their reusable research outputs validate. The other 17 retailer records remain historical research, explicitly marked `legacy_not_revalidated`. No new source retrieval or TinyFish browser run is claimed for those stores.

## Current evidence and previous work

- `pilots/atlas/`, `pilots/shorthand/` and `pilots/wonder-fair/` contain the current field-level evidence, source observations, full 210-row SKU audits, candidates and Markdown briefs. Their `research.json` records acquisition mode, real run IDs when supplied by the provider, failures and Unknown fields. A connector capture imported for offline verification is not a new live API request.
- `retailers.csv` retains the original 20 real businesses. Current pilot fields cover category, brand, public contact and supplier-submission information only. Location and ownership evidence are explicitly historical and require revalidation before use.
- `evidence.csv` preserves every historical row and adds the three pilots' accepted evidence under IDs such as `R01-P-E001`. Current rows contain an exact supporting quotation, field-level confidence, retrieval timestamp and source-capture path. Historical rows are labeled separately; old retrieval timestamps are never relabeled as fresh.
- `sku_matches.csv` replaces only the three pilot selections using their full-catalog audit. The remaining 17 selections are historical candidate hypotheses. Every candidate still joins to the unchanged `products.csv`, source sheet/row and exact image path.
- `top5_buyers.md` is now a tied human-review queue. Its filename remains for compatibility; no arbitrary top-five cutoff is produced while 17 stores await revalidation.

The original Atlas TinyFish browser receipt remains at `sources/tinyfish_atlas_run.json`: completed run `98bb203b-8683-4485-8f7b-fc157e5c2a3b`. That previous receipt is not evidence that this upgrade ran TinyFish. Current acquisition receipts and IDs appear in the new pilot outputs. A run link may require the account owner's login. The historical run's three provider-only exact product URLs remain unconfirmed and are excluded from matches.

The original `atlas_buyer_brief.pdf` and `link_checks.csv` are historical artifacts. Their earlier 124-unit Atlas selection, numerical score, cutoff position and HTTP counts do not describe the current pilot. Read the current Atlas Markdown brief instead. `phase2.py --brief` reports its path and does not regenerate obsolete PDF content.

## Separate review dimensions

There is no weighted score, estimated buying probability, automatic best buyer or commercial readiness claim. Old numeric inputs and totals are retained only in `legacy_*` columns for historical audit; the program never ranks by them.

| Dimension | Meaning and limit |
|---|---|
| Product fit | Category-level inference for actual candidate SKUs after scanning all 210 products. Category overlap does not establish visual taste, paper performance, English usability, product demand or brand equivalence. |
| Evidence strength | Direct official text and navigation can support observable site claims; navigation is weaker than a specific product listing. Exact source URLs, observation times, confidence and Unknown fields remain visible. Official information is self-reported and may be stale. |
| Buyer access | A published incoming vendor process is a route signal. General contact, a named buyer or an outbound wholesale page does not establish incoming submission permission. Restrictions remain binding. |
| Order feasibility | **Unknown for every retailer.** No buyer confirmed buying interest, carton acceptance, purchasing capacity or terms. Supplier availability, landed price, margin, lead time and U.S. resale/licensing authority also remain unverified. |

All three promoted pilots share **review priority 1 (tie; human review)**. Alphabetical display order has no commercial meaning. A human must compare fit, evidence and access, inspect images and choose whether any store merits further work. The 17 historical records stay on hold; they are not silently compared against refreshed evidence.

## Contact and product rules

No email, form submission, buyer conversation or purchase was performed. This is an internal research workflow, not a send-ready offer. Any future outreach needs separate authorization and must follow the current official policy.

The previous research identified restrictions worth preserving as review leads: Shorthand discourages unannounced sample visits; Wonder Fair discourages follow-up inquiries and has artwork exclusions; Two Hands bars vendor submissions to its web-order email. Recheck the exact current source before acting. A retailer's outward wholesale program does not prove it buys outside brands. Research assisted by AI does not establish the provenance or eligibility of merchandise artwork.

Every individual SKU requires **one separate full carton** under the Phase 1 project rule. No mixed or split carton is assumed. The MOQ is not independently verified supplier acceptance. `DTB6611-1` and `DTB6616-1` remain **112 units/carton**. Aesthetic judgments are not automated: the original photo is linked and the brief explicitly requires human image review. Nominal A6 dimensions do not establish refill compatibility.

No private supplier spreadsheet, quotation, stock, credential, correspondence or order detail belongs in the public outputs. SKU names, source coordinates and approved catalog images remain the only product source data used.

## Reproduce

```bash
python3 -m unittest -v test_import test_research
python3 research.py --help
# See the root README for each pilot's real acquisition and replay commands.
python3 phase2.py --integrate-pilots
python3 phase2.py
python3 phase2.py --refresh
python3 phase2.py --brief
```

`--integrate-pilots` validates all three output directories before replacing their match rows. `--refresh` regenerates the separate-dimension review queue from reviewed CSVs without accessing the network. Validation checks 20 distinct businesses, 3–5 catalog candidates per business, same-retailer evidence foreign keys, claim/URL consistency, exact product source/image/carton joins, explicit scopes, tied review priority, the two 112-unit overrides and SHA-256 preservation of 214 Phase 1 files. Six negative controls corrupt SKU, MOQ, evidence, feasibility, weighted ranking and manual-review priority. A passing validator is not independent verification of every source claim.

## Measurement limits and remaining work

Only durations and provider costs returned by actual execution may be reported. Unknown API cost is not zero. No measured conversion, revenue, user adoption or human time savings exists. Next work is source revalidation for the remaining 17 stores, independent review of the three briefs and buyer confirmation of a permitted route and carton feasibility. A controlled manual-versus-assisted comparison is still required before claiming efficiency gains.
