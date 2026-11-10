#!/usr/bin/env python3
"""Small offline, human-reviewed comparison. No gold labels or API requests.

Generated review rows conceal the system-to-side mapping. Keep the adjacent
*.key.csv away from reviewers until answers are locked; prose can reveal origin,
so this is partial blinding, not an independently validated benchmark.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import research

RETAILERS = ('atlas', 'shorthand', 'wonder-fair')
REVIEW_COLUMNS = ('review_id', 'retailer_id', 'sku', 'name_zh', 'image_path',
    'moq_cartons', 'moq_units', 'confirmed_product_facts',
    'retailer_evidence_urls', 'comparison_a', 'comparison_b',
    'commercial_unknowns', 'choice', 'sku_fit', 'reason', 'reviewer', 'seconds')
KEY_COLUMNS = ('review_id', 'retailer_id', 'sku', 'a_system', 'b_system',
               'sample_reason', 'new_status')
PROBES = (
    ('DT589003', 'Intentional challenge: blind-box pen; category overlap may conceal design and 768-unit carton mismatch.'),
    ('DTBB0113', 'Intentional challenge: storage design contrast; evaluate the real image, not the category name.'),
    ('DTB6611-1', 'Intentional challenge: blank A6 refill; compatibility with actual retailer notebook systems is unverified.'),
    ('DTYC0006', 'Design comparison probe: A6 illustrated journal hypothesis; inspect evidence and image before deciding.'),
)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def _score(candidate):
    for field in ('score', 'text_score', 'style_score', 'support_score'):
        try:
            return float(candidate[field])
        except (KeyError, ValueError, TypeError):
            continue
    return len(candidate.get('retailer_evidence_ids') or [])


def _as_text(value):
    if isinstance(value, list):
        return '; '.join(str(v) for v in value)
    return str(value or 'Unknown')


def sample_candidates(result, count=12):
    """Deterministic union, including challenges; no hypothesis becomes a label."""
    candidates = {c['sku']: c for c in result['candidates']}
    if len(candidates) != len(result['candidates']):
        raise ValueError('Duplicate candidate SKU')
    chosen, reasons = [], {}
    def add(sku, reason):
        if sku not in candidates:
            raise ValueError('Comparison references missing candidate SKU: ' + sku)
        reasons.setdefault(sku, []).append(reason)
        if sku not in chosen:
            chosen.append(sku)
    for sku in result.get('baseline_skus', []):
        add(sku, 'Frozen pre-change category-baseline selection')
    for sku in result.get('selected_skus', []):
        add(sku, 'New evidence-linked shortlist selection')
    for sku, reason in PROBES:
        add(sku, reason)
    if len(chosen) > count:
        raise ValueError('Baseline + new shortlist + challenges exceed sample budget')
    for c in sorted(candidates.values(), key=lambda c: (-_score(c), c['sku'])):
        if len(chosen) >= count:
            break
        if c['sku'] not in chosen:
            add(c['sku'], 'Remaining evidence-supported candidate, or highest available support when evidence is insufficient')
    if len(chosen) != count:
        raise ValueError('Not enough unique catalog candidates for review sample')
    return [(candidates[sku], '; '.join(reasons[sku])) for sku in chosen]


def build_review_rows(results, products, seed='kinbor-style-v1'):
    """Build 12 real-catalog SKU comparisons per retailer and a separate key."""
    catalog = {p['sku']: p for p in products}
    rows, keys = [], []
    for result in results:
        retailer = result['retailer_id']
        if len(result['candidates']) != len(catalog) or {c['sku'] for c in result['candidates']} != set(catalog):
            raise ValueError('Comparison must retain the complete catalog audit')
        baseline_reasons = result.get('baseline_reasons') or {}
        for candidate, sample_reason in sample_candidates(result):
            sku = candidate['sku']
            product = catalog[sku]
            # The catalog is authoritative for identifiers, image and carton facts.
            for field in ('image_path', 'moq_units'):
                if field in candidate and str(candidate[field]) != str(product[field]):
                    raise ValueError('Candidate catalog fact drift: ' + field)
            rid = retailer + ':' + sku
            if sku in result.get('baseline_skus', []):
                old = baseline_reasons.get(sku) or 'Selected by frozen category baseline; product-specific style reasoning was not recorded in the comparison input.'
            else:
                old = 'Not selected by category baseline.'
            new = _as_text(candidate.get('reason'))
            counter = candidate.get('counterevidence') or []
            if counter:
                new += ' Counterevidence / uncertainty: ' + _as_text(counter)
            new += ' Review disposition: ' + str(candidate.get('status', 'needs_human_review')) + '.'
            # Stable per-row side assignment. A reproducible mapping is hidden in key.csv.
            swap = int(hashlib.sha256((seed + ':' + rid).encode()).hexdigest(), 16) % 2
            a, b = (new, old) if swap else (old, new)
            urls = candidate.get('retailer_evidence_urls') or candidate.get('evidence_urls') or candidate.get('retailer_evidence_url') or []
            if not urls:
                # Rejected/unassessed examples still need actual store context;
                # these are comparison references, not claimed positive support.
                urls = [e['source_url'] for e in result.get('observations', [])]
            row = {'review_id': rid, 'retailer_id': retailer, 'sku': sku,
                'name_zh': product['name_zh'], 'image_path': product['image_path'],
                'moq_cartons': product['moq_cartons'], 'moq_units': product['moq_units'],
                'confirmed_product_facts': f"Catalog SKU {sku}; {product['category']}; one full carton / {product['moq_units']} units; source {product['source_sheet']} row {product['source_row']}. Category may be inferred; style, materials and performance are not confirmed by this cell.",
                'retailer_evidence_urls': _as_text(urls), 'comparison_a': a, 'comparison_b': b,
                'commercial_unknowns': 'Buyer interest, stock, resale authorization, supply, price/margin and acceptance of one full carton per individual SKU remain Unknown.',
                'choice': '', 'sku_fit': '', 'reason': '', 'reviewer': '', 'seconds': ''}
            rows.append(row)
            keys.append({'review_id': rid, 'retailer_id': retailer, 'sku': sku,
                         'a_system': 'new' if swap else 'old', 'b_system': 'old' if swap else 'new',
                         'sample_reason': sample_reason, 'new_status': candidate.get('status', 'needs_human_review')})
    # Shuffle row display reproducibly too, independent of support/rank/source order.
    rows.sort(key=lambda r: hashlib.sha256((seed + ':order:' + r['review_id']).encode()).hexdigest())
    return rows, keys


def generate(pilot_root, output, *, catalog_path=research.ROOT / 'products.csv', force=False, seed='kinbor-style-v1'):
    output = Path(output)
    key_path = output.with_suffix('.key.csv')
    if not force and (output.exists() or key_path.exists()):
        raise ValueError('Review output exists; preserve responses or use a new --output. --force explicitly replaces both files.')
    # Import locally so the evaluator stays a consumer of the matching workflow,
    # and never publishes a comparison from edited/stale unsupported decisions.
    import matching
    for retailer in RETAILERS:
        matching.validate_saved(Path(pilot_root) / retailer)
    results = [json.loads((Path(pilot_root) / r / 'matching.json').read_text(encoding='utf-8')) for r in RETAILERS]
    rows, keys = build_review_rows(results, research.load_catalog(catalog_path), seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    research.write_csv(output, rows, REVIEW_COLUMNS)
    research.write_csv(key_path, keys, KEY_COLUMNS)
    return {'status': 'generated', 'rows': len(rows), 'reviews': str(output),
            'mapping_key': str(key_path), 'gold_labels': 0,
            'source_validation': 'All three saved matching outputs validated offline.',
            'quality_claim': 'Not measured; human responses are blank.'}


def summarize(review_path, key_path=None):
    rows = read_csv(review_path)
    keys = read_csv(key_path or Path(review_path).with_suffix('.key.csv'))
    mapping = {r['review_id']: r for r in keys}
    if len(mapping) != len(keys) or len({r['review_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate review IDs')
    if set(mapping) != {r['review_id'] for r in rows}:
        raise ValueError('Review/key identity mismatch')
    preference, fit, retailer_counts = Counter(), Counter(), {}
    seconds, timed = 0.0, 0
    for row in rows:
        key = mapping[row['review_id']]
        if row['sku'] != key['sku'] or row['retailer_id'] != key['retailer_id']:
            raise ValueError('Review/key SKU or retailer mismatch')
        choice = row.get('choice', '').strip().lower()
        label = row.get('sku_fit', '').strip().lower()
        if choice not in ('', 'a', 'b', 'uncertain', 'tie') or label not in ('', 'yes', 'no', 'uncertain'):
            raise ValueError('Use choice A/B/uncertain/tie and sku_fit yes/no/uncertain (or blank)')
        if key['a_system'] not in ('old', 'new') or key['b_system'] not in ('old', 'new') or key['a_system'] == key['b_system']:
            raise ValueError('Invalid system-side mapping')
        selected = key[choice + '_system'] if choice in ('a', 'b') else choice or 'pending'
        preference[selected] += 1
        fit[label or 'pending'] += 1
        per = retailer_counts.setdefault(row['retailer_id'], Counter())
        per[selected] += 1
        value = row.get('seconds', '').strip()
        if value:
            try:
                amount = float(value)
            except ValueError:
                raise ValueError('Review seconds must be a nonnegative finite number') from None
            if not 0 <= amount < float('inf'):
                raise ValueError('Review seconds must be a nonnegative finite number')
            seconds += amount
            timed += 1
    return {'rows': len(rows), 'preference_counts': dict(preference), 'sku_fit_counts': dict(fit),
            'definite_fit_labels': fit['yes'] + fit['no'], 'uncertain_fit_excluded': fit['uncertain'],
            'per_retailer_preference_counts': {r: dict(c) for r, c in retailer_counts.items()},
            'recorded_review_seconds': round(seconds, 3) if timed else 'Unknown', 'timed_rows': timed,
            'accuracy': 'Not computed: these subjective comparison responses are not independent gold labels.',
            'commercial_outcome': 'Unknown; reviewer preference does not establish buyer acceptance.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--generate', action='store_true')
    action.add_argument('--summarize', type=Path, metavar='REVIEWS_CSV')
    parser.add_argument('--pilot-root', type=Path, default=research.ROOT / 'phase2' / 'live')
    parser.add_argument('--output', type=Path, default=research.ROOT / 'phase2' / 'reviews.csv')
    parser.add_argument('--key', type=Path, help='System mapping file for summarize only')
    parser.add_argument('--seed', default='kinbor-style-v1')
    parser.add_argument('--force', action='store_true', help='Explicitly replace existing generated review and key files')
    args = parser.parse_args(argv)
    try:
        report = summarize(args.summarize, args.key) if args.summarize else generate(args.pilot_root, args.output, force=args.force, seed=args.seed)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, research.safe_text(str(exc)) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
