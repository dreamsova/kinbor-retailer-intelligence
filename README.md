# Kinbor Retailer Intelligence — Phase 1

A **small, reproducible product catalog** for an independent U.S. retailer research project. It uses real Kinbor SKU codes and original Chinese product names. This is an independent project, **not an official Kinbor/Guangbo or Brunch Brother distribution offer**.

## Files

| File | Purpose |
| --- | --- |
| `products.csv` | 210 real SKU records, each with a relative `image_path` to its product photo. |
| `import.py` | Rebuilds the CSV and optimized SKU images from the two **private** October 16, 2026 workbooks. |
| `test_import.py` | Checks counts, uniqueness, one-carton MOQ, confirmed carton quantities and safe public fields. |
| `images/` | 210 optimized product images (WebP), one per SKU; multiple source panels combined where appropriate. |
| `docs/DATA_DICTIONARY.md` | English schema, field types, source-cell mapping, carton evidence, Unknown policy and public/private boundaries. |
| `docs/COMMIT_PRIVACY.md` | Git author/committer privacy guidance and pre-existing history remediation. |
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

For field-level evidence, source coordinates, case-pack uncertainty, and exclusions, see [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md). For privacy controls and the remaining historical Git author-email issue, see [`docs/COMMIT_PRIVACY.md`](docs/COMMIT_PRIVACY.md).

## Next

**Phase 2:** use TinyFish to research real U.S. retailers, cite evidence from retailer websites, and connect those facts to candidate SKUs. Phase 1 does **not** include TinyFish API calls, retailer matching, buyer outreach, or a web dashboard.
