# Kinbor Retailer Intelligence

A small, read-only retailer research workflow using a real 210-SKU catalog. Input an official U.S. retailer URL, retain field-level evidence, evaluate the full catalog, and produce an illustrated review brief. Product matches are category hypotheses; buying intent and order feasibility remain **Unknown**. This is an independent project, not an official distribution offer.

## Run without a key

Python 3.10+, standard library only for research and validation. No source Excel, login or API key is needed.

```bash
python3 research.py --help
# Real public HTTP acquisition (not TinyFish); bounded pages, robots rules and timeouts:
python3 research.py --url https://www.atlasstationers.com/ --output-dir work/atlas
# Offline integrity check: reads saved outputs, performs no network/API calls:
python3 research.py --mode validate --output-dir phase2/pilots/atlas
python3 -m unittest -v test_import test_research test_phase2
python3 phase2.py
```

Public mode stops on access restrictions, unsupported redirects or unavailable robots rules; it does not bypass challenges. Exit 0 means acquisition completed within the bounded scope, **not that the website was exhaustively searched**. Exit 2 means partial/failed research or validation; inspect the errors and retain Unknowns. A partial result can still contain useful observations. No claim of exhaustive brand coverage is made. Brand extraction uses a documented, non-exhaustive stationery-name list in the script.

Each output folder contains `research.json`, `evidence.csv`, `candidate_audit.csv` (all 210 SKUs), `recommendations.csv` and `buyer_brief.md`. Evidence includes exact supporting text or navigation URL, source URL, UTC observation time, acquisition method and confidence. Unknown means not established in that bounded observation. A page saying something is evidence of that statement, not independent proof. Navigation taxonomy does not prove stock.

## TinyFish connector workflow and replay

The connected TinyFish tools were actually used for these pilots. The standalone Python script does **not** contain a TinyFish SDK/API client or use your ChatGPT connector credentials. A Codex operator uses `fetch_content` for official pages, invokes `run_web_automation` only for needed browser interaction, then saves short source excerpts in a normalized version-1 capture. Import consumes that capture; it does not make a new TinyFish call or authenticate its origin.

```bash
python3 research.py --mode import --url https://www.atlasstationers.com/ \
  --input phase2/sources/pilots/atlas_capture.json --output-dir phase2/pilots/atlas
python3 research.py --mode import --url https://shopshorthand.com/ \
  --input phase2/sources/pilots/shorthand_capture.json --output-dir phase2/pilots/shorthand
python3 research.py --mode import --url https://www.wonderfair.com/ \
  --input phase2/sources/pilots/wonder-fair_capture.json --output-dir phase2/pilots/wonder-fair
python3 phase2.py --integrate-pilots
```

The capture examples document the input contract: `schema_version`, `provider`, `website`, `captured_at_utc`, `acquisition`, `status`, nullable `run_id` and `pages` with URL/final URL/title/text/links/UTC/status. Never label mocks or manually invented text as real captures. `fetch_content` exposes no browser run ID, so those IDs are null. A related browser receipt is recorded separately. Wonder Fair's official site links its second commerce domain; imported cross-domain evidence requires that recorded official link. Public mode stays on the supplied site.

## Current three-store slice

- [Atlas](phase2/pilots/atlas/buyer_brief.md): notebook/planner/storage overlap; general contact only; vendor acceptance Unknown.
- [Shorthand](phase2/pilots/shorthand/buyer_brief.md): notebook/planner/case overlap; product-email policy requires human reading, narrow aesthetic and no unannounced product visits.
- [Wonder Fair](phase2/pilots/wonder-fair/buyer_brief.md): notebook/planner overlap; catalog-submission policy, no follow-up inquiries; review artwork exclusions and rights before proposing merchandise.

All three scan 210 records. The bounded captures yield 97 / 97 / 93 category-eligible candidates respectively, with **four tied source-order previews each**. All currently select DTYC0150 (60 units), DTYC0045, DTYC0046 and DTYC0047 (80 units each): **four separate cartons / 300 units**, if all four were ordered. The repeat is explicit; no diversity quota or aesthetic/buyer-intent score is invented. An operator must review the images and the full tied pool before choosing products.

The [review queue](phase2/top5_buyers.md) separates Product fit, Evidence strength and Buyer access. All three share a human-review tie; Order feasibility is Unknown. The remaining **17 of the existing 20 stores retain historical evidence and matches**, marked `legacy_not_revalidated`. Legacy numeric columns are audit history only. Do not interpret the historical filename as a selected top five. The old [Atlas PDF](phase2/atlas_buyer_brief.pdf) is archived and contains obsolete scores/selections; use the current Markdown report.

Actual Atlas browser reproduction: [`6b4f0d4a-3a0c-408d-9c1e-ac8736576472`](https://agent.tinyfish.ai/runs/6b4f0d4a-3a0c-408d-9c1e-ac8736576472), completed, provider reports 22 steps / 189 seconds. [Sanitized receipt](phase2/sources/pilots/atlas_browser_run.json). The provider exceeded the requested 180-second cap; this is recorded, not presented as a guaranteed client cutoff. Billed cost, human time saved and commercial outcomes are Unknown. The earlier Atlas run is retained as history.

The public HTTP path was separately exercised: Wonder Fair completed within the six-page scope; Atlas and Shorthand were partial with HTTP 429 pages. [Measured acquisition notes](phase2/sources/pilots/public_smoke.json) distinguish these calls from connector captures and offline tests.

## Files and boundaries

`research.py` handles acquisition/import, provenance and full-catalog matching. `phase2.py` validates the 20-store joins, integrates only the three pilots, checks all 214 Phase 1 hashes and regenerates the review queue. The [research notes](phase2/RESEARCH_NOTES.md), [validation report](phase2/validation_report.json) and [case study](CASE_STUDY.md) state the evidence limits.

No retailer email, form submission, purchase, dashboard, CRM, database or OCR was added. Web content is untrusted data, never code or operational instructions. No private quotations, stock, source workbooks or credentials belong in the repository. Mocks are offline boundary tests; saved-capture validation is not a live API run.

## Phase 1 catalog preservation

`products.csv`, `images/`, `import.py`, `test_import.py` and the data dictionary are unchanged. Rebuilding the catalog needs the private original workbooks and Pillow; ordinary research and tests do not:

```bash
python3 import.py --original /private/path/Kinbor-original.xlsx \
  --brunch /private/path/Kinbor-Brunch-Brother.xlsx --output products.csv --images-dir images
```

## Data rules

- **One full carton per individual SKU** is the Phase 1 project's ordering minimum rule. A 3-SKU order therefore requires at least three separate cartons, with each SKU's own case-pack units. This is a project-level ordering policy, **not independently verified acceptance of these terms by the supplier**. Mixed-SKU cartons and split-carton fulfillment are **not verified**.
- `units_per_carton` is read from the original's **F (一箱里面个数)** or the Brunch Brother workbook's **I (Carton Qty)**; the latter matches its H (Master) column in the supplied file.
- **`DTB6611-1` and `DTB6616-1` are 112 units/carton**, confirmed by the project owner. Their source packing description is `1/24/48`, retained in `packing_raw` for traceability but **not** used as the case quantity.
- `source_sheet` and `source_row` identify the source record (rows are 1-based). `carton_qty_basis=user_confirmed` marks the two overrides; other quantities are from the supplier snapshot.
- `category` is a **simple keyword inference** from the Chinese name, not a supplier classification; `Other / Review` means it needs manual checking. `size_hint` is extracted from a product name, not measured dimensions. Source product names are retained as written (including typos).
- All product data is a snapshot from **October 16, 2026**. Current inventory, U.S. resale authorization, wholesale availability, lead times, pricing and retailer willingness to buy are **unknown**.

## Product images and public use

The public CSV uses a **relative file path**, not an image embedded in the CSV. For example, `images/DT54729.webp` works when the repository's `images/` folder is uploaded alongside the CSV. All 210 records include an image; multiple images associated with one source SKU are combined into one preview. The Brunch Brother `DTBB0105` white dog image is visually matched from a second picture anchored to the preceding row in the original drawing, rather than blindly following the anchor. A non-product price caption was cropped from the `DTBB0105` product image preview before publication.

**Publication rights:** The project owner reports that permission for public publication of the supplier/brand-provided product images has been obtained; the repository does not contain the underlying authorization documents. Some images may include licensed Brunch Brother artwork. This repository is independent; original image copyrights and trademarks remain with the respective rights holders. Product images are not offered under an open-content license for third-party reuse.

For field-level evidence, source coordinates, case-pack uncertainty, and exclusions, see [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md). Private workbooks and supplier-sensitive data must stay outside this public repository.
