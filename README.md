# Kinbor Retailer Intelligence — Phases 1 and 2

A **small, reproducible product catalog** for an independent U.S. retailer research project. It uses real Kinbor SKU codes and original Chinese product names. This is an independent project, **not an official Kinbor/Guangbo or Brunch Brother distribution offer**.

## Files

| File | Purpose |
| --- | --- |
| `products.csv` | 210 real SKU records, each with a relative `image_path` to its product photo. |
| `import.py` | Rebuilds the CSV and optimized SKU images from the two **private** October 16, 2026 workbooks. |
| `test_import.py` | Checks counts, uniqueness, one-carton MOQ, confirmed carton quantities and safe public fields. |
| `images/` | 210 optimized product images (WebP), one per SKU; multiple source panels combined where appropriate. |
| `docs/DATA_DICTIONARY.md` | English schema, field types, source-cell mapping, carton evidence, Unknown policy and public/private boundaries. |
| `phase2/` | 20 U.S. retailer businesses, 74 actual SKU candidates, 148 claim-level sources, top-five queue and Atlas Buyer Brief. |
| `phase2.py` | Validate research/catalog joins, preserve Phase 1 hashes, regenerate priorities, optionally check links and render the brief. |
| `CASE_STUDY.md` | Field-engineering decisions, real execution evidence, validation and measurement limits. |
| `README.md` | These instructions and data limitations. |

## Run

Requires Python 3.10+ and Pillow to build the product images (`python3 -m pip install Pillow`). Running the committed CSV tests requires only the standard library. Keep the original XLSX files **outside** the public repository.

```bash
python3 import.py \
  --original '/private/path/Kinbor-original.xlsx' \
  --brunch '/private/path/Kinbor-Brunch-Brother.xlsx' \
  --output products.csv \
  --images-dir images

python3 -m unittest -v test_import
```

The source workbooks are required **only to regenerate the CSV**. Reviewing the CSV or running its tests does not require private source files. The exporter reads only product name, SKU, carton/packing information and worksheet coordinates; it does not export quotations, supplier cost, inventory, barcodes, or order amounts. The product images are regenerated as optimized, metadata-stripped WebP files in `images/`; original workbooks are not included.

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

## Phase 2: evidence-led retailer pilot

Start with the illustrated [Atlas one-page Buyer Brief](phase2/atlas_buyer_brief.pdf) ([text and sources](phase2/atlas_buyer_brief.md)), then the [top-five review queue](phase2/top5_buyers.md). Review [retailers.csv](phase2/retailers.csv), [sku_matches.csv](phase2/sku_matches.csv), [evidence.csv](phase2/evidence.csv), and the [method/rubric/limitations](phase2/RESEARCH_NOTES.md).

```bash
python3 -m unittest -v test_import
python3 phase2.py
python3 phase2.py --refresh
# Optional network checks:
python3 phase2.py --check-links
# Optional PDF rebuild (reportlab + Pillow):
python3 phase2.py --brief
```

Atlas has **one completed connected TinyFish live-browser run**, with a [saved receipt](phase2/sources/tinyfish_atlas_run.json) and independent official-page cross-checks. The other 19 businesses use public web research, **not TinyFish live API execution**. Evidence is URL-level with retrieval timestamps (2026-11-10 UTC / 2026-11-09 Chicago); page tools may use caches. Three provider-reported exact Atlas product links returned 429 on independent checks and are not used for matching/ranking.

The score separates category breadth, evidence strength and contact-route clarity. **Order feasibility is Unknown for every store** and excluded from the score. Candidate matches and English descriptions are model judgments; buyers' interest, capacity, supplier terms, pricing and U.S. resale rights are unverified. See the tie-break and source weaknesses before interpreting rank. Existing Phase 1 data/importer/tests/images are preserved.

No dashboard, retailer email, submitted form, customer production deployment or measured time saving is claimed. The next step is a human review of samples, commercial feasibility and permitted contact routes. [CASE_STUDY.md](CASE_STUDY.md) explains the FDE work and future measured comparison.
