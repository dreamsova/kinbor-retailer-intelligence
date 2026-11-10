# Direct API retailer research: saved evidence and repository cleanup

> **Historical record — frozen category baseline.** The narrative and four-pick previews below describe the earlier direct REST cleanup, before the current style matcher. References to “current” and “this cleanup” belong to that earlier run; its deletion and test statements do not describe the current project layout. Start with the [current project README](../README.md), [style output map](../examples/README.md) and [baseline guide](BASELINES.md). The historical narrative is retained below; file links and runnable command examples follow the current layout. Historical directory names in the narrative describe that earlier tree.

## Workflow

The CLI combines a real 210-SKU Kinbor catalog with observations from official retailer websites. `python3 -m kinbor.research --mode tinyfish` reads `TINYFISH_API_KEY`, uses the direct TinyFish Fetch REST API, follows a bounded set of official links, records evidence and request receipts, and produces a full-catalog candidate audit and illustrated buyer brief. Optional Search discovery and Agent client helpers remain separate capabilities.

Each saved bundle contains six files: `research.json`, `api_receipt.json`, `evidence.csv`, `candidate_audit.csv`, `recommendations.csv`, and `buyer_brief.md`. The files are retained together because the validator checks receipt hashes, source evidence, catalog joins, and reproducible candidate selection across them.

## Previously captured API evidence

The committed bundles record direct Python API executions from November 9, 2026 in Chicago (November 10 UTC). Each final run records HTTP 200 responses for two authenticated Fetch requests and one usage read, with no fallback, Search, or Agent execution. This repository cleanup made **no new paid API calls**; its checks only read these saved results and use offline test mocks.

| Retailer | Observed pages | Catalog audited | Category-eligible pool | Preview | Receipt |
|---|---:|---:|---:|---:|---|
| [Atlas Stationers](../examples/retailers/atlas/buyer_brief.md) | 6 | 210 | 118 | 4 | [API receipt](../examples/retailers/atlas/api_receipt.json) |
| [Shorthand](../examples/retailers/shorthand/buyer_brief.md) | 6 | 210 | 126 | 4 | [API receipt](../examples/retailers/shorthand/api_receipt.json) |
| [Wonder Fair](../examples/retailers/wonder-fair/buyer_brief.md) | 4 | 210 | 87 | 4 | [API receipt](../examples/retailers/wonder-fair/api_receipt.json) |

These bundles contain 16 successful URL observations. Fetch is synchronous and does not supply a browser run ID; a null `run_id` is expected. Authentication and transport success do not establish exhaustive coverage, independent verification of site claims, buying interest, or commercial suitability. Returned usage records do not include a billed monetary amount, so cost remains Unknown.

Earlier acquisition attempts and connector-based versions are historical records in Git history. They are not required to validate the retained direct API bundles and are not presented as new execution evidence.

## Evidence and selection boundaries

Evidence rows retain source URLs, observation times, supporting text, acquisition method, and confidence. `fact_observation` means the official site made the observed statement. Navigation categories do not prove inventory. Optional Search snippets discover URLs; fetched page content must support a fact.

Selected products join to the unchanged catalog's SKU, image path, source sheet/row, and carton quantities. Matching uses category evidence, evidence specificity, literal shared attributes where available, and rotation across supported categories and collections for a manageable preview. Alphabetical SKU order breaks display ties. The preview is not an aesthetic ranking or buyer approval; the complete 210-row audit exposes alternatives and exclusions.

Each SKU needs its own full carton under the project rule. High case packs remain visible, including the Atlas pen candidate's 768 units. `DTB6611-1` and `DTB6616-1` remain 112 units/carton. Neither supplier acceptance of this ordering rule nor buyer acceptance of carton quantities has been established.

Atlas provides a general contact route; incoming vendor acceptance is Unknown. Shorthand and Wonder Fair publish submission guidance with restrictions. Review the complete source policy linked from each brief before any future action. No outreach is part of this workflow.

## This cleanup

The current tree keeps one complete saved result per store and removes obsolete connector captures, duplicate pilot bundles, old Atlas briefs/PDF, and debug/link logs. Git history preserves the removed versions. The combined CSV data remains available; the queue is now named [`review_queue.md`](../examples/review_queue.md). The retained Atlas bundle is now at `examples/retailers/atlas/`; the application resolves the original serialized paths without rewriting the raw evidence.

Only three stores have the retained current-pilot evidence. All three share priority 1 for human review; 17 other stores remain `legacy_not_revalidated`. Product fit, evidence strength, and buyer access remain separate dimensions. No confirmed buyer list, purchasing probability, or order feasibility is claimed.

The 214 Phase 1 files are protected by the [SHA-256 manifest](phase1_manifest.json): 210 images, `products.csv`, `import.py`, `test_import.py`, and `docs/DATA_DICTIONARY.md`. The [validation report](../examples/history/validation_report.json) records the actual offline checks for this cleanup, rather than treating an old test report as a new run.

## Reproduce the offline checks

Use Python 3.10+ for the current read-only equivalents of the saved-data checks. Public tests use the standard library; Pillow is only needed to rebuild images from private workbooks:

```bash
python3 scripts/verify_repository.py
python3 -m unittest discover -v
python3 -m kinbor.research --mode validate --output-dir examples/retailers/atlas
python3 -m kinbor.research --mode validate --output-dir examples/retailers/shorthand
python3 -m kinbor.research --mode validate --output-dir examples/retailers/wonder-fair
python3 -m kinbor.pipeline
```

The suite covers catalog integrity, request authentication boundaries, missing credentials, network failures, throttling, timeouts, malformed/partial responses, Agent lifecycle states, evidence validity, matching, and explicit non-API mode labels. Optional Search and Agent behavior is mock-tested; these checks do not establish live provider behavior or fresh site truth.

The cleanup does not change API calls, product matching, or commercial rules. Credentials, private supplier workbooks, quotations, and inventory stay outside the public repository. See [API implementation notes](TINYFISH_API.md) for new live research setup and execution limits.
