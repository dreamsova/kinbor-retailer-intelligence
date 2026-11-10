# Architecture and engineering decisions

The product boundary is a source-linked research brief for a human, not automatic buyer selection. The preserved catalog supplies SKU/image/source/carton facts; retailer pages supply timestamped observations; matching supplies explicitly labelled hypotheses.

```mermaid
flowchart TD
    CLI[research.py: explicit acquisition mode] --> REST[tinyfish_client.py: direct REST]
    REST --> SEARCH[Optional Search: discover URLs only]
    REST --> FETCH[Fetch: bounded official-page retrieval]
    SEARCH --> FETCH
    FETCH --> NORMAL[research.py: scope checks and normalization]
    CONNECTOR[Saved connected TinyFish product observations] --> PRODUCT[product_evidence.json]
    NORMAL --> PRODUCT
    NORMAL --> OLD[Frozen research bundles: original receipts and category comparator]
    PRODUCT --> MATCH[matching.py: compatible format and specific shared traits]
    CATALOG[products.csv + images/: immutable 210 SKUs] --> MATCH
    NOTES[sku_visual_notes.json: 45 analyst notes] --> MATCH
    MATCH --> OUTPUT[matching.json: 210 candidates + style_brief.md]
    OUTPUT --> EVAL[eval.py: 36 comparison rows, human responses pending]
    MATCH -. explicit opt-in .-> VISION[vision.py: optional OpenAI image input]
    VISION -. no live validation yet .-> OUTPUT
```

## Module responsibilities

| Module | Responsibility and boundary |
|---|---|
| `research.py` | Official-domain discovery, page normalization, source evidence, catalog joins, output writing and offline validation. `--product-evidence` adds product-first acquisition and current style outputs. |
| `tinyfish_client.py` | Fixed official API origins, environment credentials, bounded retries/budgets, request receipts and explicit failures. Search/Agent helpers are separate capabilities; Agent is not an automatic fallback. |
| `matching.py` | Small inspectable vocabulary and functional compatibility rules. Retains every SKU, supporting evidence, counterevidence and uncertainty; never fills a category quota. |
| `vision.py` | Optional bounded image transmission and model inference; disabled by default. |
| `phase2.py` | Validates the combined historical tables and displays current style pointers. Existing `current_pilot` CSV labels belong to the earlier category run. |
| `eval.py` | Deterministic comparison sampling, separate A/B key, response-preserving generation and summaries of actual responses only. |
| `import.py` | Frozen local importer. Exports allowlisted catalog fields and sanitized product images; private sources are not required for the public demo. |

## Research and evidence contracts

Search snippets can nominate a URL. Only fetched official page content can support a retailer observation. An external shop requires observed linkage from the official site; an explicit product URL alone cannot authorize it. URLs, observation times, quotes, acquisition provenance and missing values remain visible.

The direct client limits pages, attempts and scheduling time, honors bounded throttling/backoff, refuses credential-forwarding redirects and blocks before transport when credentials are absent. Partial URL failures remain partial; HTTP 200 does not prove a complete run. Usage counts do not establish billed cost. The [API notes](TINYFISH_API.md) document the existing implementation and historical provider references.

The current 19-product capture came from connected TinyFish Search/Fetch tools. The adjacent `api_receipt.json` files authenticate older Python REST runs, not that newer capture. New REST product acquisition is covered by mocks; current cleanup checks make no fresh live calls.

## Matching and abstention

An eligible style hypothesis needs an individually inspected catalog image, a specific product observation, a compatible functional family and sufficiently specific overlapping traits. Retailer tags are inferred from observed text, not image pixels. Generic plain covers alone are insufficient; a refill needs compatibility evidence to stand in for a notebook. There is no retailer-diversity rule. SKU order stabilizes display ties only.

The default preview cap is four, not a minimum. Atlas displays one hypothesis; Shorthand displays four of eight supported review hypotheses; Wonder Fair displays none. All three retain 210 candidate records. The 165 catalog images without notes cannot support a style judgement in this baseline. This deliberately small vocabulary and sample can miss good matches; abstention is uncertainty, not evidence that a store dislikes the catalog.

## Optional image assessment

`vision.py` implements image input through the fixed OpenAI Responses endpoint. It requires explicit permission for these specific images, `--vision --authorize-openai-images`, `OPENAI_API_KEY` and an image-capable `KINBOR_VISION_MODEL`. At most eight already-supported, hash-checked catalog WebPs and three public retailer image URLs are sent in one request with `store: false`. Private supplier documents and arbitrary uploads are excluded. Permission to transmit is distinct from publication rights.

No live model assessment is saved: all three receipts contain zero requests and no assessments. Missing permission, credentials, model or images, refusal and invalid results keep the offline baseline and `MULTIMODAL LIVE NOT VALIDATED`. Model output would still be inference pending human review; access, model availability and quality need an enabled pilot.

## Evaluation and preservation

Automated tests exercise joins, deterministic outputs and failure boundaries. They do not establish recommendation quality, private workbook reconciliation, image rights, current inventory or commercial outcomes. The 36-row partial-blind review is pending, and the changed discovery evidence confounds any attempt to attribute future preference differences solely to the matcher. See the [evaluation protocol](MATCHING_EVALUATION.md).

The 214 Phase 1 file paths and hashes, complete pilot bundles and historical reports stay in place. Moving only non-frozen tests avoids rewriting serialized source paths, receipt hashes and image links. The [read-only verifier](../scripts/verify_repository.py) checks saved evidence and preservation without regenerating it. [Baseline guide](BASELINES.md) explains the coexistence of old and new artifacts.
