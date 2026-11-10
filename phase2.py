#!/usr/bin/env python3
"""Validate catalog joins and integrate the three reproducible retailer pilots.

No outreach occurs. Product fit, evidence strength and buyer access remain separate;
there is no purchase-probability score or automatic winner at a shortlist cutoff.
"""
import argparse
import copy
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'phase2'
PILOTS = {'atlas': 'R01', 'shorthand': 'R05', 'wonder-fair': 'R16'}
LEGACY_FIELDS = (
    'category_fit_0_5', 'category_fit_reason', 'evidence_strength_0_5',
    'evidence_strength_reason', 'contact_route_0_3', 'contact_route_reason',
    'contact_priority_score', 'contact_priority_rank',
)
UNKNOWN = 'Unknown'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(name):
    with (DATA / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(name, rows):
    require(bool(rows), 'Cannot write empty review table')
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (DATA / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def migrate(retailers, matches, evidence):
    """Label previous research without claiming its sources were re-read."""
    for r in retailers:
        for key in LEGACY_FIELDS:
            if key in r:
                require('legacy_' + key not in r, 'Active score field unexpectedly reintroduced: ' + key)
                r['legacy_' + key] = r.pop(key)
        r.setdefault('research_status', 'legacy_not_revalidated')
        r.setdefault('product_fit', 'Legacy category hypothesis; needs revalidation')
        r.setdefault('evidence_strength', 'Legacy sources; not revalidated in this upgrade')
        r.setdefault('buyer_access', 'Legacy route; needs revalidation')
        r.setdefault('review_priority', 'Hold: source revalidation')
        r.setdefault('pilot_report', '')
        r.setdefault('location_ownership_scope', 'Legacy evidence; not revalidated in this upgrade')
        if r.get('order_feasibility') == 'unknown':
            r['order_feasibility'] = UNKNOWN
    for m in matches:
        m.setdefault('aesthetic_fit', 'Needs human image review; no aesthetic judgment verified')
        m.setdefault('evidence_scope', 'legacy_not_revalidated')
        m.setdefault('tie_group', 'category_candidates_need_human_review')
        if m.get('order_feasibility') == 'unknown':
            m['order_feasibility'] = UNKNOWN
    for e in evidence:
        e.setdefault('evidence_scope', 'legacy_not_revalidated')
        e.setdefault('confidence', 'Unknown: legacy row has no current field-level confidence')
        e.setdefault('quote', '')
        e.setdefault('source_capture', '')
        e.setdefault('field_value', '')
        e.setdefault('run_id', '')
    return retailers, matches, evidence


def _joined(value):
    if isinstance(value, list):
        return '|'.join(str(x) for x in value) or UNKNOWN
    return str(value) if value else UNKNOWN


def integrate_pilots(retailers, matches, evidence, pilot_root=None):
    """Replace only the three pilot matches; retain all historical evidence rows."""
    from research import validate_outputs
    pilot_root = Path(pilot_root or DATA / 'pilots')
    retailers, matches, evidence = migrate(copy.deepcopy(retailers), copy.deepcopy(matches), copy.deepcopy(evidence))
    by_id = {r['retailer_id']: r for r in retailers}
    for slug, rid in PILOTS.items():
        directory = pilot_root / slug
        validate_outputs(directory, ROOT)
        result = json.loads((directory / 'research.json').read_text(encoding='utf-8'))
        require(result['summary']['catalog_count'] == 210, 'Pilot did not evaluate the complete 210-SKU catalog')
        require(result['status'] in ('completed', 'partial', 'needs_review'), 'Pilot did not complete a usable evidence review')
        require(urlparse(result['website']).hostname.removeprefix('www.') ==
                urlparse(by_id[rid]['website']).hostname.removeprefix('www.'), 'Pilot business URL mismatch')
        with (directory / 'evidence.csv').open(encoding='utf-8', newline='') as f:
            source_evidence = list(csv.DictReader(f))
        with (directory / 'recommendations.csv').open(encoding='utf-8', newline='') as f:
            selected = list(csv.DictReader(f))
        require(3 <= len(selected) <= 5, 'A promoted pilot needs 3-5 evidence-supported SKU candidates')
        prefix = rid + '-P-'
        evidence = [e for e in evidence if not e['evidence_id'].startswith(prefix)]
        converted = []
        mapping = {}
        for e in source_evidence:
            if not e.get('source_url') or e.get('value') == UNKNOWN:
                continue
            eid = prefix + e['evidence_id']
            mapping[e['evidence_id']] = eid
            converted.append({
                'evidence_id': eid, 'retailer_id': rid,
                'claim_type': e['field'], 'claim': e['quote'], 'field_value': e['value'], 'url': e['source_url'],
                'retrieved_at_utc': e['retrieved_at_utc'], 'access_method': e['acquisition'],
                'verification_status': 'page_read', 'source_class': 'retailer_official',
                'support_limit': 'Official page text or navigation only; no inventory, taste, buyer interest or carton acceptance established.',
                'evidence_scope': 'current_pilot', 'confidence': e['confidence'],
                'quote': e['quote'], 'run_id': e.get('run_id', ''), 'source_capture': str((directory / 'research.json').relative_to(DATA)),
            })
        evidence += converted
        matches = [m for m in matches if m['retailer_id'] != rid]
        for i, m in enumerate(selected, 1):
            ids = [mapping[eid] for eid in m['retailer_evidence_ids'].split('|') if eid]
            require(bool(ids), 'Pilot candidate lacks usable assortment evidence')
            row = {
                'retailer_id': rid, 'match_rank': str(i), 'sku': m['sku'], 'name_zh': m['name_zh'],
                'english_description_inferred': m['product_category_inferred'] + ' (category translation; inspect actual product)',
                'product_category_inferred': m['product_category_inferred'], 'collection': m['collection'],
                'retailer_evidence_ids': '|'.join(ids), 'retailer_fact': m['retailer_fact'],
                'retailer_evidence_url': m['retailer_evidence_url'], 'match_basis': m['match_basis'],
                'match_reason': m['match_reason'], 'confidence': 'Category inference; aesthetic fit needs human review',
                'image_path': m['image_path'], 'product_source': 'products.csv',
                'product_source_sheet': m['product_source_sheet'], 'product_source_row': m['product_source_row'],
                'units_per_carton': m['units_per_carton'], 'moq_cartons': m['moq_cartons'],
                'moq_units': m['moq_units'], 'carton_qty_basis': m['carton_qty_basis'],
                'order_feasibility': UNKNOWN, 'commercial_status': 'research_candidate_only',
                'unknowns': 'Buyer interest, aesthetic fit, language/layout, paper performance, supply, landed economics and resale authority remain Unknown.',
                'aesthetic_fit': m['aesthetic_fit'], 'evidence_scope': 'current_pilot',
                'tie_group': m.get('tie_group', 'category_candidates_need_human_review'),
            }
            matches.append(row)
        r = by_id[rid]
        summary = result['summary']
        r.update({
            'research_status': 'current_pilot', 'product_fit': summary['product_fit'],
            'evidence_strength': summary['evidence_strength'], 'buyer_access': summary['buyer_access'],
            'review_priority': '1 (tie; human review)',
            'pilot_report': str((directory / 'buyer_brief.md').relative_to(DATA)),
            'matched_sku_count': str(len(selected)), 'minimum_cartons_all_candidates': str(len(selected)),
            'minimum_units_all_candidates': str(sum(int(m['moq_units']) for m in selected)),
            'categories_verified': _joined(result['fields']['categories']['value']),
            'brands_verified': _joined(result['fields']['brands']['value']),
            'vendor_policy_status': UNKNOWN if result['fields']['vendor_policy']['value'] == UNKNOWN else 'Official policy text observed; review restrictions',
            'vendor_policy_evidence_ids': '|'.join(e['evidence_id'] for e in converted if e['claim_type'] == 'vendor_policy'),
            'research_method': result['acquisition'],
            'retrieved_at_utc': max((e['retrieved_at_utc'] for e in converted), default=UNKNOWN),
            'contact_url': next((e['url'] for e in converted if e['claim_type'] == 'contact'), r['website']),
            'vendor_submission_url': next((e['url'] for e in converted if e['claim_type'] == 'vendor_policy'), ''),
            'policy_pages_reviewed': '|'.join(dict.fromkeys(e['url'] for e in converted if e['claim_type'] in ('contact', 'vendor_policy'))),
            'contact_constraints': 'Review exact current policy quotations; general contact is not submission permission. ' + _joined(result['fields']['vendor_policy']['value']),
            'notes': 'Current pilot revalidates categories/brands/contact/vendor policy only. Location/ownership remain explicitly legacy. No outreach.',
        })
    return retailers, matches, evidence


def validate(retailers, matches, evidence):
    with (ROOT / 'products.csv').open(encoding='utf-8-sig', newline='') as f:
        products = {p['sku']: p for p in csv.DictReader(f)}
    require(len(products) == 210, 'Need the unchanged 210-SKU catalog')
    ids = {r['retailer_id'] for r in retailers}
    ev = {e['evidence_id']: e for e in evidence}
    require(len(retailers) == len(ids) == 20, 'Need exactly 20 unique retailer businesses')
    require(len({urlparse(r['website']).hostname.removeprefix('www.') for r in retailers}) == 20,
            'Duplicate business websites; branches must count once')
    require(len(ev) == len(evidence), 'Duplicate evidence IDs')
    checked_pilots = {}
    for e in evidence:
        require(e['retailer_id'] in ids, 'Evidence retailer FK missing')
        u = urlparse(e['url'])
        require(u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password,
                'Evidence URL must be public absolute HTTPS without credentials')
        require(e['verification_status'] in ('page_read', 'search_snippet_only', 'provider_only'), 'Unknown evidence status')
        timestamp = datetime.fromisoformat(e['retrieved_at_utc'].replace('Z', '+00:00'))
        require(timestamp.tzinfo is not None, 'Retrieval timestamp must include timezone')
        require(bool(e['claim'].strip()), 'Empty evidence claim')
        require(e['evidence_scope'] in ('current_pilot', 'legacy_not_revalidated'), 'Missing evidence scope')
        if e['evidence_scope'] == 'current_pilot':
            require(bool(e['quote'].strip()) and bool(e['confidence'].strip()), 'Current field evidence needs exact quote and confidence')
            path = (DATA / e['source_capture']).resolve()
            require(DATA.resolve() in path.parents and path.is_file(), 'Current evidence capture missing or outside phase2')
            directory = path.parent
            if directory not in checked_pilots:
                from research import validate_outputs
                validate_outputs(directory, ROOT)
                with (directory / 'evidence.csv').open(encoding='utf-8', newline='') as f:
                    checked_pilots[directory] = {row['evidence_id']: row for row in csv.DictReader(f)}
            raw_id = e['evidence_id'].split('-P-', 1)[-1]
            source = checked_pilots[directory].get(raw_id)
            require(source is not None, 'Current field evidence absent from validated pilot')
            for dest, original in (('claim', 'quote'), ('field_value', 'value'), ('claim_type', 'field'), ('url', 'source_url'),
                                   ('retrieved_at_utc', 'retrieved_at_utc'), ('quote', 'quote'),
                                   ('confidence', 'confidence'), ('access_method', 'acquisition'), ('run_id', 'run_id')):
                require(e[dest] == source[original], 'Current field evidence drift: ' + e['evidence_id'])
    counts = Counter(m['retailer_id'] for m in matches)
    require(set(counts) == ids, 'Each retailer needs SKU matches')
    require(len({(m['retailer_id'], m['sku']) for m in matches}) == len(matches), 'Duplicate match pair')
    pilot_count = 0
    for r in retailers:
        rid = r['retailer_id']
        require(r['country'] == 'USA' and bool(re.fullmatch(r'\d{5}', r['postal_code'])), 'US location/ZIP missing')
        require(all(r[k].strip() for k in ('address', 'city', 'state', 'independence_basis')), 'Missing historical location/independence')
        owned = [e for e in evidence if e['retailer_id'] == rid]
        require({'address', 'independence', 'category', 'brand'}.issubset({e['claim_type'] for e in owned}), 'Historical core evidence missing')
        for key in ('independence_evidence_ids', 'vendor_policy_evidence_ids', 'buyer_role_evidence_ids'):
            for eid in filter(None, r[key].split('|')):
                require(eid in ev and ev[eid]['retailer_id'] == rid, 'Retailer evidence FK missing or cross-store')
        require(3 <= counts[rid] <= 5 and counts[rid] == int(r['matched_sku_count']), 'Need 3-5 actual SKUs per store')
        require(r['order_feasibility'] == UNKNOWN, 'No buyer has confirmed order feasibility')
        require(all(r.get(k) for k in ('product_fit', 'evidence_strength', 'buyer_access', 'review_priority')), 'Separate review dimensions missing')
        require(not any(k in r for k in LEGACY_FIELDS), 'Legacy numeric ranking must not remain active')
        if r['research_status'] == 'current_pilot':
            pilot_count += 1
            require(rid in PILOTS.values(), 'Unexpected current-pilot business')
            require(r['review_priority'] == '1 (tie; human review)', 'Pilot tie must remain explicit; no artificial top-five cutoff')
            report = (DATA / r['pilot_report']).resolve()
            require(DATA.resolve() in report.parents and report.is_file(), 'Pilot report missing')
            result = json.loads((report.parent / 'research.json').read_text(encoding='utf-8'))
            for field in ('product_fit', 'evidence_strength', 'buyer_access'):
                require(r[field] == result['summary'][field], 'Current review dimension differs from validated pilot: ' + field)
            require(r['research_method'] == result['acquisition'], 'Current acquisition method drift')
            require(r['categories_verified'] == _joined(result['fields']['categories']['value']), 'Current categories drift')
            require(r['brands_verified'] == _joined(result['fields']['brands']['value']), 'Current brands drift')
        else:
            require(r['research_status'] == 'legacy_not_revalidated' and r['review_priority'] == 'Hold: source revalidation',
                    'Legacy source set cannot be presented as currently validated')
        selected = [m for m in matches if m['retailer_id'] == rid]
        require(int(r['minimum_cartons_all_candidates']) == len(selected), 'Carton count must be per SKU')
        require(int(r['minimum_units_all_candidates']) == sum(int(m['moq_units']) for m in selected), 'Bundle units mismatch')
    require(pilot_count in (0, 3), 'Promote all three pilot outputs together')
    for m in matches:
        require(m['sku'] in products, 'Invented SKU / product FK missing')
        p = products[m['sku']]
        for dest, src in (('name_zh', 'name_zh'), ('collection', 'collection'), ('image_path', 'image_path'),
                          ('units_per_carton', 'units_per_carton'), ('moq_cartons', 'moq_cartons'),
                          ('moq_units', 'moq_units'), ('carton_qty_basis', 'carton_qty_basis'),
                          ('product_source_sheet', 'source_sheet'), ('product_source_row', 'source_row')):
            require(m[dest] == p[src], f'SKU source mismatch: {m["sku"]} {dest}')
        require(int(m['moq_cartons']) == 1 and int(m['moq_units']) == int(m['units_per_carton']), 'Per-SKU carton rule violated')
        require((ROOT / m['image_path']).is_file(), 'Missing image')
        require('inference' in m['match_basis'], 'Match must be labeled inference')
        require(m['order_feasibility'] == UNKNOWN and m['commercial_status'] == 'research_candidate_only', 'Commercial overclaim')
        require(bool(m['aesthetic_fit']), 'Aesthetic uncertainty missing')
        for eid in m['retailer_evidence_ids'].split('|'):
            require(eid in ev and ev[eid]['retailer_id'] == m['retailer_id'], 'Match cites wrong/missing retailer')
            require(ev[eid]['claim_type'] in ('category', 'brand', 'product'), 'Match needs assortment evidence')
            require(ev[eid]['verification_status'] == 'page_read', 'Unconfirmed provider/snippet claim used for matching')
            if m['evidence_scope'] == 'current_pilot':
                require(ev[eid]['evidence_scope'] == 'current_pilot', 'Current pilot cannot cite historical assortment')
        require(any(m['retailer_evidence_url'] == ev[eid]['url'] and m['retailer_fact'] == ev[eid]['claim']
                    for eid in m['retailer_evidence_ids'].split('|')), 'Match fact/provenance drift')
    for sku in ('DTB6611-1', 'DTB6616-1'):
        require(products[sku]['units_per_carton'] == '112', 'Owner-confirmed 112-unit carton changed')
    for rows in (retailers, matches, evidence):
        require(not any(str(v).lstrip().startswith(('=', '+', '-', '@')) for row in rows for v in row.values()), 'Unsafe spreadsheet formula prefix')
    manifest = json.loads((DATA / 'sources/phase1_manifest.json').read_text())
    require(len(manifest['phase1_files']) == 214, 'Phase 1 preservation manifest incomplete')
    for path, expected in manifest['phase1_files'].items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Phase 1 file changed: ' + path)
    run = json.loads((DATA / 'sources/tinyfish_atlas_run.json').read_text())
    require(run['response']['status'] == 'completed' and run['run_id'] == '98bb203b-8683-4485-8f7b-fc157e5c2a3b', 'Historical TinyFish receipt missing')
    return {'retailers': len(retailers), 'current_pilots': pilot_count, 'legacy_not_revalidated': 20 - pilot_count,
            'sku_matches': len(matches), 'evidence_rows': len(evidence), 'phase1_preserved_files': 214,
            'purchase_probability': 'Not modeled', 'order_feasibility': UNKNOWN, 'checks': 'passed'}


def fault_checks(retailers, matches, evidence):
    """Small negative controls for joins, commercial claims and artificial ranking."""
    cases = []
    m = copy.deepcopy(matches); m[0]['sku'] = 'NOT-A-REAL-SKU'; cases.append((retailers, m, evidence))
    m = copy.deepcopy(matches); m[0]['moq_units'] = '1'; cases.append((retailers, m, evidence))
    m = copy.deepcopy(matches); m[0]['retailer_evidence_ids'] = 'R20-E04'; cases.append((retailers, m, evidence))
    r = copy.deepcopy(retailers); r[0]['order_feasibility'] = 'Confirmed'; cases.append((r, matches, evidence))
    r = copy.deepcopy(retailers); r[0]['contact_priority_score'] = '99.99'; cases.append((r, matches, evidence))
    r = copy.deepcopy(retailers); r[0]['review_priority'] = 'Automatic winner'; cases.append((r, matches, evidence))
    for args in cases:
        try:
            validate(*args)
        except ValueError:
            continue
        raise ValueError('A deliberately corrupted dataset passed validation')
    return len(cases)


def refresh(retailers, matches, evidence):
    validate(retailers, matches, evidence)
    for name, rows in (('retailers.csv', retailers), ('sku_matches.csv', matches), ('evidence.csv', evidence)):
        write(name, rows)
    current = sorted((r for r in retailers if r['research_status'] == 'current_pilot'), key=lambda r: r['name'])
    text = [
        f'# Buyer review queue — {len(current)} current pilots; remaining stores on hold', '',
        'The historical filename is retained. This is not an automatically selected top five or a list of confirmed buyers. '
        f'There is no weighted total score or purchasing probability. **All {len(current)} current pilots share priority 1 (tie; human review).** '
        'Alphabetical display order has no commercial meaning. Order feasibility is **Unknown** for every retailer.', '',
        '| Review priority | Retailer | Product fit | Evidence strength | Buyer access | All-candidate minimum |',
        '|---|---|---|---|---|---|',
    ]
    for r in current:
        text.append(f'| 1 (tie; human review) | [{r["name"]}]({r["pilot_report"]}) | {r["product_fit"]} | {r["evidence_strength"]} | {r["buyer_access"]} | {r["minimum_cartons_all_candidates"]} cartons / {r["minimum_units_all_candidates"]} units |')
    for r in current:
        selected = [m for m in matches if m['retailer_id'] == r['retailer_id']]
        text += ['', '## ' + r['name'],
                 'Current field-level evidence, exact source links and retrieval times: [pilot brief](' + r['pilot_report'] + ').',
                 '**Candidate SKUs:** ' + ', '.join(f'{m["sku"]} ({m["moq_units"]} units / carton; [category evidence]({m["retailer_evidence_url"]}))' for m in selected) + '.',
                 '**Product fit:** category-level inference from the entire 210-SKU candidate audit. Images link to the unchanged original SKU photos. Aesthetic fit, language/layout and paper performance need human review.',
                 '**Order feasibility: Unknown.** Each individual SKU requires one separate full carton under the project rule. No buyer confirmed buying interest, carton acceptance or commercial terms.',
                 '**Location / ownership:** historical evidence retained; the new pilot does not revalidate those fields. No outreach occurred.']
        policies = [e for e in evidence if e['retailer_id'] == r['retailer_id']
                    and e['evidence_scope'] == 'current_pilot' and e['claim_type'] == 'vendor_policy']
        if policies:
            text += ['', '**Published submission-policy excerpts:** Read the complete linked source before acting; excerpts do not establish applicability or buying interest.', '']
            for e in policies:
                quote = ' '.join(e['quote'].split()).replace('"', '&quot;')
                text.append('- "' + quote + '" [Source](' + e['url'] + ') (' + e['evidence_id'] + ').')
        else:
            text += ['', '**Vendor submission policy: Unknown.** A general contact route is not incoming-vendor permission.']
    held = sorted((r for r in retailers if r['research_status'] != 'current_pilot'), key=lambda r: r['name'])
    text += ['', f'## Hold — remaining {len(held)} stores', '',
             ', '.join(r['name'] for r in held) + '.', '',
             'Their historical records and candidate joins remain available for review, explicitly marked `legacy_not_revalidated`. '
             'No new evidence or new TinyFish execution is claimed for them. Revalidate sources and run the full-catalog workflow before promoting any into the current queue.', '',
             'A person must review the separate dimensions and permitted contact policy before choosing any five stores. '
             'The legacy scores are retained only in `legacy_*` CSV columns for audit history; they never drive this queue. '
             'No forms, email, purchases, dashboard or CRM were added.', '',
             'The old `atlas_buyer_brief.pdf` is a historical Phase 2 artifact with obsolete score/selection details. Use the current Atlas Markdown brief linked above.']
    (DATA / 'top5_buyers.md').write_text('\n'.join(text) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Validate and regenerate the tied human-review queue; no network')
    parser.add_argument('--integrate-pilots', action='store_true', help='Import all three existing validated research.py output directories and refresh CSVs/queue')
    parser.add_argument('--brief', action='store_true', help='Print the current Atlas Markdown brief path; historical PDF is not regenerated')
    args = parser.parse_args()
    retailers, matches, evidence = read('retailers.csv'), read('sku_matches.csv'), read('evidence.csv')
    if args.integrate_pilots:
        retailers, matches, evidence = integrate_pilots(retailers, matches, evidence)
    else:
        retailers, matches, evidence = migrate(retailers, matches, evidence)
    if args.refresh or args.integrate_pilots:
        refresh(retailers, matches, evidence)
    report = validate(retailers, matches, evidence)
    report['negative_controls_passed'] = fault_checks(retailers, matches, evidence)
    if args.brief:
        report['brief'] = 'phase2/pilots/atlas/buyer_brief.md'
        report['historical_pdf_status'] = 'Archived; obsolete score and SKU selection, not regenerated'
    report['checked_at_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
