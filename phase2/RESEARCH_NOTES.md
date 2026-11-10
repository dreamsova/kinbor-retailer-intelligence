# Phase 2 evidence and operating notes

Research collected **2026-11-10 UTC / 2026-11-09 America/Chicago**. This is a desk-research pilot for an independent Kinbor catalog project, not customer discovery interviews, a distribution offer or a deployed customer procurement system.

## Scope and actual execution

20 unique U.S. retailer businesses; 74 actual catalog-SKU candidates (3–4 per business); 148 claim-level evidence rows. Multiple locations of the same business count once. The sample is a convenience sample of stationery, paper, gift and art/book-adjacent shops, not a representative U.S. market census. No pure bookstore was forced into the sample without stationery evidence.

Atlas was the first browser research pilot. The connected **TinyFish `run_web_automation` actually completed**: run `98bb203b-8683-4485-8f7b-fc157e5c2a3b`, [run receipt](https://agent.tinyfish.ai/runs/98bb203b-8683-4485-8f7b-fc157e5c2a3b). Provider reports 17 steps and 231 seconds. A first request was rejected before starting because the optional step cap requires beta access; the successful retry removed only that unsupported cap. There was one successfully started run, with no login/profile/vault use requested. The sanitized provider result is in `sources/tinyfish_atlas_run.json`. The run URL may require its owner's TinyFish login.

**The other 19 stores were researched with public web search/page reading, NOT verified TinyFish live API executions.** Their `web_open` method means a page was read through a web tool; its content may have been cached. `retrieved_at_utc` records the observation/retrieval time, not proof the retailer updated its site at that moment. No direct TinyFish API credential was read or exported.

TinyFish output was reviewed as fallible data. Unsupported claims such as an exhaustive 90+ brand count, superlative store size, definitive absence of Kinbor and the existence of an official linked “selling to us” policy were not adopted as verified facts. Its three precise product URLs could not be independently extracted, and subsequent HTTP checks returned **429**, not 404: they remain `provider_only`, unused by matches or scoring. Atlas notebook/planner/pen-storage collections and story/contact pages independently support the accepted facts. Raw provider output retains these limitations to make the review auditable.

## Read the CSVs

- `retailers.csv`: one business, one precise current physical-location address, owner/independence basis, observed categories/brands, policy status, public contact URL, separate scoring dimensions, all-candidate carton totals and unknown commercial feasibility.
- `evidence.csv`: unique evidence ID, retailer ID, claim type, short paraphrase, exact source URL, UTC timestamp, method, source class and verification limit. This is provenance, not an archive of entire copyrighted pages.
- `sku_matches.csv`: retailer/SKU pair, unchanged source name, **inferred** English descriptor/category, specific retailer fact/evidence ID and URL, inferred match reason, image path, original source-sheet/row pointers, carton quantities and unknowns.
- `link_checks.csv`: 38 HTTP/title spot checks, **35 reachable and 3 rate-limited (429)** in this run. An HTTP 200 or a page title does not validate a factual claim. No bypass/repeated requests were used on rate-limited product links.

`page_read` means the source page text supported the paraphrase; it does not certify a company's legal ownership, current stock or factual truth. `search_snippet_only` and `provider_only` are weaker and never used as primary SKU-match evidence. Oblation's mt brand and washi category are provisional, outside verified fields. Navigation/filter taxonomy supports a category's existence, not a named stocked product. Brand representation never implies Kinbor acceptance or matching paper quality.

Independence means a named owner/family/founder operation or an explicit independent-business statement; it permits locally owned businesses with several branches. Goods for the Study's owner is supported by a book-fair organizer biography rather than its retailer page (E4); Bob Slate's owner evidence is a **2011 local business association announcement**, so current ownership needs reconfirmation (E4). This is not an exhaustive corporate ownership investigation. Wet Paint replaced Archer because it explicitly identifies itself as a single-store independent business. Current location corrections include Baum-kuchen's Eagle Rock shop and FLAX's Fort Mason shop. Paper Tree uses both “Buchanan Mall” and “Buchanan Street” for the same address. The Paper Mouse shop is 1274 Washington Street; 1280 is its event space. Two Hands online assortment/warehouse differs from the Boulder store; exact in-store availability remains unknown.

## Scoring rubric (review queue, not purchase probability)

`priority = 10*C + 6*E + (20/3)*P`, maximum 100. Dimension inputs are reviewed judgments in the retailer CSV; the script reproduces arithmetic and rank, not the research judgment. No financial readiness, intent, inventory or likelihood of order is inferred.

| Dimension | Anchors and evidence requirements |
|---|---|
| Category fit C, 0–5, weight 50 | 0 no evidenced fit; 1 generic gift adjacency; 2 partial category adjacency with weak exact fit (Paper Skyscraper); 3 one directly observed relevant family (e.g. notebooks), or two adjacent families such as gift pouches/stickers; 4 two direct families such as notebooks and planners/cases; 5 three or more direct relevant families among notebooks, planners, memo stationery, pouches and decorative paper. A current official navigation/filter can count but is explicitly weaker than a named product. C measures breadth, not taste, sales demand or tested construction. Repeated notebook SKUs do not create extra families. |
| Evidence E, 0–5, weight 30 | 0 no sources; 1 third-party lead; 2 snippets only; 3 official assortment with location/ownership gaps; 4 core evidence present but ownership is historical/secondary or some reported assortment remains snippet-only; 5 official location + owner/family/independence + category + brand evidence reviewed. Official statements are still self-reported and can be stale. |
| Contact route P, 0–3, weight 20 | 0 reviewed contact channel bars vendor submissions and no permitted alternative found; 1 general public contact, buying policy unknown; 2 official named buying role plus general contact, acceptance unknown; 3 explicit incoming product/vendor submission channel. P3 is not permission to ignore restrictions or evidence of buyer interest. |
| Order feasibility, separate | **Unknown for all 20**, excluded from numerical score. Display actual per-SKU cartons and bundle units. Buyer capacity, supplier acceptance/current availability, landed price, margin, lead time, U.S. resale/licensing rights and actual carton acceptance have not been verified. |

Equal scores sort by stable retailer ID, an administrative tie-break with no commercial meaning. Paper Plant, Shorthand and Wonder Fair tie at 100. Penny Post scores 93.33 from a named buyer role. Atlas, Yoseka, Baum-kuchen, niconeco and OMOI tie at 86.67; Atlas is fifth only by the declared tie-break, and also serves as the first pilot. These weights are a transparent starting hypothesis, not a calibrated sales model.

## Contact rules and human review

- [Paper Plant](https://paperplant.co/pages/contact): `sales@paperplant.co` explicitly handles vendor inquiries. This is a valid inquiry route, not buying interest.
- [Shorthand FAQ](https://shopshorthand.com/pages/faqs): emailed product information welcomed; a narrow aesthetic and small store constrain selection. No unannounced sample visits. Dedicated buyer email not established; use the published public contact route to follow its instructions.
- [Wonder Fair submissions](https://www.wonderfair.com/submit): catalog/Faire links or samples, no guaranteed sample return, no follow-up inquiries. Its artwork exclusions include fan art and AI-assisted art. The catalog's artwork provenance and resale authority must be checked before submitting; using AI for research does not establish that merchandise violates or satisfies its policy.
- [Paper Skyscraper vendor page](https://www.paperskyscraper.com/pages/become-a-vendor): explicit form, no promised response/review timing. Weak exact category evidence and a large sticker carton limit priority.
- [Two Hands customer care](https://twohandspaperie.com/pages/customer-care): do not send vendor submissions to its web-order email (`webinfo@twohandspaperie.com`). Restriction is channel-specific, not proof the business refuses all vendors.
- Penny Post lists Julia as Buyer; The Paper Mouse lists an Assistant Buyer. Neither publishes a verified open incoming submission process in reviewed pages.
- Retailer “wholesale” pages often sell their **own** goods outward (e.g. niconeco, Greenwich, Oblation and Goods for the Study). They do not prove incoming buying acceptance.

Review candidate images and aesthetics, obtain actual English/internal-layout and paper samples, check supplier availability/resale authority, agree lawful commercial terms, then separately authorize any outreach. **No email, form submission, buyer conversation or purchase occurred in this pilot.** This is an internal review brief, not a send-ready quotation. Do not publish or add private costs, supplier XLSX files, stock, rebates, order details, credentials or correspondence.

The Phase 1 one-full-carton-per-SKU project rule remains: 4 candidates means 4 separate cartons if all are ordered. The Atlas candidate bundle is 124 units (24 + 40 + 20 + 40). No mixed or split cartons are assumed. `DTB6611-1` and `DTB6616-1` remain **112 units/carton**; the pilot deliberately does not pitch refill compatibility from nominal A6 size. All Phase 1 source limitations still apply. Supplier acceptance of the project MOQ rule is not independently verified.

## Reproduce and update

```bash
python3 -m unittest -v test_import
python3 phase2.py
python3 phase2.py --refresh
# Optional network GETs; may yield errors/rate limits and overwrite link_checks.csv:
python3 phase2.py --check-links
# Optional single-page PDF generation; needs reportlab + Pillow:
python3 phase2.py --brief
```

Edit reviewed evidence and match rows deliberately; never infer new supplier facts from retailer pages. `--refresh` recomputes ranking/top-five prose from CSV inputs. Validation checks 20 distinct businesses, 3–5 actual SKUs each, evidence foreign keys and provenance text consistency, original carton/image/source fields, score arithmetic, rank ties, prohibited channel handling, 112-unit overrides and SHA-256 preservation of 214 Phase 1 files. Six negative controls deliberately corrupt SKU, MOQ, provenance, feasibility, contact strength and a negated buyer-role claim. A passing script does **not** prove every source claim or future URL availability. No GitHub CI execution is implied.

Exclusions: [Little Otsu](https://www.littleotsu.com/pages/about-us) physical shop closed in 2024 (online shop remains); [Anderson Pens](https://www.andersonpens.com/) closed; [Appointed physical District Shop](https://appointed.co/blogs/noteworthy/a-new-chapter-for-appointed) closed (brand remains); [GREER](https://greerchicago.com/pages/customer-service) Chicago online-only with concessions elsewhere; Archer was omitted for weaker direct independence evidence. CW Pencil was not used; Greenwich Letterpress was verified instead. Closure decisions are not assertions that the remaining online brands stopped trading.

## Cost and measurement limits

TinyFish billed credits/USD were **not returned**; cost is Unknown. No wallet setting, subscription or auto-reload was changed. Provider-reported 231 seconds is browser-run duration, not total research labor or a time-saving measurement. Web tools and model cost were not instrumented. No measured customer time savings, conversion rate, deployed retailer usage or revenue outcome exists. Later compare the same frozen 5-store task manually vs agent-assisted, logging active human minutes, full elapsed time, source checks, critical factual errors, rework, billed API cost, permitted-route completeness and independently reviewed usefulness; only then report differences.
