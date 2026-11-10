# Kinbor Retailer Intelligence

A read-only retailer research CLI backed by the real 210-SKU Kinbor catalog and approved product previews. The default research mode calls the **official TinyFish REST API directly from local Python**. It fetches an official retailer URL, records source evidence and authenticated request receipts, evaluates every catalog SKU and writes a Buyer Brief. Product fit remains an inference; aesthetic fit, buying intent and order feasibility require human review.

This independent research project is not an official distribution offer or a commercially validated sales system.

## Run the direct API workflow

Python 3.10+, standard library only for research and validation. Configure `TINYFISH_API_KEY` in your secure execution environment or secret manager. For an interactive terminal, enter it without displaying or saving it in shell history:

```bash
read -r -s TINYFISH_API_KEY  # bash or zsh; type the key, then press Enter
export TINYFISH_API_KEY
```

Do not paste the key in chat or commit it, `.env`, private workbooks or supplier-sensitive material. The CLI reads the environment; it does not read connector OAuth tokens or a credential file. See the [API implementation notes](docs/TINYFISH_API.md) for setup and limits.

```bash
python3 research.py --mode tinyfish --url https://www.atlasstationers.com/ \
  --output-dir work/atlas --collect-usage
python3 research.py --mode tinyfish --url https://shopshorthand.com/ \
  --output-dir work/shorthand --collect-usage
python3 research.py --mode tinyfish --url https://www.wonderfair.com/ \
  --output-dir work/wonder-fair --collect-usage
# The default is also --mode tinyfish.
python3 research.py --help
```

The default route makes two Fetch requests: the supplied homepage, then one bounded batch of relevant official links. `--tinyfish-search` adds optional domain-restricted Search discovery; snippets do not become facts. No Agent run is needed or automatically created. There is no automatic HTTP or connector fallback. Missing credentials produce `LIVE API TEST BLOCKED — missing credential` in the receipt and exit 2, never a fabricated successful run.

Each output folder contains:

| File | Review purpose |
|---|---|
| `api_receipt.json` | Direct transport, provider request IDs, HTTP outcomes, timestamps, budgets and available usage; unreported cost is Unknown. |
| `research.json` | Acquisition mode, bounded pages, extracted fields, errors and summary. |
| `evidence.csv` | Source URL, observation time, supporting text, `fact_observation` status and confidence; matching inferences and Unknowns remain explicit in the candidate/summary outputs. |
| `candidate_audit.csv` | All 210 catalog rows, eligibility and matching reasons. |
| `recommendations.csv` | A small representative review preview joined to actual catalog SKU/source/image/carton facts. |
| `buyer_brief.md` | Illustrated candidate brief, source links, policy limits and Unknowns. |

Exit 0 means the bounded acquisition completed, not an exhaustive website search or proof of commercial suitability. Exit 2 means partial, failed or blocked research; inspect the receipt and errors. Passing `validate` reads saved outputs and makes no API calls.

## Verified three-store API slice

On November 9, 2026 in Chicago (November 10 UTC), the Python CLI received authenticated HTTP 200 responses from the official Fetch API and its usage endpoint for all three stores. Each final run made **two Fetch requests and one usage read**, with no fallback, Search or Agent run. Receipts reconcile usage records to the two provider request IDs. Fetch is synchronous, so browser `run_id` is null, not invented.

| Store | Final pages | Catalog scanned | Category-eligible candidates | Review preview | Receipt |
|---|---:|---:|---:|---:|---|
| [Atlas Stationers](phase2/live/atlas/buyer_brief.md) | 6 | 210 | 118 | 4 | [Direct API receipt](phase2/live/atlas/api_receipt.json) |
| [Shorthand](phase2/live/shorthand/buyer_brief.md) | 6 | 210 | 126 | 4 | [Direct API receipt](phase2/live/shorthand/api_receipt.json) |
| [Wonder Fair](phase2/live/wonder-fair/buyer_brief.md) | 4 | 210 | 87 | 4 | [Direct API receipt](phase2/live/wonder-fair/api_receipt.json) |

Initial Atlas and Wonder Fair observations were rerun after improving bounded link coverage. Across all five real CLI runs, this task observed 10 Fetch requests, five usage reads and 24 successfully fetched URL observations; the final committed slice contains 16 of those observations. Initial run audit files remain local in ignored `work/`. These are observations, not 24 distinct URLs or a claim of free execution. Billed cost is **Unknown** because the returned usage data does not provide it.

The current matching strategy uses observed categories, evidence specificity and literal shared attributes when available, then rotates categories and equally supported collections for a manageable preview. SKU alphabetical order breaks display ties only. The three previews differ; repeated SKUs can still be valid tied candidates. They are not a ranked top four, an aesthetic assessment or buyer approval. Broad office-category evidence is especially weak for a particular product and requires manual review. High case packs remain visible rather than being hidden by a low-quantity story.

Atlas establishes a general contact route; incoming vendor acceptance is Unknown. Shorthand's product-email policy requires review of its narrow aesthetic and discourages unannounced product visits. Wonder Fair's submission policy includes no follow-up inquiries, artwork exclusions and sample-return limits. Read the full source policies and inspect the actual product images before selecting merchandise. No outreach occurred.

The [review queue](phase2/top5_buyers.md) separates Product fit, Evidence strength and Buyer access. Order feasibility is Unknown for every store. Three current pilots share a human-review tie; the other 17 stores retain historical evidence and matches marked `legacy_not_revalidated`. The historical filename does not establish a top five. The old Atlas PDF and connector-based `phase2/pilots/` outputs remain archived audit material, not the current API validation.

## Validate and integrate saved outputs

```bash
python3 -m unittest discover -v
python3 research.py --mode validate --output-dir phase2/live/atlas
python3 research.py --mode validate --output-dir phase2/live/shorthand
python3 research.py --mode validate --output-dir phase2/live/wonder-fair
python3 phase2.py --integrate-pilots --pilot-root phase2/live
python3 phase2.py
```

`phase2.py` validates joins, integrates the three selected output folders into the existing CSVs, retains historical snapshots, checks all **214 Phase 1 hashes** and regenerates the review queue. These commands are offline; they do not repeat the real API calls. The [validation report](phase2/validation_report.json) records 63 passing offline tests, six passing negative controls and 214/214 unchanged Phase 1 files. Test mocks cover the network boundary but are never reported as live execution. The [case study](CASE_STUDY.md) distinguishes the current API result from historical connector research and remaining commercial unknowns.

## Explicit alternative modes

```bash
# Public HTTP acquisition, not TinyFish; public is a compatibility alias:
python3 research.py --mode public_http --url https://www.atlasstationers.com/ --output-dir work/http-atlas
# Offline connector-capture import, not an API call:
python3 research.py --mode import --url https://www.atlasstationers.com/ \
  --input phase2/sources/pilots/atlas_capture.json --output-dir work/import-atlas
```

Public HTTP mode respects its robots, redirect and access boundaries and stops on challenges. Import validates a version-1 `tinyfish_connector` capture and does not authenticate its origin or retrieve new pages. Historical connector browser receipts describe actual earlier Work tool runs only; they do not prove that Python called the API. The optional client Agent queue/poll/cancel helpers are mock-tested and were not live-tested in this task.

## Files and boundaries

`tinyfish_client.py` handles fixed official API endpoints, environment authentication, request receipts, bounded retries and optional Agent lifecycle helpers. `research.py` handles acquisition, provenance, full-catalog matching and output validation. Web content is untrusted data and never becomes code, an Agent goal or permission for an external action. Catalog data, images and private supplier details are not sent to TinyFish for these Fetch calls.

No retailer email, form submission, purchase, dashboard, CRM, database or OCR was added. No private quotation, inventory, original source workbook or credential belongs in this public repository. Official-page statements are self-reported evidence, not independent verification; navigation taxonomy does not establish stock. Unknown means not established within the observed scope, not absent from the website.

## Phase 1 catalog preservation

`products.csv`, `images/`, `import.py`, `test_import.py` and the data dictionary are unchanged. Research and saved-output validation use the standard library. The full test suite and image importer require Pillow; rebuilding the catalog also requires the private original workbooks:

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
