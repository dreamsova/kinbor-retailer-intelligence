# Phase 1 public data dictionary

## Scope and provenance

This public dataset is a **2026-10-16 snapshot**, not live supplier inventory or a binding wholesale quotation. `products.csv` contains 210 unique product SKUs: 120 from the first visible worksheet `原创-在售产品` of the private Original Design catalog, and 90 from `Brunch Brother新品` of the private Brunch Brother catalog. Private source workbooks must remain outside the public repository.

For a record, `source_sheet` and `source_row` identify the exact supplier worksheet and **1-based Excel row**. To verify the original product fields, locate `B<row>` (SKU), `C<row>` (Chinese product name), plus the packaging columns specified below. These coordinates are provenance pointers, **not** a substitute for possessing the private source workbooks; public repository tests cannot independently re-compare source rows without them.

The importer reads allowlisted cells. Original Design: B = SKU, C = name, E = raw packing, F = carton units. Brunch Brother: B = SKU, C = name, F/G/H = unit/inner/master information, I = carton quantity. The Brunch Brother import checks numerical H against I. The Original Design import checks the final numeric component of E against F, except for two explicit, user-confirmed exceptions. Missing, zero, non-integer, or conflicting carton quantities cause an import error; they are **not silently replaced or inferred**.

## CSV fields

| Field | Type / format | Meaning, derivation, and limitations |
| --- | --- | --- |
| `sku` | nonempty string | Product identifier from source column B; unique across both catalogs. |
| `name_zh` | UTF-8 string | Original Chinese product name from source column C; source spelling is preserved. Not a translated product title. |
| `collection` | enum string | `Original Design` or `Brunch Brother`, determined by source workbook. |
| `category` | string | **Heuristic** English category inferred by keyword matching on `name_zh`; not supplier-certified. `Other / Review` means manual categorization is needed. |
| `size_hint` | string or blank | Name-derived size token such as A5/B6 when detected; blank when absent. Not a measurement or guaranteed fit. |
| `packing_raw` | string | Original Design: literal source E packing expression, e.g. `1/24/48`; Brunch Brother: labeled F/G/H unit/inner/master values. Descriptive only; **do not assume the final component is the verified case size**. |
| `units_per_carton` | positive integer | Units per supplier case: Original Design F, Brunch Brother I, or one of the two user-confirmed overrides described below. This is the relevant quantity for minimum order units. |
| `moq_cartons` | integer, presently 1 | **Project-level order policy:** one full carton **per individual SKU**. It is not evidence of a separately signed supplier MOQ agreement or permission to combine SKUs in one carton. |
| `moq_units` | positive integer | `moq_cartons × units_per_carton` for **that same SKU**; currently equals `units_per_carton`. Not an order-wide total or mixed-case allocation. |
| `carton_qty_basis` | enum | `source` = carton value taken from the October 16 supplier snapshot; `user_confirmed` = explicit project-owner confirmation. It does **not** certify current supply/availability. |
| `source_sheet` | string | Exact visible worksheet name used as the record's row-level source. |
| `source_row` | positive integer | 1-based worksheet row for the record; interpret together with `source_sheet` and `collection`. |
| `image_path` | relative POSIX path | `images/<SKU>.webp` public product preview. Images may combine multiple source panels; not an assertion of stock or current sellability. |

The CSV header is English, while Chinese source product names and the original Chinese worksheet label are intentionally preserved to avoid changing supplier data.

## Carton evidence, exceptions, and Unknown

- The minimum **one carton applies separately to each SKU**. For example, ordering three different SKUs means one carton of each: three cartons, with the unit count calculated using each SKU's own `units_per_carton`. No shared/mixed-SKU carton, fractional carton, or split-carton fulfillment has been verified.
- `DTB6611-1` and `DTB6616-1` have `units_per_carton=112` with `carton_qty_basis=user_confirmed`. Their original `packing_raw=1/24/48` remains unaltered as a source trace. Do not use 48 as the case count for either SKU.
- Every **published** SKU currently has a positive integer carton quantity. This is a validation requirement of the importer; it does not prove a fresh supplier re-confirmation of all 210 quantities.
- **Unknown policy:** Live inventory, supplier price, EXW cost, rebates, availability, lead time, U.S. resale rights, and seller acceptance of this minimum are **Unknown** and are not public CSV fields. If a future SKU has no defensible case quantity, mark its quantity **Unknown in a review/staging process and do not publish it with fabricated `moq_units`**. The current importer rejects such a source until resolved; it does not support `Unknown` as a published `units_per_carton` value.
- `Other / Review` (category) and blank `size_hint` signify specific uncertainty; they are not evidence of missing carton quantities.

## Reproduction and tests

Use Python 3.10+ and Pillow to regenerate CSV and WebP assets from private files, as described in the root README. Run `python3 -m unittest -v test_import` to check the published CSV, image paths, uniqueness, formula escaping, one-carton arithmetic, exceptions and some known examples. These repository tests **cannot** establish the accuracy of private workbook-to-CSV reconciliation without the private workbooks, and cannot independently confirm live supplier terms or image license scope.

## Public/private boundary

Public: SKU, Chinese product name, collection, heuristic category, size hint, carton packaging information, per-SKU project MOQ, provenance pointers and licensed-for-publication product previews (authorization reported by the project owner; underlying rights are retained by respective owners). Private: source XLSX workbooks, supplier EXW costs and prices, inventory, rebates, order details, any personal data, tokens, passwords, local environment settings and unpublished supplier correspondence. `.gitignore` is preventive only; it does not remove data or author/committer emails from **existing commit history**.

## Claims discipline

Phase 1 supplies a reproducible **public catalog snapshot**. It is not a live retailer-matching system, confirmed U.S. distribution contract, current supplier inventory feed, or production procurement platform. Status statements must distinguish successful local tests from GitHub CI checks and distinguish project-owner statements from independent documentary verification.
