# Current style outputs and frozen baselines

Old and new outputs remain adjacent to preserve source paths, receipt hashes and historical comparisons. Their filenames describe different stages; “live” is a legacy directory name, not a guarantee of fresh inventory.

| Artifact | Scope | How to read it |
|---|---|---|
| `phase2/live/*/style_brief.md` | Current style hypotheses | Primary human-readable entry point. Includes counterevidence, carton constraints and pending validation. |
| `phase2/live/*/matching.json` | Current style audit | All 210 candidates per store, with reasons, statuses and the displayed shortlist. |
| `phase2/live/*/product_evidence.json` | Current product observations | Newer connected TinyFish acquisition and its receipts; not authenticated by the older REST receipt. |
| `phase2/sku_visual_notes.json` | Current catalog-image notes | 45 local Codex image observations, analyst inference pending human review. |
| `phase2/live/*/{research,api_receipt}.json` | Frozen direct REST research | Previously saved Python executions. Retained with all dependent CSVs and original brief. |
| `phase2/live/*/{evidence,candidate_audit,recommendations}.csv`, `buyer_brief.md` | Frozen category baseline | Reproducible `evidence_review_v2` comparator, including the old four picks per store. Not current style selections. |
| `phase2/{retailers,sku_matches,evidence}.csv` | Frozen combined tables | 20 historical retailer records, 74 matches and 267 evidence rows. Old schema has three `current_pilot` records and 17 `legacy_not_revalidated`; this does not make their category matches current style recommendations. |
| `phase2/review_queue.md` | Mixed navigation retained | Current style links at top, then historical category queue. Use the style briefs for current hypotheses. |
| `phase2/reviews.csv`, adjacent `.key.csv` | Pending evaluation | 36 blank comparisons and separate A/B mapping; keep the key away from reviewers and do not publish future responses. |
| `phase2/{validation_report,style_validation_report}.json` | Historical check records | Evidence of their own checks and timestamps; not a substitute for a new test run. |
| `docs/CASE_STUDY.md` | Historical narrative | Describes the earlier direct REST/category cleanup. |

The old matcher rotated supported categories/collections and used SKU spelling for stable display. Its four picks were not evidence of aesthetic preference. The current matcher requires product-specific support and inspected SKU imagery, does not fill a quota and can abstain. Fewer candidates do not prove improved quality. The evidence acquisition also differs, limiting algorithm-only comparison.

## Read-only checks

```bash
python3 scripts/verify_repository.py
python3 phase2.py
python3 research.py --mode validate --output-dir phase2/live/atlas
python3 matching.py --pilot-dir phase2/live/atlas --validate
```

`phase2.py` without mutation flags validates the combined category tables and current style pointers. Its historical `--brief` option points to the old buyer brief, so use the linked style briefs for a current demo. Repeat per-store checks for Shorthand and Wonder Fair, or use the verifier for all three.

## Regeneration boundaries

`phase2.py --refresh` and `--integrate-pilots` write combined historical tables and the queue. `matching.py` without `--validate` writes style outputs. `eval.py --generate` writes a worksheet and key; it refuses replacement unless `--force` is supplied. Use new ignored `work/` directories for experiments and preserve existing responses. No regeneration is required for the saved demo.

Phase 1 remains byte-for-byte protected by [the original manifest](phase1_manifest.json): `products.csv`, 210 WebPs, `import.py`, `test_import.py` and `docs/DATA_DICTIONARY.md`. This cleanup relocates only the other nine tests, updates their imports and adds navigation/check tooling. No raw capture, historical bundle or Git history is deleted or rewritten.
