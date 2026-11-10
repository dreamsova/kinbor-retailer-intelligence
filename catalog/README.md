# Preserved product catalog

**210 unique SKUs and 210 WebP product images**, from the October 16, 2026 catalog snapshot. This is not live supplier inventory or a binding wholesale quotation.

```text
products.csv     Public allowlisted SKU, image, source and carton facts
images/          One WebP per SKU
import.py        Preserved private-workbook importer
test_import.py   Preserved catalog tests, kept beside their data
```

CSV `image_path` values such as `images/DT55566.webp` are relative to this catalog directory. The original values are preserved.

The [data dictionary](../docs/DATA_DICTIONARY.md) documents the schema and source limitations. Its original bytes and historical path examples are retained. The [original preservation manifest](../docs/phase1_manifest.json) still contains all 214 original hashes; [path resolution](../kinbor/paths.py) maps its legacy catalog filenames to this directory without changing the protected bytes.

Each individual SKU requires one separate full carton under the project rule. `DTB6611-1` and `DTB6616-1` remain 112 units/carton. Supplier and buyer acceptance of those terms is unverified.

Run public-data checks from the repository root:

```bash
python3 -m unittest -v catalog.test_import
python3 scripts/verify_repository.py
```

Public checks do not need the private workbooks or Pillow. To inspect the preserved importer interface:

```bash
python3 catalog/import.py --help
```

An authorized private-source image rebuild additionally requires [Pillow](requirements.txt), installed with `python3 -m pip install -r catalog/requirements.txt`. Keep source workbooks outside the repository, and direct any regenerated CSV and image folder together into an ignored `work/` directory. Do not replace this preserved snapshot during a demo. Private prices, inventory, quotations and credentials are excluded from the public catalog; image rights remain with their owners.
