# Kinbor Retailer Intelligence

Evidence-linked SKU review for a preserved **210-SKU Kinbor catalog**. Phase 2 now compares actual retailer product observations with an explicitly annotated subset of the real SKU images. It does not rotate categories or fill a recommendation quota.

Start with the current briefs: **[Atlas](phase2/live/atlas/style_brief.md)** · **[Shorthand](phase2/live/shorthand/style_brief.md)** · **[Wonder Fair](phase2/live/wonder-fair/style_brief.md)**. Each shows why a specific SKU merits review, source product/image URLs, visible SKU features, contrary evidence, carton quantity and unresolved questions. `matching.json` retains every one of the 210 candidates, including unassessed and rejected hypotheses.

## What actually changed

The old `evidence_review_v2` selected categories, rotated collections and used SKU spelling to break display ties. Its four picks per store were not evidence of aesthetic fit. That implementation and the original saved API bundles remain **frozen comparators**, explicitly invoked for evaluation; category-only evidence now produces **zero recommendations by default**.

The new small matcher requires an individually inspected SKU image, a specific official retailer product observation, a compatible functional format, and sufficiently specific shared design features. Generic “plain cover” alone is insufficient; a refill never substitutes for a notebook without compatibility evidence. Equal evidence uses SKU order only for stable display. No store-diversity quota applies. A limited sample and simple vocabulary can miss good products: unannotated images are **unassessed**, not negative labels.

| Current pilot | Official product observations | Review candidates | Evidence-based change |
|---|---:|---|---|
| Atlas Stationers | 7 | `DT55566` | Translucent purple pouch compared with the listed Hightide transparent-front A6 case; dimensions/construction and 100-unit carton acceptance remain unverified. The blind-box gel pen is no longer auto-picked because Atlas lists pens. |
| Shorthand | 6 | `DT54744`, `DT54726`, `DT54729`, `DTYC0006` | Checker/geometric and botanical cover hypotheses tied to actual Checker Black and Botanical Archway notebook pages; handedness, gold foil, binding and exact artwork differ or are unverified. |
| Wonder Fair | 6 | None | Mixed artist stationery, animal memo pads and restrained notebooks do not yet support a sufficiently specific same-format match in the inspected subset. **Insufficient evidence**, rather than invented recommendations. |

**MULTIMODAL LIVE NOT VALIDATED.** No visual-model API key was available, so no live model assessment was made. The 45 SKU image notes came from local Codex image inspection and are labelled analyst inference, pending human review. Retailer image URLs were observed, but their pixels were not assessed. This is a conservative rules baseline with better evidence and abstention, **not proven improvement in selection quality**.

## Reproduce offline

Python 3.10+; Pillow is needed for the unchanged importer/image tests.

```bash
python3 -m pip install Pillow
python3 -m unittest discover -v
python3 matching.py --pilot-dir phase2/live/atlas --validate
python3 matching.py --pilot-dir phase2/live/shorthand --validate
python3 matching.py --pilot-dir phase2/live/wonder-fair --validate
python3 phase2.py
python3 eval.py --summarize phase2/reviews.csv
```

To regenerate style outputs, omit `--validate`. To create a **new** worksheet without replacing responses:

```bash
python3 eval.py --generate --output work/reviews-round2.csv
```

The supplied [reviews.csv](phase2/reviews.csv) has **36 blank A/B comparisons**, 12 real SKUs per shop, including old picks, new hypotheses and deliberate design/function challenges. The separate mapping key is withheld from reviewers. Follow the [evaluation protocol](docs/MATCHING_EVALUATION.md). No user gold labels, accuracy, preference rate, saved time, sales result or improvement percentage exists yet.

## Acquire fresh product evidence

`tinyfish_client.py` remains the direct official REST transport. Securely inject `TINYFISH_API_KEY` into the process environment; no keys in chat, files or command arguments. Missing credentials fail before transport with a blocked receipt, never an implicit fallback.

```bash
python3 research.py --mode tinyfish --url https://www.atlasstationers.com/ \
  --product-evidence --max-pages 10 --output-dir work/atlas-new
```

This opts into bounded product-first discovery, writes `product_evidence.json`, and runs the new matcher. Repeat `--product-url` for known official product pages; explicit URLs still cannot authorize an unlinked external shop. The official homepage can establish a linked shop domain. Search is optional URL discovery, never assortment proof. Account/cart/checkout actions are excluded. Missing product images, explicit prices or currencies stay `Unknown`. REST image links are requested only in product mode; the metadata-rich connector response is not claimed to be identical to REST. See [API contract and limits](docs/TINYFISH_API.md).

For this pilot, the connected official TinyFish **Search/Fetch** tools supplied new public product evidence: 2 Search + 9 Fetch calls, 38 URL requests including repeats, 37 successful results and one discovery 404. The receipts in `product_evidence.json` distinguish these executions from the **previous** direct Python API runs in `api_receipt.json`. A TinyFish REST key was absent locally; the new REST product mode was tested with mocks, not a fresh authenticated REST call. Billed costs are **Unknown**. Product pages are observed public listings, not verified current inventory; some pages showed out-of-stock or contradictory availability text.

## Optional image assessment

`vision.py` implements genuine image input to the fixed **OpenAI Responses API**. Default is off. To enable, securely configure `OPENAI_API_KEY` and an image-capable `KINBOR_VISION_MODEL`, check that specific image transmission is permitted, and use both explicit flags:

```bash
python3 matching.py --pilot-dir work/atlas-new --vision --authorize-openai-images
```

OpenAI then receives at most 8 already-supported, hash-checked catalog WebP images and 3 public retailer image URLs in one request, with `store: false`. No supplier workbook, quotation, inventory, arbitrary uploaded image or secret is accepted. This flag confirms permission for this service, not publication rights; public visibility alone does not grant an image license. Without permission/key/model/images, on refusal or invalid output, the result remains `MULTIMODAL LIVE NOT VALIDATED` and keeps the offline baseline. All model claims are inference, with citations/counterevidence and pending human review. Model availability, access and quality require a real enabled pilot. [Official image-input documentation](https://developers.openai.com/api/docs/guides/images-vision).

## Preserved scope

`products.csv`, all **210 WebP images**, `import.py` and Phase 1 test/source provenance retain their **214 preservation hashes**. Each individual SKU requires **one separate full carton** under the project rule. `DTB6611-1` and `DTB6616-1` remain **112 units/carton**. Supplier/buyer acceptance, materials, paper performance, Kinbor retail/landed prices, authorization, brand relationships, current stock and buying intent remain unverified. No outreach, dashboard, CRM or checkout was added.

Retailer images are URL references only, not downloaded or republished in GitHub. Catalog-image rights remain with their owners. Private supplier workbooks, quotations and credentials remain excluded. No user-uploaded private material was sent to a new model service.

`phase2/sku_matches.csv`, `retailers.csv`, `evidence.csv`, original `research.json` and older `buyer_brief.md` retain the pre-change comparator and 17 stores marked `legacy_not_revalidated`; they are not the active style shortlist. The [current queue](phase2/review_queue.md) points to the new briefs. [Validation and spot checks](phase2/style_validation_report.json) record measured checks and remaining limitations. No deleted historical files were restored.
