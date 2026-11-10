# Kinbor retailer intelligence: a bounded field-engineering pilot

## Customer problem and discovery boundary

The project owner has 210 real Kinbor catalog SKUs and images, but needs a defensible way to decide which U.S. independent retailers merit a conversation and which products to show. A scraped list alone does not answer why a shop fits, whether a buying route exists, or what a full-carton order entails. This problem comes from the owner's supplied brief; no retailer interview or confirmed buyer demand is claimed.

Success was scoped to a reviewable decision package: first an Atlas Stationers brief, then 20 real businesses, 3–5 actual SKU candidates each, explicit facts versus inference, a transparent contact queue and validation. A dashboard, CRM, OCR framework, bulk autonomous outreach and production supplier integrations were excluded.

## Integration and decisions

Preserved the existing catalog/importer/tests and all 210 image files. Phase 2 joins on real `sku`, carries source-sheet/row provenance, and keeps one carton per SKU, including the two 112-unit overrides. Private supplier workbooks, costs, inventory and credentials remain outside the public artifacts. Public images are reused subject to the owner's reported permission; underlying authorization documents are not in the repository and third-party reuse is not licensed by this pilot.

Integrated the user's connected TinyFish browser tool for Atlas. One completed run has a persisted receipt (17 steps, provider-reported 231 seconds). An unsupported optional step cap was rejected before execution, then removed. The result was treated as an extraction candidate, not ground truth: independent official-page checks support address, family operation and notebook/planner/storage categories; unconfirmed exact product links and broad negative/superlative claims were not used in matches or ranking. Three product-link GETs returned 429, explicitly retained as limitations. The remaining 19 stores use verifiable public web research and are clearly labeled **not TinyFish live executions**.

Field findings changed the implementation: replaced closed physical shops, corrected moved addresses, counted multi-location businesses once, replaced inferred group independence with Wet Paint's explicit independent status, and distinguished outward wholesale sales from incoming product submissions. The useful integration is the evidence-to-decision join, with a person deciding whether the merchandise, terms and channel are suitable.

## Delivered behavior and verification

Delivered 20 businesses, 74 SKU candidates and 148 URL-level evidence records, with UTC observations, source methods and verification limits. Atlas has a one-page illustrated Buyer Brief. A small standard-library script checks dataset integrity and regenerates ranking; optional HTTP checks/PDF generation are explicit actions. No credentials or private spreadsheets are required to inspect or validate the committed snapshot.

The ranking separates category breadth (50 points), evidence quality (30) and public contact route (20). Commercial order feasibility stays Unknown for all stores. Paper Plant, Shorthand and Wonder Fair have explicit inbound routes and tie at 100; Penny Post's named buyer yields 93.33; Atlas at 86.67 is tied with four others and reaches fifth by a published administrative tie-break. These are contact-research priorities, not probabilities of purchase.

Actual checks: 12 existing Phase 1 tests passed; Phase 2 validates the 20-store/3–5-SKU contract, foreign keys, source names, image paths, per-SKU/carton arithmetic, ranking, source limits and preservation hashes for 214 Phase 1 files. Six deliberately corrupted inputs are rejected. HTTP/title checks reached 35 of 38 selected URLs; three Atlas product URLs were rate-limited and remain provider-only. Agent source-page reviews checked the top policies, precise addresses and match rationale; user review is still pending. The PDF is rendered and visually checked as a single page. Final delivery/commit status is recorded in the delivery verification file and must be read separately from these local results; no GitHub CI run is implied.

## Human operating workflow

1. Review cited store evidence and images; reconfirm pages before using them externally.
2. Ask the supplier for actual paper/layout samples, current supply, resale/licensing authority and commercial terms without publishing sensitive details.
3. Calculate a feasible order with a full carton of each selected SKU; Atlas's four-candidate bundle is four cartons/124 units, not four samples.
4. Have a person approve retailer fit, permitted contact route and any message. Observe Wonder Fair's no-follow-up/sample constraints, Shorthand's aesthetic/no-walk-in guidance and Two Hands' email restriction.
5. Record any real retailer response and revise assumptions. No retailer was contacted in this pilot.

## Costs, limits and next measured experiment

TinyFish billed cost is Unknown because the connector did not expose it. Its reported run duration is not human research time. No production customer deployment, buyer acceptance, measured time savings, sales conversion or revenue is claimed. Ownership evidence for Bob Slate is historical; Goods for the Study uses a secondary official biography. Some categories are navigation/filter evidence, stock is not confirmed, and the sample favors discoverable stationery specialists. Nominal size does not establish refill fit, paper quality or English usability. Full-carton economics and U.S. resale rights may make every candidate unsuitable until resolved.

The next experiment is a frozen five-store comparison with the same deliverable and a blinded reviewer: manual versus assisted active minutes and elapsed time, critical claim errors, provenance completeness, policy compliance, corrections, API invoice cost and usefulness of the brief. A separately authorized outreach experiment can later measure response/qualified-interest rates. Do not convert those future metrics into present-tense claims.

This demonstrates discovery from the owner's real constraint, bounded scoping, live tool integration, a minimal data contract, traceable joins, failure handling, human review and reproducible validation. External customer adoption and commercial effectiveness remain untested.
