# Direct TinyFish API research with a real Kinbor catalog

## Problem and delivered behavior

The previous Phase 2 workflow could fetch pages over public HTTP or replay evidence collected through Work's TinyFish connector. Its Python CLI did not call TinyFish's public API. Those connector executions were real, but importing their captures did not satisfy direct API integration.

The CLI now defaults to `--mode tinyfish`: local Python reads `TINYFISH_API_KEY`, sends authenticated requests to the documented TinyFish Fetch REST endpoint, selects a bounded batch of official links, extracts source-backed observations, scans all 210 actual catalog rows and writes an illustrated Buyer Brief. The client records provider request IDs, HTTP outcomes, timestamps, limits and available usage. There is no manual capture dependency or automatic fallback in this path. Optional Search discovery and Agent lifecycle helpers have separate, explicit boundaries.

## Actual end-to-end execution

On November 9, 2026 in Chicago (November 10 UTC), the local CLI completed authenticated Fetch and usage calls for Atlas Stationers, followed by Shorthand and Wonder Fair migration checks. Each final run received HTTP 200 for two Fetch requests and one usage read. No Search, Agent, connector, profile, vault, outreach or purchase was used in these executions.

| Store | Pages observed | Catalog rows audited | Category-eligible pool | Preview candidates | Final receipt |
|---|---:|---:|---:|---:|---|
| [Atlas Stationers](phase2/live/atlas/buyer_brief.md) | 6 | 210 | 118 | 4 | [api_receipt.json](phase2/live/atlas/api_receipt.json) |
| [Shorthand](phase2/live/shorthand/buyer_brief.md) | 6 | 210 | 126 | 4 | [api_receipt.json](phase2/live/shorthand/api_receipt.json) |
| [Wonder Fair](phase2/live/wonder-fair/buyer_brief.md) | 4 | 210 | 87 | 4 | [api_receipt.json](phase2/live/wonder-fair/api_receipt.json) |

These final outputs contain 16 successful URL observations and usage records matched to all six Fetch provider request IDs. Fetch has no browser run ID; its null `run_id` is expected. A successful transport response supports authentication and acquisition, not exhaustive research or factual independence.

Initial Atlas and Wonder Fair runs were repeated after improving link coverage. The full task therefore made five CLI executions: 10 Fetch requests, five usage reads and 24 successful URL observations, counting repeated retrievals. Initial run audit files remain in ignored local `work/`; the final three-store outputs are committed under `phase2/live/`. This accounting does not claim 24 distinct pages. The API did not return billed cost, so cost remains **Unknown**, not zero.

The committed receipts show `execution: local_python_direct_api`, `transport: official_rest`, authenticated responses and no fallback. Unit-test fixtures and historical connector captures are separate from these real receipts.

## Evidence and candidate selection

Every evidence row retains its source URL, UTC observation time, supporting text, acquisition method and confidence. The new API evidence rows carry `epistemic_status: fact_observation`; matching inferences appear in candidate `match_basis`, while unsupported fields remain Unknown in the summary and brief. Search snippets, when optional Search is enabled, only discover URLs; the fetched page must support a fact. Exact excerpts are observations of what an official site states, not independent proof of stock or buying intentions. Observation timestamps are not site-publication timestamps.

All selected product facts join to unchanged `products.csv`, including source sheet, source row, image path and units per carton. Category matching is an inference from the actual catalog and observed retailer evidence. The current selector considers evidence specificity and literal shared attributes where available, then rotates observed categories and equally supported collections for a small review preview. Alphabetical SKU order breaks display ties only. This removes the former dependence on the first four catalog rows without inventing an aesthetic or buyer-intent score.

The final store previews differ but may share candidates. These are representative hypotheses, not a ranked top four. Broad desk/office evidence is weak support for an individual wrist rest; pen-category overlap does not establish suitability of a specific gel pen at a fountain-pen retailer. Human review must decide whether those hypotheses are useful. The full candidate audit remains available, including tied alternatives and excluded products.

Each SKU requires its own full carton under the project rule. The previews do not assume mixed cartons, split cartons or buyer acceptance. High case packs, including the Atlas pen candidate's 768 units, remain visible. `DTB6611-1` and `DTB6616-1` remain 112 units/carton. A feasible order, margin or low-risk test quantity has not been established.

## Store-specific limits

Atlas exposes a general contact route; incoming vendor acceptance is Unknown. Shorthand publishes product-email guidance but stresses its particular aesthetic and discourages unannounced product visits. Wonder Fair publishes catalog-submission guidance, no-follow-up rules, artwork exclusions and sample-return limits. Read the full [Shorthand FAQ](https://shopshorthand.com/pages/faqs) and [Wonder Fair submission policy](https://www.wonderfair.com/submit) before any future action. Research using AI does not establish whether merchandise artwork meets those rules.

The 20-store dataset remains intact. Only the three current pilots are refreshed; 17 stores stay `legacy_not_revalidated`. Product fit, Evidence strength and Buyer access remain separate review dimensions, with a human-review tie rather than a weighted commercial ranking. Order feasibility is Unknown throughout. The historical `top5_buyers.md` filename is retained for compatibility and does not establish five current winners.

## Engineering and verification

The standard-library client uses fixed official API hosts and environment authentication. It refuses API redirects that could forward the key, bounds response size, retries explicit throttling and appropriate transient failures, records each attempt and retains partial/unknown outcomes. Ambiguous Agent submissions are not blindly repeated. Fetch requests use `ttl: 0`, a 45-second per-URL timeout budget and a bounded page/request/deadline scope. The default CLI budget is six pages, four total API attempts and a 240-second scheduling deadline. DNS and in-flight socket operations can exceed a scheduling deadline; no precise cost or wall-clock guarantee is claimed.

Offline tests cover existing catalog/import integrity plus API authentication boundaries, missing credentials, network failure, HTTP 429/backoff, timeouts, malformed and partial results, Agent asynchronous states/cancellation, evidence validity, all-catalog joins and explicit non-API fallback labeling. Agent helpers and optional Search were mock-tested, not live-tested in this task. The [validation report](phase2/validation_report.json) records 63 passing offline tests and six passing negative controls. Run `python3 -m unittest discover -v` to reproduce the test suite; Pillow is required by the unchanged importer/image tests.

All 214 Phase 1 preservation hashes remain unchanged: 210 product images, catalog, importer, original tests and data dictionary. The existing CSVs and historical snapshots are retained. Integrating `phase2/live/` validates saved outputs, refreshes the three pilot records and review queue, and performs no network calls. Legacy `phase2/pilots/` connector imports, earlier browser run receipts and the Atlas PDF remain historical audit material; they are not the current direct API result.

No retailer email, form submission, purchase, dashboard, CRM, database or OCR was added. Untrusted page text does not become executable instructions, an Agent goal or authorization for an external action. Catalog/image content and private supplier details are not transmitted in these Fetch requests. Credentials, private source workbooks, quotations and inventory do not belong in the public repository.

## Reproduction and remaining work

```bash
# TINYFISH_API_KEY must already be securely configured in the execution environment.
python3 research.py --mode tinyfish --url https://www.atlasstationers.com/ \
  --output-dir work/atlas --collect-usage
python3 -m unittest discover -v
python3 research.py --mode validate --output-dir phase2/live/atlas
python3 phase2.py --integrate-pilots --pilot-root phase2/live
python3 phase2.py
```

The direct Fetch integration has real end-to-end evidence for these three bounded runs. Production reliability, broader retailer coverage and commercial usefulness are still unproven. Revalidate the remaining 17 stores, inspect product images and language/layout, verify supplier and resale terms, and obtain buyer confirmation before proposing an order. Human time saved, adoption, conversion, revenue and billed API cost remain Unknown. Runtime observations are not business-effectiveness measurements.

See [TinyFish API implementation notes](docs/TINYFISH_API.md) for the verified endpoint choices, optional capabilities, authentication and current documentation sources.
