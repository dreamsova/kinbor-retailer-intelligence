# Current style outputs and frozen baselines

The repository is grouped by purpose: catalog data in `catalog/`, application code in `kinbor/`, and saved research in `examples/`. Current and frozen per-store artifacts remain together so their provenance can be compared.

| Artifact | Scope | How to read it |
|---|---|---|
| `examples/retailers/*/style_brief.md` | Current style hypotheses | Main review entry point, with counterevidence, carton constraints and pending validation. |
| `examples/retailers/*/matching.json` | Current style audit | All 210 candidates per store, including the displayed shortlist and unassessed products. |
| `examples/retailers/*/product_evidence.json` | Current product observations | Connected TinyFish acquisition and its receipts; not authenticated by the older REST receipt. |
| `examples/sku_visual_notes.json` | Current catalog-image notes | 45 local Codex image observations, analyst inference pending human review. |
| `examples/retailers/*/{research,api_receipt}.json` | Frozen direct REST research | Previously captured Python executions; retained with dependent CSVs and the original brief. |
| `examples/retailers/*/{evidence,candidate_audit,recommendations}.csv`, `buyer_brief.md` | Frozen category baseline | `evidence_review_v2` comparator, including the old four picks per store. These are not current style selections. |
| `examples/baselines/{retailers,sku_matches,evidence}.csv` | Frozen combined tables | 20 historical retailer records, 74 matches and 267 evidence rows. The old schema has three `current_pilot` records and 17 `legacy_not_revalidated`. |
| `examples/review_queue.md` | Review navigation | Current style links followed by the historical category queue. |
| `examples/evaluation/reviews.csv`, adjacent `.key.csv` | Pending evaluation | 36 blank comparisons and separate A/B mapping; withhold the key from reviewers and keep future responses private. |
| `examples/history/{validation_report,style_validation_report}.json` | Historical check records | Their own checks and timestamps, not the latest test result. |
| `docs/CASE_STUDY.md` | Historical narrative | The earlier direct REST/category cleanup. |

The old matcher rotated supported categories/collections and used SKU spelling for stable display. Its four picks were not evidence of aesthetic preference. The current matcher requires product-specific support and inspected SKU imagery, does not fill a quota and can abstain. Fewer candidates do not establish improved quality. Acquisition evidence also differs, limiting algorithm-only comparison.

## Read-only checks

```bash
python3 scripts/verify_repository.py
python3 -m kinbor.pipeline
python3 -m kinbor.research --mode validate --output-dir examples/retailers/atlas
python3 -m kinbor.matching --pilot-dir examples/retailers/atlas --validate
```

The pipeline validates the combined category tables and current style pointers. Use the linked style briefs for a current demo. Repeat per-store checks for Shorthand and Wonder Fair, or use the verifier for all three.

## Regeneration boundaries

`python3 -m kinbor.pipeline --refresh` and `--integrate-pilots` write combined historical tables and the queue. Matching without `--validate` writes style outputs. Evaluation `--generate` writes a worksheet and key; it refuses replacement unless `--force` is supplied. Use new ignored `work/` directories for experiments and preserve existing responses. No regeneration is required for the saved demo.

## Preservation after relocation

The [original Phase 1 manifest](phase1_manifest.json) remains unchanged, with all **214 original hashes**: `products.csv`, 210 WebPs, `import.py`, `test_import.py` and `docs/DATA_DICTIONARY.md`. Catalog files now live under `catalog/`; [the path resolver](../kinbor/paths.py) maps their original manifest names to their new locations. The frozen importer and catalog test stay beside their data, with their bytes unchanged. The data dictionary retains its historical path examples; use the [current catalog guide](../catalog/README.md) for commands.

Raw JSON/CSV captures, receipt hashes, SKU identifiers and provenance fields retain their original values. Serialized catalog `image_path` values such as `images/<SKU>.webp` are relative to `catalog/`. Historical references such as `live/atlas/research.json` are resolved to `examples/retailers/atlas/research.json` by the application, rather than rewriting source records. Markdown navigation and image links use the new layout. No source evidence or Git history is deleted or rewritten.
