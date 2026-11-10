# Kinbor Retailer Intelligence — Phase 1

A **small, reproducible product catalog** for an independent U.S. retailer research project. It uses real Kinbor SKU codes and original Chinese product names. This is an independent project, **not an official Kinbor/Guangbo or Brunch Brother distribution offer**.

## Files

| File | Purpose |
| --- | --- |
| `products.csv` | 210 real, safe-to-share SKU records (120 Original Design + 90 Brunch Brother). |
| `import.py` | Rebuilds the CSV from the two **private** October 16, 2026 quotation workbooks. Standard Python only. |
| `test_import.py` | Checks counts, uniqueness, one-carton MOQ, confirmed carton quantities and safe public fields. |
| `README.md` | These instructions and data limitations. |

## Run

Requires Python 3.10+; no pip install needed. Keep the original XLSX files **outside** the public repository.

```bash
python3 import.py \
  --original '/private/path/Kinbor-original.xlsx' \
  --brunch '/private/path/Kinbor-Brunch-Brother.xlsx' \
  --output products.csv

python3 -m unittest -v test_import
```

The source workbooks are required **only to regenerate the CSV**. Reviewing the CSV or running its tests does not require private source files. The exporter reads only product name, SKU, carton/packing information and worksheet coordinates; it does not export quotations, supplier cost, inventory, barcodes, order amounts, or images. Do **not** commit the original workbooks or their extracted images to a public repository.

## Data rules

- **One carton per SKU** is the minimum order quantity. A 3-SKU order therefore requires at least three separate cartons. Mixed-SKU cartons and split-carton fulfillment are **not verified**.
- `units_per_carton` is read from the original's **F (一箱里面个数)** or the Brunch Brother workbook's **I (Carton Qty)**; the latter matches its H (Master) column in the supplied file.
- **`DTB6611-1` and `DTB6616-1` are 112 units/carton**, confirmed by the project owner. Their source packing description is `1/24/48`, retained in `packing_raw` for traceability but **not** used as the case quantity.
- `source_sheet` and `source_row` identify the source record (rows are 1-based). `carton_qty_basis=user_confirmed` marks the two overrides; other quantities are from the supplier snapshot.
- `category` is a **simple keyword inference** from the Chinese name, not a supplier classification; `Other / Review` means it needs manual checking. `size_hint` is extracted from a product name, not measured dimensions. Source product names are retained as written (including typos).
- All product data is a snapshot from **October 16, 2026**. Current inventory, U.S. resale authorization, wholesale availability, lead times, pricing and retailer willingness to buy are **unknown**.

## Next

**Phase 2:** use TinyFish to research real U.S. retailers, cite evidence from retailer websites, and connect those facts to candidate SKUs. Phase 1 does **not** include TinyFish API calls, retailer matching, buyer outreach, or a web dashboard.
