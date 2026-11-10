# Kinbor Retailer Intelligence

Research official retailer websites, review source evidence, and compare their observed assortment with a **210-SKU Kinbor catalog**. The Python CLI calls the TinyFish REST API directly and produces an illustrated buyer brief, evidence table, API receipt, and audit of every catalog SKU.

## What it does

- Keeps retailer observations linked to source URLs and retrieval times.
- Joins candidate products to their actual SKU, image, source row, and carton quantity.
- Separates product fit, evidence strength, and buyer access for human review.

Start with the saved **[Atlas buyer brief](phase2/live/atlas/buyer_brief.md)** and its **[API receipt](phase2/live/atlas/api_receipt.json)**. The brief links product images and evidence; the adjacent `research.json`, `evidence.csv`, `candidate_audit.csv`, and `recommendations.csv` contain the complete review data. This is the single canonical Atlas example, retained under `phase2/live/` so the same files support validation and CSV integration.

## How to run

Use Python 3.10+. Research and saved-output validation use the standard library; the full test suite and image importer also require Pillow.

```bash
python3 -m pip install Pillow
python3 -m unittest discover -v
python3 research.py --mode validate --output-dir phase2/live/atlas
python3 research.py --mode validate --output-dir phase2/live/shorthand
python3 research.py --mode validate --output-dir phase2/live/wonder-fair
python3 phase2.py
```

These checks run offline against saved results. They do not make new API calls. `phase2.py` validates the 20-store CSV joins, image/source/carton references, and all **214 Phase 1 preservation hashes**. To regenerate the tied review queue from the saved three-store results:

```bash
python3 phase2.py --integrate-pilots --pilot-root phase2/live
```

For **new live research**, securely configure `TINYFISH_API_KEY` in the process environment, then run:

```bash
python3 research.py --mode tinyfish --url https://www.atlasstationers.com/ \
  --output-dir work/atlas --collect-usage
```

This command makes API requests and may incur provider charges. The default acquisition uses the homepage and one bounded batch of official links, with no automatic fallback. Missing credentials produce a blocked receipt and exit 2. See [API setup, modes, budgets, and errors](docs/TINYFISH_API.md) or `python3 research.py --help` before running new research.

## Saved results and limits

The three saved bundles are evidence from prior direct Python API executions; validating or integrating them does **not** repeat those live calls.

| Retailer | Observed pages | Catalog rows audited | Preview candidates |
|---|---:|---:|---:|
| [Atlas Stationers](phase2/live/atlas/buyer_brief.md) | 6 | 210 | 4 |
| [Shorthand](phase2/live/shorthand/buyer_brief.md) | 6 | 210 | 4 |
| [Wonder Fair](phase2/live/wonder-fair/buyer_brief.md) | 4 | 210 | 4 |

The **[review queue](phase2/review_queue.md)** contains three tied research candidates. The remaining 17 retailers retain historical records marked `legacy_not_revalidated`. These are hypotheses for review, not confirmed buyers or a ranked top five. Categories and shared product attributes support matching inferences; aesthetic fit, current inventory, resale authority, buyer interest, commercial terms, and order feasibility remain unconfirmed. Read each retailer's complete submission policy before any future contact. No outreach occurs in this workflow. Billed API cost is Unknown where receipts contain no monetary amount.

Each individual SKU requires **one separate full carton** under the project's ordering rule; supplier or retailer acceptance of that rule is unverified. `DTB6611-1` and `DTB6616-1` remain **112 units/carton**. The catalog is an October 16, 2026 snapshot. Product images and source coordinates remain unchanged; image rights stay with their owners and are not licensed here for third-party reuse.

## Repository guide

| Path | Purpose |
|---|---|
| `products.csv`, `images/`, `import.py` | Preserved Phase 1 catalog and importer. |
| `research.py`, `tinyfish_client.py` | Acquisition, provenance, full-catalog matching, and output validation. |
| `phase2.py`, `phase2/*.csv`, `phase2/review_queue.md` | Combined retailer dataset, joins, and human-review queue. |
| `phase2/live/` | Three complete saved API result bundles required for reproducible validation. |
| `test_*.py` | Offline regression tests, including the unchanged Phase 1 tests. |
| `docs/` | [Data dictionary](docs/DATA_DICTIONARY.md), [API notes](docs/TINYFISH_API.md), [case study](docs/CASE_STUDY.md), and preservation manifest. |

See the [validation report](phase2/validation_report.json) for this cleanup's recorded checks and scope. Older connector captures, duplicate pilot outputs, obsolete briefs, and debug logs remain recoverable in Git history. Private supplier workbooks, quotations, inventory, and credentials are excluded from the public repository.
