# Documentation

Read the [project README](../README.md) first, then choose a route:

| Purpose | Read |
|---|---|
| Product / FDE interview walkthrough | [5-minute demo](DEMO.md) |
| System design, boundaries and tradeoffs | [Architecture](ARCHITECTURE.md) |
| Find current evidence and saved outputs | [Phase 2 evidence map](../phase2/README.md) |
| Separate old category previews from current style hypotheses | [Frozen baselines](BASELINES.md) |
| Direct REST setup, receipts and failure handling | [TinyFish API](TINYFISH_API.md) |
| Understand the pending 36-row human review | [Evaluation protocol](MATCHING_EVALUATION.md) |
| Catalog schema and immutable provenance | [Data dictionary](DATA_DICTIONARY.md) · [214-file manifest](phase1_manifest.json) |
| Historical direct API cleanup record | [Historical case study](CASE_STUDY.md) |
| Run tests after the directory cleanup | [Test guide](../tests/README.md) |

The current entry point is a `style_brief.md`. A `buyer_brief.md` is a preserved category-baseline artifact. Historical validation reports document their own execution time and scope; they do not report the latest tests. Run `python3 scripts/verify_repository.py` and `python3 -m unittest discover -v` for current offline checks.
