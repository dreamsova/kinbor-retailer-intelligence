# From a static retailer MVP to a reusable research workflow

## Problem and delivered behavior

The owner has 210 real Kinbor SKUs and product images. The previous Phase 2 snapshot listed 20 U.S. stores and 74 proposed matches, but only used 14 distinct SKUs and could not research a new URL. Its weighted ranking also hid unresolved ties.

`research.py` now accepts an official retailer URL, acquires bounded public evidence or imports an actual TinyFish connector capture, scans all 210 catalog records and produces source-linked candidate audits, four review candidates and illustrated Markdown briefs. Separate Product fit, Evidence strength and Buyer access replace the active numerical total. Order feasibility is always Unknown without real buyer confirmation. The three tested stores share a review tie; the filename `top5_buyers.md` is retained without inventing two additional current selections.

## Actual execution

On November 9, 2026 in Chicago (November 10 UTC), connected TinyFish `fetch_content` read official Atlas Stationers, Shorthand and Wonder Fair pages. Short exact excerpts and source URLs are saved in `phase2/sources/pilots/`. Their capture timestamps record operator observation of the returned content; they do not claim site publication time or cache-free origin retrieval.

Atlas required interactive navigation/filter inspection. A real `run_web_automation` completed: [6b4f0d4a-3a0c-408d-9c1e-ac8736576472](https://agent.tinyfish.ai/runs/6b4f0d4a-3a0c-408d-9c1e-ac8736576472), provider-reported 22 steps and 189 seconds. An unsupported optional step cap was rejected before starting; only that argument was removed. The successful run exceeded the requested 180-second cap, so the receipt records the discrepancy. No profile, vault, login or outreach was used. Narrative browser output was treated as paraphrase, not a verbatim source; exact field evidence comes from separately fetched official text. A provider observation of not finding Kinbor was not accepted as proof of its absence.

The standalone script has no TinyFish API client or connector-token access. Codex uses the connected tools and hands their normalized capture to the CLI. Import/validate are honest offline replay, not new API executions; `fetch_content` exposes no browser run ID. Atlas's separate browser receipt is linked without assigning its ID to those page fetches. This operator bridge remains a limitation compared with a fully unattended TinyFish API deployment.

The public HTTP path was also exercised independently: Wonder Fair completed within its three fetched pages; Atlas and Shorthand returned partial results due to HTTP 429. No bypass or repeated retry occurred. The saved acquisition receipt reports elapsed times for those calls, not human labor or time saved. Initial restricted-environment DNS failures were recorded separately from network-enabled acquisitions.

## Three-store results

| Store | Category-eligible pool / all 210 scanned | Verified review finding |
|---|---|---|
| Atlas Stationers | 97 | Notebook/planner/storage overlap; general contact; incoming vendor acceptance Unknown. |
| Shorthand | 97 | Notebook/planner/case overlap; product-email policy, narrow aesthetic and discouraged unannounced product visits. |
| Wonder Fair | 93 | Notebook/planner overlap on the officially linked commerce site; catalog submission and no follow-up inquiries. |

Read the full [Shorthand FAQ](https://shopshorthand.com/pages/faqs) and [Wonder Fair submission rules](https://www.wonderfair.com/submit) before any use. Wonder Fair excludes fan art and AI-assisted artwork; merchandise artwork provenance and resale rights require human confirmation. The research process does not determine whether a SKU satisfies that policy.

Every store currently previews the same tied source-order candidates: DTYC0150, DTYC0045, DTYC0046 and DTYC0047. These total four separate cartons / 300 units under the project rule. Repetition is disclosed rather than obscured by a diversity quota. A person must choose from the full eligible pool after viewing actual images and samples; category overlap does not establish aesthetic fit, paper quality, price suitability, purchase intent or carton acceptance.

## Verification and engineering decisions

All 214 Phase 1 preservation hashes remain unchanged: the 210 images, catalog, importer, original tests and data dictionary. SKU, image path, source-sheet/row and carton fields join to the real catalog; DTB6611-1 and DTB6616-1 remain 112 units/carton. The existing 20 stores and 148 historical evidence records are preserved. Only the three current pilots are refreshed; 17 stores are explicitly held as `legacy_not_revalidated`. The old Atlas PDF is archived because it contains obsolete scores and selections.

Offline tests cover URL/credential boundaries, denied and timeout acquisition, failure without fabricated run IDs, deduplication, exact supporting quotes, negation/injected instructions, secret removal, all-210 joins, policy restrictions and tied review behavior. Review found and corrected a false pen-category inference from pen-pouch names and missing policy constraints. The final validation report records actual test counts and dataset checks. Mocks and replay validation are separate from real network calls; passing them does not authenticate provider origin or guarantee current website truth.

HTTPS/public-host validation, same-site redirects, robots rules, request/page limits, explicit partial/failed states and per-request inactivity timeouts keep public research bounded. The crawl deadline is a scheduling budget; system DNS and an in-flight HTTP operation can overrun it. Untrusted web text never becomes code, a tool instruction or permission for external action. No dashboard, database, CRM, OCR, retailer email, form submission, purchase, private quotation, inventory, key or source workbook was added.

## Remaining work and measurement limits

Revalidate the remaining 17 stores using the same workflow before promoting them. Complete human image/layout and policy review for the three pilots, then obtain real supplier and buyer confirmations before any outreach or order. A future unattended TinyFish API integration needs an officially configured credential and separately tested client, rather than pretending that saved-capture import makes API calls.

TinyFish billed cost, human time saved, production adoption, conversion and revenue are Unknown. Provider runtime and HTTP acquisition latency are not business effectiveness metrics. A future frozen-task manual/assisted comparison should measure human minutes, factual errors, rework, permitted-route completeness, billed cost and independently reviewed usefulness. No such result is claimed here.
