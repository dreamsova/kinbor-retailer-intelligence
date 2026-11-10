# TinyFish direct API implementation

Implementation reference date: November 9, 2026 (Chicago). `kinbor/tinyfish_client.py` remains a small Python standard-library REST client; no Work connector or manually imported capture is required for `python3 -m kinbor.research --mode tinyfish`.

Current matching update: `--product-evidence` prioritizes actual product pages, optionally follows one observed shop/collection discovery hop within the budget, and adds the documented `image_links: true` request option. It writes `product_evidence.json` and automatically runs `kinbor/matching.py` for a current `style_brief.md` plus the full 210-SKU `matching.json` audit. Repeat `--product-url` for known official product URLs; an explicit URL does not authorize an unrelated commerce domain. Category-only acquisition now abstains by default.

The [official Fetch reference](https://docs.tinyfish.ai/fetch-api/reference) was checked for this extension. REST product mode requests `image_links`, not the connector-only `page_metadata` option. It retains documented response description/image links when available; missing or ambiguous image, price and currency values stay `Unknown`. The public HTTP parser can read actual HTML JSON-LD/Open Graph product metadata. None of these paths fetches image bytes.

The new 19-product pilot used the connected official TinyFish Search/Fetch tools, not a new Python REST execution: 2 Search, 9 Fetch, 38 requested URLs including repeats, 37 successful URL results and one discovery 404. Acquisition receipts in each `product_evidence.json` identify this scope (the Atlas/Shorthand receipt is shared and must not be counted twice). No local REST or visual-model credential was available. The older `api_receipt.json` files and the direct-run statements below describe the **prior frozen comparator runs**; they do not authenticate the new product acquisition. New matching results explicitly retain `MULTIMODAL LIVE NOT VALIDATED`; billed costs are Unknown.

## Official endpoints and choice

| Capability | Documented endpoint | This project |
|---|---|---|
| Search | `GET https://api.search.tinyfish.ai` | Optional `--tinyfish-search`; official-domain discovery only. |
| Fetch | `POST https://api.fetch.tinyfish.ai` | Default live acquisition; homepage then bounded official-link batch. |
| Fetch usage | `GET https://api.fetch.tinyfish.ai/usage` | Optional `--collect-usage`; reconciles this client's provider request IDs. |
| Search usage | `GET https://api.search.tinyfish.ai/usage` | Available in the client; not invoked by the research CLI. |
| Agent queue | `POST https://agent.tinyfish.ai/v1/automation/run-async` | Explicit client helper, not automatic CLI fallback. |
| Agent poll | `GET https://agent.tinyfish.ai/v1/runs/{id}` | Client helper with bounded polling. |
| Agent cancel | `POST https://agent.tinyfish.ai/v1/runs/{id}/cancel` | Client helper verifies the returned terminal state. |

Search and Fetch suffice for the observed public retailer pages. Browser interaction was not needed for the three frozen direct REST runs. No Agent request, profile or vault was used. The optional Agent helpers are covered by network mocks. The older `research.json` / `api_receipt.json` bundles contain no live Agent or Search execution; the newer `product_evidence.json` acquisition includes the connected Search calls described above. Repository verification uses offline checks only.

The [official overview](https://docs.tinyfish.ai/) lists canonical public API surfaces. The implementation references the [Search reference](https://docs.tinyfish.ai/search-api/reference), [Fetch reference](https://docs.tinyfish.ai/fetch-api/reference), [Agent reference](https://docs.tinyfish.ai/agent/api/agent) and [run retrieval reference](https://docs.tinyfish.ai/api-reference/runs/get-run-by-id). Those references informed the existing implementation rather than older examples. The [cookbook](https://github.com/tinyfish-io/tinyfish-cookbook) and [competitor scout recipe](https://github.com/tinyfish-io/tinyfish-cookbook/tree/main/competitor-scout-cli) confirm the Search/Fetch/Agent separation; recipe fallbacks are not evidence of a successful API call.

## Authentication and safe configuration

REST uses `X-API-Key`. The CLI reads `TINYFISH_API_KEY` from the local process environment. Configure it through your execution environment's secure secret settings or secret manager and inject it into that process. The project does not read connector OAuth tokens or automatically load `.env` files. MCP/Work authentication does not substitute for the Python process's key. See [official authentication](https://docs.tinyfish.ai/authentication) and the [API key dashboard](https://agent.tinyfish.ai/api-keys).

For an interactive bash or zsh terminal, type the following, enter the key when the cursor waits, then press Enter. The value is not displayed or included in command history:

```bash
read -r -s TINYFISH_API_KEY
export TINYFISH_API_KEY
```

Never paste a key into chat, a command-line argument, source code or a report. `.env*` is ignored, but this is not permission to stage credential files. The code records no request headers or raw HTTP error bodies and redacts its active key from decoded responses. Only fixed official API origins are permitted; redirects are refused to avoid credential forwarding.

With no credential, direct mode writes a blocked receipt containing `LIVE API TEST BLOCKED — missing credential`, no authenticated request and no invented provider ID; the CLI exits 2. Configure the credential securely and rerun the same command. Connector imports and HTTP acquisition cannot satisfy this check.

## Fetch and discovery contract

The client submits JSON containing `urls`, `format: "markdown"`, `links: true`, `ttl: 0` and `per_url_timeout_ms: 45000`. `ttl: 0` requests a live retrieval rather than accepting any cached entry. The homepage response supplies official links; permitted category/contact/submission pages are prioritized before one further batch. An official shop link may authorize the linked commerce domain. Account, cart, checkout and other action paths are excluded.

Fetch returns `results[]` plus `errors[]`. Result text and links are checked against the requested retailer scope. HTTP 200 can contain per-URL failures, missing content or an incomplete batch; those outcomes remain partial/failed rather than becoming facts. Final URL redirects must stay within the approved scope. Search snippets, when enabled, only add URLs for subsequent Fetch, never proof of assortment or vendor acceptance.

Source-backed observations retain URLs and response-observation UTC times. API evidence rows use `epistemic_status: fact_observation` for the observed site statement. Product matching and shared-attribute interpretation remain inferences in candidate `match_basis`; unobserved or unsupported summary fields remain Unknown. Navigation-only category evidence is weaker than a product-specific listing.

## Budgets, errors and lifecycle

The research CLI defaults to six pages, four total API attempts and a 240-second scheduling budget. Change these with `--max-pages`, `--max-api-requests` and `--deadline` within the CLI's enforced bounds. Attempts include retries, optional Search and usage reads. The default two Fetch calls plus optional usage use three attempts; adding Search uses the fourth and leaves no spare retry within that cap.

The official Fetch contract allows at most 10 URLs per request and a per-URL timeout of 1–110000ms. It recommends at least a 150-second client timeout because the backend/CDN have their own ceilings. The client uses a 150-second request timeout, shortened by the remaining deadline; DNS and in-flight operations can still overrun a scheduling deadline. The CLI's `--timeout` flag controls public HTTP mode, not the API Fetch timeout.

The client observes `Retry-After` on 429, otherwise uses bounded exponential backoff; appropriate server failures and safe reads may retry. Authentication failures do not fall back to a different mode. A network timeout or ambiguous server failure during Agent submission yields `submission_outcome_unknown`, avoiding an automatic duplicate run and potential duplicate cost. Receipts preserve each request attempt and outcome. See [official error handling and rate headers](https://docs.tinyfish.ai/error-codes).

Agent queue returns a `run_id` and nullable `error`. Polling checks `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` and `CANCELLED`; the last three terminate the wait. Unknown states are rejected. A wait timeout can request cancellation, but cancellation is only reported from the response: a run may already be complete, or the cancellation can fail after the budget is exhausted. No cancellation success is assumed. The helper uses the generally available `agent_config.max_duration_seconds`; beta-only `mode/max_steps` are omitted. See [async submission](https://docs.tinyfish.ai/api-reference/automation/start-automation-asynchronously) and [Agent endpoint comparison](https://docs.tinyfish.ai/agent/api/agent/endpoints).

As documented at the check date, personal limits default to Search 30 requests/minute and Fetch 150 URLs/minute; organizations use their contract limits. Search's daily free allowance is 12,000 requests and Fetch's is 1,000 successful URLs, resetting at 00:00 UTC; usage beyond the allowance can charge the wallet. These are provider rules, not a guarantee of zero task cost. Agent concurrency and account entitlements differ. No wallet top-up, auto-reload change or paid Agent fallback is performed.

## Receipts and real usage

`api_receipt.json` records local execution, endpoint, client/provider request IDs, HTTP status, authenticated-response observation, UTC start/finish, duration, returned URL counts, rate headers, limits, fallback state and usage when available. The direct Fetch API has no browser run ID; null is correct. A local request ID is never presented as a provider-issued one.

`--collect-usage` reads one time-bounded Fetch usage page and keeps only records matching this client's provider request IDs. Other account activity is excluded. Usage can lag, the page is capped at 100 records, and missing matches remain uncertain. Per-URL usage records expose counts/status/latency; no returned money amount means billed cost is **Unknown**. URL count, a free allowance or elapsed seconds do not establish the invoice amount. See [Fetch usage](https://docs.tinyfish.ai/fetch-api/reference#usage-endpoint) and [Search usage](https://docs.tinyfish.ai/api-reference/list-search-usage).

The committed `examples/retailers/{atlas,shorthand,wonder-fair}/` receipts represent previously captured real Python API executions. This cleanup validates those saved files without making new live calls. Each final run has two authenticated Fetch responses and one authenticated usage response, all HTTP 200. They cover 6/6/4 successfully fetched pages and 210 SKU audits per store. Optional Search/Agent mocks are not live API evidence. Obsolete connector versions are recoverable from Git history.

## Commands and explicit non-API modes

```bash
# Current product-first mode; live credentials required and provider charges may apply:
python3 -m kinbor.research --mode tinyfish --url https://www.atlasstationers.com/ \
  --product-evidence --max-pages 10 --output-dir work/atlas-new
# Category research transport, retained for comparator compatibility:
python3 -m kinbor.research --mode tinyfish --url https://www.atlasstationers.com/ \
  --output-dir work/atlas --collect-usage
# Optional discovery, still direct API; consumes the default fourth attempt:
python3 -m kinbor.research --mode tinyfish --url https://www.atlasstationers.com/ \
  --output-dir work/atlas-search --tinyfish-search --collect-usage
python3 -m unittest discover -v
python3 -m kinbor.research --mode validate --output-dir examples/retailers/atlas
python3 scripts/verify_repository.py
python3 -m kinbor.pipeline
```

`public_http` (and its compatibility alias `public`) is direct public website acquisition, not TinyFish. `import` replays a normalized connector capture; `validate` checks saved outputs. These modes do not contact the TinyFish API. No mode sends retailer email, submits a form or buys products. The [historical validation report](../examples/history/validation_report.json) records its earlier checks and scope. The existing test suite and saved-output validation use the standard library; Pillow is needed only for actual image rebuilding from private workbooks. Test mocks prove boundary behavior only, not authentication or live site truth. Mutation flags such as `python3 -m kinbor.pipeline --integrate-pilots` rewrite historical combined outputs; see [regeneration boundaries](BASELINES.md#regeneration-boundaries) before using them.
