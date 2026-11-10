# Five-minute demo walkthrough

Run from the repository root with Python 3.10+. This demonstration reads saved evidence; no credential, private workbook or live API request is needed.

## 1. Frame the product problem — 30 seconds

“A brand researching independent retailers needs to connect actual products to observed assortments, with evidence and ordering constraints. This prototype uses TinyFish research to produce reviewable hypotheses. It preserves 210 real catalog SKUs and images and has three actual-site research pilots.”

Be explicit that the stores did not participate in a commercial pilot. The available result is a research artifact, with human quality review and buying outcomes still pending.

## 2. Trace one candidate — 90 seconds

Open the [Atlas style brief](../phase2/live/atlas/style_brief.md). Inspect SKU `DT55566`, its actual catalog image, the linked Hightide product observation and its 100-unit carton requirement. The shared translucent/transparent trait supports investigation; construction, dimensions, material and buyer acceptance are unresolved.

Open [Atlas product evidence](../phase2/live/atlas/product_evidence.json) for captured observations and receipts, then [matching.json](../phase2/live/atlas/matching.json) for the full 210-candidate audit. The adjacent [older buyer brief](../phase2/live/atlas/buyer_brief.md) is a frozen category comparator, not the current recommendation.

```bash
python3 matching.py --pilot-dir phase2/live/atlas --validate
python3 research.py --mode validate --output-dir phase2/live/atlas
```

Both commands validate saved data. The first checks current style outputs; the second checks the older research bundle. Neither refetches a website.

## 3. Show abstention and display limits — 60 seconds

Open the [Wonder Fair brief](../phase2/live/wonder-fair/style_brief.md): zero selections means insufficient support in the inspected subset, not a verdict on all 210 products. Then compare [Shorthand](../phase2/live/shorthand/style_brief.md): four displayed candidates come from eight supported review hypotheses under the default cap. A complete four-item list is not a success metric.

```bash
python3 matching.py --pilot-dir phase2/live/wonder-fair --validate
python3 matching.py --pilot-dir phase2/live/shorthand --validate
```

## 4. Show engineering evidence — 60 seconds

```bash
python3 scripts/verify_repository.py
python3 -m unittest discover -v
```

Expected verifier facts: **214 matching preservation hashes**, **210 SKUs**, **210 images**, **three validated saved research bundles**, **three validated current style bundles**, **19 product observations**, **45 image notes** and **36 pending comparison rows**. The test suite has 111 tests covering catalog facts, source/receipt drift, request boundaries, failures, matching and evaluation behavior. Transport mocks demonstrate code behavior, not fresh API or model execution.

Use the [architecture diagram](ARCHITECTURE.md) to explain why Search discovery, Fetch observations, deterministic matching and human review remain separate. Historical report timestamps describe older checks; current command output describes this run.

## 5. Close with the next decision — 60 seconds

```bash
python3 eval.py --summarize phase2/reviews.csv
```

The 36 rows are pending: no accuracy, preference improvement or measured time saving is established. Next, collect independent reviews and disagreement reasons, inspect retailer image pixels in an explicitly authorized model pilot, and verify physical samples and commercial feasibility. The baseline/new comparison also changes acquisition evidence, so it cannot isolate the algorithm's effect.

For a new evaluation round, write to a new ignored file instead of replacing responses:

```bash
python3 eval.py --generate --output work/reviews-round2.csv
```

Give reviewers only the worksheet and allowed sources, withholding the adjacent A/B key until responses are locked. Keep real reviewer responses private. Follow the [evaluation protocol](MATCHING_EVALUATION.md).

## Optional preparation after the saved demo

For fresh TinyFish research, follow the [live configuration guide](TINYFISH_API.md) and write to `work/`, not a committed pilot directory. To regenerate an offline style brief, first copy the whole saved pilot bundle into `work/` and run `matching.py --pilot-dir` on that copy without `--validate`. Do not run `phase2.py --refresh`, `--integrate-pilots`, or an evaluation `--force` command during a read-only demonstration. [Frozen baseline guide](BASELINES.md).
